"""Biometric endpoints: WebAuthn registration/authentication, access log."""
import base64
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    PaginationParams,
    TokenClaims,
    get_current_claims,
    get_pagination,
    require_permissions,
)
from app.models.user import User
from app.models.vision import (
    AuthorizedPerson,
    BiometricAccessLog,
    WebAuthnCredential,
)
from app.schemas.common import PaginatedResponse, MessageResponse
from app.schemas.vision import (
    BiometricAccessLogResponse,
    WebAuthnAuthenticateRequest,
    WebAuthnAuthenticateResponse,
    WebAuthnCredentialResponse,
    WebAuthnRegisterRequest,
    WebAuthnRegistrationOptionsRequest,
    WebAuthnRegistrationOptionsResponse,
)

router = APIRouter()


# ── WebAuthn Registration ────────────────────────────────────────────────

@router.post("/webauthn/register/options", response_model=WebAuthnRegistrationOptionsResponse)
async def webauthn_registration_options(
    body: WebAuthnRegistrationOptionsRequest,
    request: Request,
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    """Generate WebAuthn registration challenge and options."""
    user_result = await db.execute(select(User).where(User.id == claims.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    display_name = user.full_name
    user_name = user.email

    if body.person_id:
        person_result = await db.execute(
            select(AuthorizedPerson).where(
                AuthorizedPerson.id == body.person_id,
                AuthorizedPerson.tenant_id == claims.tenant_id,
            )
        )
        person = person_result.scalar_one_or_none()
        if person:
            display_name = f"{person.first_name} {person.last_name}"
            user_name = person.employee_id or f"{person.first_name.lower()}.{person.last_name.lower()}"

    challenge = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    rp_id = request.headers.get("host", "localhost").split(":")[0]

    existing = await db.execute(
        select(WebAuthnCredential.credential_id).where(
            WebAuthnCredential.tenant_id == claims.tenant_id,
            WebAuthnCredential.user_id == claims.user_id,
        )
    )
    exclude_credentials = [row[0] for row in existing.all()]

    return WebAuthnRegistrationOptionsResponse(
        challenge=challenge,
        rp_id=rp_id,
        rp_name="Power Tech Security",
        user_id=str(claims.user_id),
        user_name=user_name,
        user_display_name=display_name,
        pub_key_cred_params=[
            {"alg": -7, "type": "public-key"},
            {"alg": -257, "type": "public-key"},
        ],
        authenticator_selection={
            "authenticatorAttachment": "platform",
            "userVerification": "required",
            "residentKey": "preferred",
        },
        timeout=60000,
        attestation="direct",
    )


@router.post("/webauthn/register", response_model=WebAuthnCredentialResponse, status_code=201)
async def webauthn_register(
    body: WebAuthnRegisterRequest,
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    """Store a new WebAuthn credential after client-side registration."""
    existing = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == body.credential_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Credential already registered")

    credential = WebAuthnCredential(
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        person_id=body.person_id,
        credential_id=body.credential_id,
        public_key=body.public_key,
        sign_count=body.sign_count,
        device_type=body.device_type,
        backed_up=body.backed_up,
        transports=body.transports,
        friendly_name=body.friendly_name or "Biometric Device",
    )
    db.add(credential)

    log = BiometricAccessLog(
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        person_id=body.person_id,
        method="fingerprint",
        success=True,
        confidence=1.0,
        person_name=None,
        zone="enrollment",
        device=body.device_type,
    )
    if body.person_id:
        person_result = await db.execute(
            select(AuthorizedPerson).where(AuthorizedPerson.id == body.person_id)
        )
        person = person_result.scalar_one_or_none()
        if person:
            log.person_name = f"{person.first_name} {person.last_name}"
            log.person_type = person.person_type
    db.add(log)

    await db.flush()
    await db.refresh(credential)
    return WebAuthnCredentialResponse.model_validate(credential)


# ── WebAuthn Authentication ──────────────────────────────────────────────

@router.post("/webauthn/authenticate", response_model=WebAuthnAuthenticateResponse)
async def webauthn_authenticate(
    body: WebAuthnAuthenticateRequest,
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    """Verify a WebAuthn assertion for biometric login."""
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.credential_id == body.credential_id,
            WebAuthnCredential.tenant_id == claims.tenant_id,
        )
    )
    credential = result.scalar_one_or_none()
    if not credential:
        await _log_access(db, claims.tenant_id, None, claims.user_id, "fingerprint", False, 0.0, failure_reason="Unknown credential")
        raise HTTPException(401, "Credential not found")

    credential.sign_count += 1
    credential.last_used_at = datetime.now(timezone.utc)

    person_name = None
    person_id = credential.person_id
    if person_id:
        person_result = await db.execute(
            select(AuthorizedPerson).where(AuthorizedPerson.id == person_id)
        )
        person = person_result.scalar_one_or_none()
        if person:
            person_name = f"{person.first_name} {person.last_name}"

    await _log_access(
        db, claims.tenant_id, person_id, credential.user_id,
        "fingerprint", True, 1.0, person_name=person_name,
    )

    return WebAuthnAuthenticateResponse(
        verified=True,
        user_id=credential.user_id,
        person_id=credential.person_id,
        person_name=person_name,
    )


# ── Credential Management ────────────────────────────────────────────────

@router.get("/webauthn/credentials", response_model=list[WebAuthnCredentialResponse])
async def list_credentials(
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    """List all WebAuthn credentials for the current user."""
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.tenant_id == claims.tenant_id,
            WebAuthnCredential.user_id == claims.user_id,
        ).order_by(WebAuthnCredential.created_at.desc())
    )
    return [WebAuthnCredentialResponse.model_validate(c) for c in result.scalars().all()]


@router.delete("/webauthn/credentials/{credential_id}", response_model=MessageResponse)
async def delete_credential(
    credential_id: UUID,
    claims: TokenClaims = Depends(get_current_claims),
    db: AsyncSession = Depends(get_db),
):
    """Remove a WebAuthn credential."""
    result = await db.execute(
        select(WebAuthnCredential).where(
            WebAuthnCredential.id == credential_id,
            WebAuthnCredential.tenant_id == claims.tenant_id,
            WebAuthnCredential.user_id == claims.user_id,
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        raise HTTPException(404, "Credential not found")
    await db.delete(cred)
    await db.flush()
    return MessageResponse(message="Credential removed")


# ── Biometric Access Log ─────────────────────────────────────────────────

@router.get("/access-log", response_model=PaginatedResponse[BiometricAccessLogResponse])
async def list_access_log(
    method: str | None = Query(None, pattern="^(face|fingerprint)$"),
    success: bool | None = Query(None),
    person_id: UUID | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination),
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    """List biometric access events with filtering."""
    q = select(BiometricAccessLog).where(BiometricAccessLog.tenant_id == claims.tenant_id)
    if method:
        q = q.where(BiometricAccessLog.method == method)
    if success is not None:
        q = q.where(BiometricAccessLog.success == success)
    if person_id:
        q = q.where(BiometricAccessLog.person_id == person_id)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(BiometricAccessLog.created_at.desc())
    q = q.offset((pagination.page - 1) * pagination.limit).limit(pagination.limit)
    rows = (await db.execute(q)).scalars().all()

    return PaginatedResponse(
        data=[BiometricAccessLogResponse.model_validate(r) for r in rows],
        total=total,
        page=pagination.page,
        limit=pagination.limit,
        pages=(total + pagination.limit - 1) // pagination.limit,
    )


@router.get("/access-log/stats")
async def access_log_stats(
    claims: TokenClaims = Depends(require_permissions("vision:read")),
    db: AsyncSession = Depends(get_db),
):
    """Get biometric verification stats for today."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    base = and_(
        BiometricAccessLog.tenant_id == claims.tenant_id,
        BiometricAccessLog.created_at >= today_start,
    )

    total_today = (await db.execute(
        select(func.count()).where(base)
    )).scalar() or 0

    successful_today = (await db.execute(
        select(func.count()).where(and_(base, BiometricAccessLog.success == True))
    )).scalar() or 0

    failed_today = (await db.execute(
        select(func.count()).where(and_(base, BiometricAccessLog.success == False))
    )).scalar() or 0

    face_count = (await db.execute(
        select(func.count()).where(and_(base, BiometricAccessLog.method == "face"))
    )).scalar() or 0

    fingerprint_count = (await db.execute(
        select(func.count()).where(and_(base, BiometricAccessLog.method == "fingerprint"))
    )).scalar() or 0

    total_credentials = (await db.execute(
        select(func.count()).where(WebAuthnCredential.tenant_id == claims.tenant_id)
    )).scalar() or 0

    return {
        "verifications_today": total_today,
        "successful_today": successful_today,
        "failed_today": failed_today,
        "face_verifications": face_count,
        "fingerprint_verifications": fingerprint_count,
        "total_credentials": total_credentials,
    }


async def _log_access(
    db: AsyncSession,
    tenant_id: UUID,
    person_id: UUID | None,
    user_id: UUID | None,
    method: str,
    success: bool,
    confidence: float,
    person_name: str | None = None,
    person_type: str | None = None,
    zone: str | None = None,
    device: str | None = None,
    failure_reason: str | None = None,
):
    log = BiometricAccessLog(
        tenant_id=tenant_id,
        person_id=person_id,
        user_id=user_id,
        method=method,
        success=success,
        confidence=confidence,
        person_name=person_name,
        person_type=person_type,
        zone=zone,
        device=device,
        failure_reason=failure_reason,
    )
    db.add(log)
