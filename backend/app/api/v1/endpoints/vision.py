"""AI Vision endpoints: cameras, authorized persons, face enrollment, threats, tracking."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, TokenClaims, get_pagination, require_permissions
from app.models.vision import (
    AuthorizedPerson,
    CameraFeed,
    FaceDetection,
    FaceEncoding,
    PersonTrack,
    ThreatDetection,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.vision import (
    AuthorizedPersonCreate,
    AuthorizedPersonResponse,
    AuthorizedPersonUpdate,
    CameraFeedCreate,
    CameraFeedResponse,
    CameraFeedUpdate,
    FaceDetectionResponse,
    FaceEnrollRequest,
    FaceEnrollResponse,
    PersonTrackResponse,
    ThreatAcknowledge,
    ThreatDetectionResponse,
    VisionDashboardStats,
)

router = APIRouter()


# ── Authorized Persons ────────────────────────────────────────────────────────

@router.get("/persons", response_model=PaginatedResponse[AuthorizedPersonResponse])
async def list_authorized_persons(
    client_id: UUID | None = Query(None),
    person_type: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuthorizedPerson).where(AuthorizedPerson.tenant_id == claims.tenant_id)
    if claims.client_id:
        q = q.where(AuthorizedPerson.client_id == claims.client_id)
    elif client_id:
        q = q.where(AuthorizedPerson.client_id == client_id)
    if person_type:
        q = q.where(AuthorizedPerson.person_type == person_type)
    if status:
        q = q.where(AuthorizedPerson.status == status)
    if search:
        pattern = f"%{search}%"
        q = q.where(
            (AuthorizedPerson.first_name.ilike(pattern))
            | (AuthorizedPerson.last_name.ilike(pattern))
            | (AuthorizedPerson.employee_id.ilike(pattern))
        )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(AuthorizedPerson.last_name.asc())
    q = q.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
    rows = (await db.execute(q)).scalars().all()

    results = []
    for person in rows:
        enc_count = (await db.execute(
            select(func.count()).where(FaceEncoding.person_id == person.id)
        )).scalar() or 0
        resp = AuthorizedPersonResponse.model_validate(person)
        resp.face_encoding_count = enc_count
        results.append(resp)

    return PaginatedResponse(
        data=results, total=total, page=pagination.page,
        limit=pagination.limit, pages=(total + pagination.limit - 1) // pagination.limit,
    )


@router.post("/persons", response_model=AuthorizedPersonResponse, status_code=201)
async def create_authorized_person(
    body: AuthorizedPersonCreate,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    person = AuthorizedPerson(
        tenant_id=claims.tenant_id,
        client_id=body.client_id,
        site_ids=[str(s) for s in body.site_ids] if body.site_ids else None,
        first_name=body.first_name,
        last_name=body.last_name,
        person_type=body.person_type,
        employee_id=body.employee_id,
        department=body.department,
        access_level=body.access_level,
        access_schedule=body.access_schedule,
        notes=body.notes,
    )
    db.add(person)
    await db.flush()
    await db.refresh(person)
    return AuthorizedPersonResponse.model_validate(person)


@router.get("/persons/{person_id}", response_model=AuthorizedPersonResponse)
async def get_authorized_person(
    person_id: UUID,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthorizedPerson).where(
            AuthorizedPerson.id == person_id,
            AuthorizedPerson.tenant_id == claims.tenant_id,
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    enc_count = (await db.execute(
        select(func.count()).where(FaceEncoding.person_id == person.id)
    )).scalar() or 0
    resp = AuthorizedPersonResponse.model_validate(person)
    resp.face_encoding_count = enc_count
    return resp


@router.patch("/persons/{person_id}", response_model=AuthorizedPersonResponse)
async def update_authorized_person(
    person_id: UUID,
    body: AuthorizedPersonUpdate,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthorizedPerson).where(
            AuthorizedPerson.id == person_id,
            AuthorizedPerson.tenant_id == claims.tenant_id,
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "site_ids" and value is not None:
            value = [str(s) for s in value]
        setattr(person, field, value)
    await db.flush()
    await db.refresh(person)
    return AuthorizedPersonResponse.model_validate(person)


@router.delete("/persons/{person_id}", response_model=MessageResponse)
async def delete_authorized_person(
    person_id: UUID,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuthorizedPerson).where(
            AuthorizedPerson.id == person_id,
            AuthorizedPerson.tenant_id == claims.tenant_id,
        )
    )
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    await db.delete(person)
    await db.flush()
    return MessageResponse(message="Person deleted")


# ── Face Enrollment ───────────────────────────────────────────────────────────

@router.post("/persons/{person_id}/enroll", response_model=FaceEnrollResponse)
async def enroll_face(
    person_id: UUID,
    body: FaceEnrollRequest,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    from app.services.face_recognition_service import FaceRecognitionService
    svc = FaceRecognitionService(db, claims)
    try:
        result = await svc.enroll_face(person_id, body.image_base64, body.is_primary)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return FaceEnrollResponse(**result)


# ── Camera Feeds ──────────────────────────────────────────────────────────────

@router.get("/cameras", response_model=PaginatedResponse[CameraFeedResponse])
async def list_cameras(
    client_id: UUID | None = Query(None),
    site_id: UUID | None = Query(None),
    status: str | None = Query(None),
    ai_enabled: bool | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(CameraFeed).where(CameraFeed.tenant_id == claims.tenant_id)
    if claims.client_id:
        q = q.where(CameraFeed.client_id == claims.client_id)
    elif client_id:
        q = q.where(CameraFeed.client_id == client_id)
    if site_id:
        q = q.where(CameraFeed.site_id == site_id)
    if status:
        q = q.where(CameraFeed.status == status)
    if ai_enabled is not None:
        q = q.where(CameraFeed.ai_enabled == ai_enabled)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(CameraFeed.name.asc())
    q = q.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
    rows = (await db.execute(q)).scalars().all()

    return PaginatedResponse(
        data=[CameraFeedResponse.model_validate(r) for r in rows],
        total=total, page=pagination.page,
        limit=pagination.limit, pages=(total + pagination.limit - 1) // pagination.limit,
    )


@router.post("/cameras", response_model=CameraFeedResponse, status_code=201)
async def create_camera(
    body: CameraFeedCreate,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    camera = CameraFeed(
        tenant_id=claims.tenant_id,
        client_id=body.client_id,
        site_id=body.site_id,
        asset_id=body.asset_id,
        name=body.name,
        stream_url=body.stream_url,
        stream_type=body.stream_type,
        location_description=body.location_description,
        floor=body.floor,
        zone=body.zone,
        ai_enabled=body.ai_enabled,
        face_recognition_enabled=body.face_recognition_enabled,
        threat_detection_enabled=body.threat_detection_enabled,
        person_tracking_enabled=body.person_tracking_enabled,
        processing_fps=body.processing_fps,
        detection_confidence_threshold=body.detection_confidence_threshold,
        roi_zones=body.roi_zones,
    )
    db.add(camera)
    await db.flush()
    await db.refresh(camera)
    return CameraFeedResponse.model_validate(camera)


@router.get("/cameras/{camera_id}", response_model=CameraFeedResponse)
async def get_camera(
    camera_id: UUID,
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CameraFeed).where(
            CameraFeed.id == camera_id,
            CameraFeed.tenant_id == claims.tenant_id,
        )
    )
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(404, "Camera not found")
    return CameraFeedResponse.model_validate(camera)


@router.patch("/cameras/{camera_id}", response_model=CameraFeedResponse)
async def update_camera(
    camera_id: UUID,
    body: CameraFeedUpdate,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CameraFeed).where(
            CameraFeed.id == camera_id,
            CameraFeed.tenant_id == claims.tenant_id,
        )
    )
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(404, "Camera not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(camera, field, value)
    await db.flush()
    await db.refresh(camera)
    return CameraFeedResponse.model_validate(camera)


@router.delete("/cameras/{camera_id}", response_model=MessageResponse)
async def delete_camera(
    camera_id: UUID,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CameraFeed).where(
            CameraFeed.id == camera_id,
            CameraFeed.tenant_id == claims.tenant_id,
        )
    )
    camera = result.scalar_one_or_none()
    if not camera:
        raise HTTPException(404, "Camera not found")
    await db.delete(camera)
    await db.flush()
    return MessageResponse(message="Camera deleted")


# ── Face Detections ───────────────────────────────────────────────────────────

@router.get("/detections/faces", response_model=PaginatedResponse[FaceDetectionResponse])
async def list_face_detections(
    camera_id: UUID | None = Query(None),
    person_id: UUID | None = Query(None),
    is_recognized: bool | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(FaceDetection).where(FaceDetection.tenant_id == claims.tenant_id)
    if camera_id:
        q = q.where(FaceDetection.camera_id == camera_id)
    if person_id:
        q = q.where(FaceDetection.person_id == person_id)
    if is_recognized is not None:
        q = q.where(FaceDetection.is_recognized == is_recognized)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(FaceDetection.created_at.desc())
    q = q.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
    rows = (await db.execute(q)).scalars().all()

    return PaginatedResponse(
        data=[FaceDetectionResponse.model_validate(r) for r in rows],
        total=total, page=pagination.page,
        limit=pagination.limit, pages=(total + pagination.limit - 1) // pagination.limit,
    )


# ── Threat Detections ─────────────────────────────────────────────────────────

@router.get("/threats", response_model=PaginatedResponse[ThreatDetectionResponse])
async def list_threats(
    camera_id: UUID | None = Query(None),
    threat_type: str | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(ThreatDetection).where(ThreatDetection.tenant_id == claims.tenant_id)
    if claims.client_id:
        q = q.where(ThreatDetection.client_id == claims.client_id)
    if camera_id:
        q = q.where(ThreatDetection.camera_id == camera_id)
    if threat_type:
        q = q.where(ThreatDetection.threat_type == threat_type)
    if severity:
        q = q.where(ThreatDetection.severity == severity)
    if status:
        q = q.where(ThreatDetection.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(ThreatDetection.created_at.desc())
    q = q.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
    rows = (await db.execute(q)).scalars().all()

    return PaginatedResponse(
        data=[ThreatDetectionResponse.model_validate(r) for r in rows],
        total=total, page=pagination.page,
        limit=pagination.limit, pages=(total + pagination.limit - 1) // pagination.limit,
    )


@router.patch("/threats/{threat_id}", response_model=ThreatDetectionResponse)
async def acknowledge_threat(
    threat_id: UUID,
    body: ThreatAcknowledge,
    claims: TokenClaims = Depends(require_permissions("vision:write")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ThreatDetection).where(
            ThreatDetection.id == threat_id,
            ThreatDetection.tenant_id == claims.tenant_id,
        )
    )
    threat = result.scalar_one_or_none()
    if not threat:
        raise HTTPException(404, "Threat not found")
    threat.status = body.status
    if body.status == "acknowledged":
        threat.acknowledged_by = claims.user_id
        threat.acknowledged_at = datetime.now(timezone.utc)
    elif body.status in ("resolved", "false_positive"):
        threat.resolved_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(threat)
    return ThreatDetectionResponse.model_validate(threat)


# ── Person Tracks ─────────────────────────────────────────────────────────────

@router.get("/tracks", response_model=PaginatedResponse[PersonTrackResponse])
async def list_person_tracks(
    site_id: UUID | None = Query(None),
    threat_level: str | None = Query(None),
    is_identified: bool | None = Query(None),
    active: bool | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    q = select(PersonTrack).where(PersonTrack.tenant_id == claims.tenant_id)
    if site_id:
        q = q.where(PersonTrack.site_id == site_id)
    if threat_level:
        q = q.where(PersonTrack.threat_level == threat_level)
    if is_identified is not None:
        q = q.where(PersonTrack.is_identified == is_identified)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(PersonTrack.last_seen_at.desc())
    q = q.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
    rows = (await db.execute(q)).scalars().all()

    return PaginatedResponse(
        data=[PersonTrackResponse.model_validate(r) for r in rows],
        total=total, page=pagination.page,
        limit=pagination.limit, pages=(total + pagination.limit - 1) // pagination.limit,
    )


# ── Vision Dashboard Stats ───────────────────────────────────────────────────

@router.get("/stats", response_model=VisionDashboardStats)
async def vision_dashboard_stats(
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    tenant_filter = CameraFeed.tenant_id == claims.tenant_id

    total_cameras = (await db.execute(
        select(func.count()).where(tenant_filter)
    )).scalar() or 0

    active_cameras = (await db.execute(
        select(func.count()).where(and_(tenant_filter, CameraFeed.status == "active"))
    )).scalar() or 0

    cameras_with_errors = (await db.execute(
        select(func.count()).where(and_(tenant_filter, CameraFeed.status == "error"))
    )).scalar() or 0

    authorized_persons = (await db.execute(
        select(func.count()).where(
            and_(AuthorizedPerson.tenant_id == claims.tenant_id, AuthorizedPerson.status == "active")
        )
    )).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    faces_detected_today = (await db.execute(
        select(func.count()).where(
            and_(FaceDetection.tenant_id == claims.tenant_id, FaceDetection.created_at >= today_start)
        )
    )).scalar() or 0

    unknown_faces_today = (await db.execute(
        select(func.count()).where(
            and_(
                FaceDetection.tenant_id == claims.tenant_id,
                FaceDetection.created_at >= today_start,
                FaceDetection.is_recognized == False,
            )
        )
    )).scalar() or 0

    active_threats = (await db.execute(
        select(func.count()).where(
            and_(
                ThreatDetection.tenant_id == claims.tenant_id,
                ThreatDetection.status.in_(["active", "acknowledged", "investigating"]),
            )
        )
    )).scalar() or 0

    threats_today = (await db.execute(
        select(func.count()).where(
            and_(ThreatDetection.tenant_id == claims.tenant_id, ThreatDetection.created_at >= today_start)
        )
    )).scalar() or 0

    active_tracks = (await db.execute(
        select(func.count()).where(
            and_(PersonTrack.tenant_id == claims.tenant_id, PersonTrack.last_seen_at >= today_start)
        )
    )).scalar() or 0

    return VisionDashboardStats(
        active_cameras=active_cameras,
        total_cameras=total_cameras,
        authorized_persons=authorized_persons,
        faces_detected_today=faces_detected_today,
        unknown_faces_today=unknown_faces_today,
        active_threats=active_threats,
        threats_today=threats_today,
        active_tracks=active_tracks,
        cameras_with_errors=cameras_with_errors,
    )
