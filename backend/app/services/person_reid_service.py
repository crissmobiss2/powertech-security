"""
Cross-camera person re-identification using InsightFace embeddings + ByteTrack.

Architecture:
- ByteTrack (via supervision) handles frame-to-frame tracking within one camera
- InsightFace 512-dim ArcFace embeddings enable cross-camera person matching
- ReID gallery: (person_id → list of embeddings) keyed by tenant+camera
- Cosine similarity (threshold 0.65) links tracks across cameras

This uses models already in the stack (InsightFace + supervision/ByteTrack)
rather than torchreid, avoiding heavy additional GPU dependencies.
"""
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

import numpy as np

logger = logging.getLogger(__name__)

REID_COSINE_THRESHOLD = 0.65     # cross-camera match threshold
TRACK_TIMEOUT_S = 300.0          # drop inactive tracks after 5 minutes
MAX_EMBEDDINGS_PER_PERSON = 20   # rolling gallery per ReID identity


@dataclass
class ReIDTrack:
    """A tracked person across one or more cameras."""
    reid_id: str
    camera_ids: list[str]
    embeddings: list[np.ndarray]
    first_seen: float
    last_seen: float
    track_ids: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))


class PersonReIDService:
    """
    Cross-camera person re-identification.
    One instance per tenant.
    """

    def __init__(self):
        self._gallery: dict[str, ReIDTrack] = {}    # reid_id → ReIDTrack
        self._camera_trackers: dict[str, object] = {}  # camera_id → sv.ByteTrack

    # ── ByteTrack per-camera frame tracking ──────────────────────────────────

    def _get_tracker(self, camera_id: str):
        if camera_id not in self._camera_trackers:
            try:
                import supervision as sv
                self._camera_trackers[camera_id] = sv.ByteTrack(
                    frame_rate=30,
                    track_activation_threshold=0.3,
                    lost_track_buffer=120,
                    minimum_matching_threshold=0.8,
                )
            except ImportError:
                logger.warning("supervision not installed — ByteTrack unavailable")
                self._camera_trackers[camera_id] = None
        return self._camera_trackers[camera_id]

    def update_tracks(
        self,
        camera_id: str,
        detections: "np.ndarray",  # [[x1,y1,x2,y2,conf,cls], ...]
    ) -> list[dict]:
        """
        Feed YOLO detections into ByteTrack. Returns active track list.

        Args:
            camera_id: camera identifier
            detections: YOLO output array shape (N, 6)

        Returns:
            list of {track_id, bbox, confidence, class_id}
        """
        tracker = self._get_tracker(camera_id)
        if tracker is None or len(detections) == 0:
            return []

        try:
            import supervision as sv

            sv_dets = sv.Detections(
                xyxy=detections[:, :4],
                confidence=detections[:, 4],
                class_id=detections[:, 5].astype(int),
            )
            tracked = tracker.update_with_detections(sv_dets)

            results = []
            for i in range(len(tracked)):
                results.append({
                    "track_id": int(tracked.tracker_id[i]),
                    "bbox": tracked.xyxy[i].tolist(),
                    "confidence": float(tracked.confidence[i]) if tracked.confidence is not None else 1.0,
                    "class_id": int(tracked.class_id[i]) if tracked.class_id is not None else 0,
                    "camera_id": camera_id,
                })
            return results
        except Exception as e:
            logger.debug("ByteTrack update error: %s", e)
            return []

    # ── Cross-camera ReID ─────────────────────────────────────────────────────

    def register_embedding(
        self,
        camera_id: str,
        track_id: int,
        embedding: np.ndarray,
    ) -> str:
        """
        Register a face/person embedding for a tracked person.
        Attempts to match against the gallery; creates a new ReID entry if no match.

        Returns: reid_id (stable cross-camera person identifier)
        """
        self._prune_stale()
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)

        best_id, best_sim = self._find_match(embedding)

        if best_id and best_sim >= REID_COSINE_THRESHOLD:
            track = self._gallery[best_id]
            track.embeddings.append(embedding)
            if len(track.embeddings) > MAX_EMBEDDINGS_PER_PERSON:
                track.embeddings = track.embeddings[-MAX_EMBEDDINGS_PER_PERSON:]
            if camera_id not in track.camera_ids:
                track.camera_ids.append(camera_id)
            track.track_ids[camera_id].append(track_id)
            track.last_seen = time.monotonic()
            return best_id
        else:
            reid_id = str(uuid4())
            self._gallery[reid_id] = ReIDTrack(
                reid_id=reid_id,
                camera_ids=[camera_id],
                embeddings=[embedding],
                first_seen=time.monotonic(),
                last_seen=time.monotonic(),
                track_ids=defaultdict(list, {camera_id: [track_id]}),
            )
            return reid_id

    def _find_match(self, embedding: np.ndarray) -> tuple[Optional[str], float]:
        best_id: Optional[str] = None
        best_sim = -1.0
        for reid_id, track in self._gallery.items():
            # Compare against mean of stored embeddings
            gallery_embeds = np.stack(track.embeddings)
            mean_embed = gallery_embeds.mean(axis=0)
            mean_embed = mean_embed / (np.linalg.norm(mean_embed) + 1e-8)
            sim = float(np.dot(embedding, mean_embed))
            if sim > best_sim:
                best_sim = sim
                best_id = reid_id
        return best_id, best_sim

    def query_person(self, embedding: np.ndarray, top_k: int = 5) -> list[dict]:
        """Find top-K matching persons in the gallery."""
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        self._prune_stale()
        results = []
        for reid_id, track in self._gallery.items():
            gallery_embeds = np.stack(track.embeddings)
            mean_embed = gallery_embeds.mean(axis=0)
            mean_embed = mean_embed / (np.linalg.norm(mean_embed) + 1e-8)
            sim = float(np.dot(embedding, mean_embed))
            results.append({
                "reid_id": reid_id,
                "similarity": round(sim, 4),
                "camera_ids": track.camera_ids,
                "first_seen": track.first_seen,
                "last_seen": track.last_seen,
                "match": sim >= REID_COSINE_THRESHOLD,
            })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def get_camera_footprint(self, reid_id: str) -> dict | None:
        """Get all cameras where this person was seen."""
        track = self._gallery.get(reid_id)
        if not track:
            return None
        return {
            "reid_id": reid_id,
            "cameras": track.camera_ids,
            "track_ids_by_camera": dict(track.track_ids),
            "first_seen": track.first_seen,
            "last_seen": track.last_seen,
            "embedding_count": len(track.embeddings),
        }

    def get_gallery_summary(self) -> dict:
        self._prune_stale()
        return {
            "total_persons": len(self._gallery),
            "camera_count": len(self._camera_trackers),
            "persons": [
                {
                    "reid_id": rid,
                    "cameras": t.camera_ids,
                    "last_seen_ago_s": round(time.monotonic() - t.last_seen),
                }
                for rid, t in list(self._gallery.items())[:50]
            ],
        }

    def _prune_stale(self):
        now = time.monotonic()
        stale = [rid for rid, t in self._gallery.items() if now - t.last_seen > TRACK_TIMEOUT_S]
        for rid in stale:
            del self._gallery[rid]


_tenants: dict[str, PersonReIDService] = {}


def get_reid_service(tenant_id: str = "default") -> PersonReIDService:
    if tenant_id not in _tenants:
        _tenants[tenant_id] = PersonReIDService()
    return _tenants[tenant_id]
