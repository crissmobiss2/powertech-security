"""
Semantic incident search using sentence-transformers.

Encodes incident text to 384-dim dense embeddings, enabling:
- "Find incidents similar to this threat description"
- Pattern recognition across historical incidents
- SOC analyst workflow: "what happened last time someone loitered near Gate 3?"

Model: sentence-transformers/all-MiniLM-L6-v2
  - 80MB, fast CPU inference, 384-dim embeddings
  - State-of-the-art on semantic textual similarity benchmarks

Falls back to TF-IDF keyword matching if sentence-transformers unavailable.
"""
import logging
import re
import time
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MAX_INDEXED_INCIDENTS = 10_000
SIMILARITY_THRESHOLD = 0.50

_model = None


def _load_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_ID)
        logger.info("Sentence-transformer loaded: %s", MODEL_ID)
    except ImportError:
        logger.warning("sentence-transformers not installed — falling back to TF-IDF")
    except Exception as e:
        logger.error("Sentence-transformer load failed: %s", e)
    return _model


@dataclass
class IncidentIndex:
    """In-memory vector index for fast similarity search."""
    ids: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    embeddings: list[np.ndarray] = field(default_factory=list)
    metadata: list[dict] = field(default_factory=list)

    def add(self, incident_id: str, text: str, embedding: np.ndarray, meta: dict):
        self.ids.append(incident_id)
        self.texts.append(text)
        self.embeddings.append(embedding)
        self.metadata.append(meta)

        if len(self.ids) > MAX_INDEXED_INCIDENTS:
            cutoff = len(self.ids) - MAX_INDEXED_INCIDENTS
            self.ids = self.ids[cutoff:]
            self.texts = self.texts[cutoff:]
            self.embeddings = self.embeddings[cutoff:]
            self.metadata = self.metadata[cutoff:]

    def search(self, query_embedding: np.ndarray, top_k: int = 10) -> list[dict]:
        if not self.embeddings:
            return []
        matrix = np.stack(self.embeddings)
        q = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8
        scores = (matrix / norms) @ q

        top_indices = np.argsort(scores)[::-1][:top_k]
        return [
            {
                "incident_id": self.ids[i],
                "similarity": round(float(scores[i]), 4),
                "text_snippet": self.texts[i][:200],
                "metadata": self.metadata[i],
                "match": float(scores[i]) >= SIMILARITY_THRESHOLD,
            }
            for i in top_indices
            if float(scores[i]) > 0
        ]


class SemanticSearchService:
    """Semantic similarity search over security incidents."""

    def __init__(self):
        self._index = IncidentIndex()
        self._tfidf_corpus: list[str] = []
        self._tfidf_ids: list[str] = []
        self._tfidf_meta: list[dict] = []

    def _incident_to_text(self, incident: dict) -> str:
        """Flatten incident dict to a single searchable string."""
        parts = []
        for key in ("title", "type", "description", "location", "severity", "notes"):
            val = incident.get(key)
            if val:
                parts.append(str(val))
        return " | ".join(parts)

    def _encode(self, text: str) -> np.ndarray | None:
        model = _load_model()
        if model is None:
            return None
        try:
            return model.encode(text, normalize_embeddings=True)
        except Exception as e:
            logger.debug("Encode failed: %s", e)
            return None

    def index_incident(self, incident_id: str, incident: dict) -> bool:
        """Add or update an incident in the search index."""
        text = self._incident_to_text(incident)
        meta = {
            "severity": incident.get("severity"),
            "type": incident.get("type"),
            "status": incident.get("status"),
            "created_at": incident.get("created_at"),
        }

        embedding = self._encode(text)
        if embedding is not None:
            self._index.add(incident_id, text, embedding, meta)
            return True

        # TF-IDF fallback index
        self._tfidf_corpus.append(text)
        self._tfidf_ids.append(incident_id)
        self._tfidf_meta.append(meta)
        return False

    def index_batch(self, incidents: list[dict]) -> int:
        """Batch index incidents. Returns count indexed."""
        model = _load_model()
        if model is not None:
            texts = [self._incident_to_text(i) for i in incidents]
            try:
                embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
                for incident, text, emb in zip(incidents, texts, embeddings):
                    iid = str(incident.get("id", ""))
                    meta = {
                        "severity": incident.get("severity"),
                        "type": incident.get("type"),
                        "status": incident.get("status"),
                    }
                    self._index.add(iid, text, emb, meta)
                return len(incidents)
            except Exception as e:
                logger.error("Batch encode failed: %s", e)

        for incident in incidents:
            iid = str(incident.get("id", ""))
            text = self._incident_to_text(incident)
            meta = {"severity": incident.get("severity"), "type": incident.get("type")}
            self._tfidf_corpus.append(text)
            self._tfidf_ids.append(iid)
            self._tfidf_meta.append(meta)
        return len(incidents)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Find incidents semantically similar to a query.
        Falls back to TF-IDF keyword search if model unavailable.
        """
        embedding = self._encode(query)
        if embedding is not None:
            return self._index.search(embedding, top_k)
        return self._tfidf_search(query, top_k)

    def _tfidf_search(self, query: str, top_k: int) -> list[dict]:
        """Simple keyword overlap fallback."""
        if not self._tfidf_corpus:
            return []
        query_terms = set(re.sub(r"[^\w\s]", "", query.lower()).split())
        results = []
        for i, text in enumerate(self._tfidf_corpus):
            doc_terms = set(re.sub(r"[^\w\s]", "", text.lower()).split())
            overlap = len(query_terms & doc_terms)
            if overlap > 0:
                score = overlap / max(len(query_terms), 1)
                results.append({
                    "incident_id": self._tfidf_ids[i],
                    "similarity": round(score, 4),
                    "text_snippet": text[:200],
                    "metadata": self._tfidf_meta[i],
                    "match": score >= 0.3,
                })
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def index_stats(self) -> dict:
        return {
            "vector_indexed": len(self._index.ids),
            "tfidf_indexed": len(self._tfidf_ids),
            "total": len(self._index.ids) + len(self._tfidf_ids),
            "model_loaded": _model is not None,
        }


_tenants: dict[str, SemanticSearchService] = {}


def get_semantic_search_service(tenant_id: str = "default") -> SemanticSearchService:
    if tenant_id not in _tenants:
        _tenants[tenant_id] = SemanticSearchService()
    return _tenants[tenant_id]
