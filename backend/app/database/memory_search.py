import os
import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:
    _HAS_NUMPY = False

from backend.app.database.models import Memory

logger = logging.getLogger("agentforge.database.memory_search")


def _normalize_vector(v: List[float]) -> List[float]:
    norm = sum(x * x for x in v) ** 0.5
    if norm == 0.0:
        return v
    return [x / norm for x in v]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    if _HAS_NUMPY:
        try:
            va = np.array(a, dtype=np.float32)
            vb = np.array(b, dtype=np.float32)
            denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
            if denom == 0.0:
                return 0.0
            return float(np.dot(va, vb) / denom)
        except Exception:
            pass
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def search_similar(
    session: Session,
    query_embedding: List[float],
    k: int = 5,
    min_similarity: float = 0.45,
    category: Optional[str] = None,
    user_id: Optional[str] = None,
    query_text: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if len(query_embedding) != 768:
        raise ValueError(f"Expected 768-dim embedding, got {len(query_embedding)}")

    normalized_query = _normalize_vector(query_embedding)

    is_postgres = False
    try:
        bind = getattr(session, "bind", None)
        if bind is None and hasattr(session, "get_bind"):
            bind = session.get_bind()
        if bind is not None and hasattr(bind, "dialect"):
            is_postgres = (bind.dialect.name == "postgresql")
    except Exception:
        is_postgres = False

    results: List[Dict[str, Any]] = []

    if is_postgres and hasattr(Memory, "embedding"):
        try:
            ef_search = os.environ.get("HNSW_EF_SEARCH")
            if ef_search:
                try:
                    ef_val = int(ef_search)
                    session.execute(text(f"SET LOCAL hnsw.ef_search = {ef_val}"))
                except Exception as ef_err:
                    logger.warning(f"Could not set hnsw.ef_search: {ef_err}")

            # ORDER BY uses the pgvector <=> cosine distance operator directly with LIMIT
            # to ensure the ix_memories_embedding_hnsw index can be used by the query planner.
            # The similarity threshold is applied in Python on the returned top-k candidates
            # to avoid index-scan defeat caused by expression wrapping or distance predicates.
            dist_expr = Memory.embedding.cosine_distance(normalized_query)
            q = session.query(Memory, dist_expr.label("distance")).filter(Memory.embedding.isnot(None))

            if category and category.strip() and category.strip().lower() != "all":
                q = q.filter(Memory.category == category.strip())

            if user_id is not None and hasattr(Memory, "user_id"):
                q = q.filter(getattr(Memory, "user_id") == user_id)

            candidates = q.order_by(dist_expr.asc()).limit(k).all()

            for mem, dist in candidates:
                distance_val = float(dist) if dist is not None else 1.0
                sim_score = max(0.0, min(1.0, 1.0 - distance_val))
                if sim_score >= min_similarity:
                    mem_dict = mem.to_dict()
                    mem_dict["similarity_score"] = round(sim_score, 4)
                    mem_dict["match_percentage"] = f"{int(round(sim_score * 100))}%"
                    results.append(mem_dict)

            if len(results) >= k or not query_text:
                return results

        except Exception as pg_err:
            logger.warning(f"Native pgvector query failed, falling back to python scan: {pg_err}")
            results = []

    if not results:
        q_sqlite = session.query(
            Memory.id,
            Memory.category,
            Memory.content,
            Memory.embedding,
            Memory.embedding_searchable_text,
            Memory.created_at
        )

        if category and category.strip() and category.strip().lower() != "all":
            q_sqlite = q_sqlite.filter(Memory.category == category.strip())

        if user_id is not None and hasattr(Memory, "user_id"):
            q_sqlite = q_sqlite.filter(getattr(Memory, "user_id") == user_id)

        rows = q_sqlite.all()

        scored_candidates = []
        for r in rows:
            emb = r.embedding
            vec = None
            if emb is not None:
                if isinstance(emb, (list, tuple)) and len(emb) > 0:
                    vec = list(emb)
                elif isinstance(emb, str):
                    try:
                        parsed = json.loads(emb)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            vec = parsed
                    except Exception:
                        pass

            if vec is None and r.embedding_searchable_text:
                try:
                    parsed = json.loads(r.embedding_searchable_text)
                    if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], (int, float)):
                        vec = parsed
                except Exception:
                    pass

            if vec is not None:
                score = _cosine_similarity(normalized_query, _normalize_vector(vec))
                if score >= min_similarity:
                    mem_dict = {
                        "id": r.id,
                        "category": r.category,
                        "content": r.content,
                        "embedding_searchable_text": r.embedding_searchable_text,
                        "embedding": vec,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "similarity_score": round(score, 4),
                        "match_percentage": f"{int(round(score * 100))}%"
                    }
                    scored_candidates.append((score, mem_dict))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        results = [item[1] for item in scored_candidates[:k]]

    if len(results) < k and query_text and query_text.strip():
        needed = k - len(results)
        existing_ids = {r["id"] for r in results}
        lex_q = session.query(
            Memory.id,
            Memory.category,
            Memory.content,
            Memory.embedding_searchable_text,
            Memory.created_at
        ).filter(Memory.embedding.is_(None))

        if category and category.strip() and category.strip().lower() != "all":
            lex_q = lex_q.filter(Memory.category == category.strip())

        if user_id is not None and hasattr(Memory, "user_id"):
            lex_q = lex_q.filter(getattr(Memory, "user_id") == user_id)

        null_rows = lex_q.limit(200).all()

        words = [w.lower() for w in query_text.strip().split() if len(w) > 2]
        lex_matches = []
        for r in null_rows:
            if r.id in existing_ids:
                continue
            content_lower = (r.content or "").lower()
            if not words:
                continue
            matches = sum(1 for w in words if w in content_lower)
            if matches > 0:
                score = min(1.0, (matches / len(words)) * 0.8)
                if score >= min_similarity:
                    lex_matches.append((score, r))

        lex_matches.sort(key=lambda x: x[0], reverse=True)
        for score, r in lex_matches[:needed]:
            results.append({
                "id": r.id,
                "category": r.category,
                "content": r.content,
                "embedding_searchable_text": r.embedding_searchable_text,
                "embedding": None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "similarity_score": round(score, 4),
                "match_percentage": f"{int(round(score * 100))}%"
            })

    return results
