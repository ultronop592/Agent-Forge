import os
import pytest
from unittest.mock import patch, MagicMock
from typing import List
from fastapi.testclient import TestClient

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Memory
from backend.app.database.memory_search import search_similar, _normalize_vector, _cosine_similarity
from backend.app.agents.memory_agent import MemoryAgent
from backend.app.api.memory import query_memory, memory_agent
from backend.app.main import app


def _make_vector(val: float, dim: int = 768) -> List[float]:
    v = [val] * dim
    return _normalize_vector(v)


def test_search_similar_top_k_sqlite():
    db = SessionLocal()
    try:
        q_vec = _make_vector(0.1)
        for i in range(10):
            mem = Memory(
                category="test_topk",
                content=f"Top-K memory item {i}",
                embedding=_make_vector(0.1 + i * 0.05)
            )
            db.add(mem)
        db.commit()

        results = search_similar(
            session=db,
            query_embedding=q_vec,
            k=3,
            min_similarity=0.1,
            category="test_topk"
        )
        assert len(results) == 3
        scores = [r["similarity_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
    finally:
        db.query(Memory).filter(Memory.category == "test_topk").delete()
        db.commit()
        db.close()


def test_search_similar_threshold_sqlite():
    db = SessionLocal()
    try:
        q_vec = _make_vector(1.0)
        high_vec = _make_vector(0.99)
        low_vec = [-x for x in q_vec]

        mem_high = Memory(category="test_thresh", content="High similarity item", embedding=high_vec)
        mem_low = Memory(category="test_thresh", content="Low similarity item", embedding=low_vec)
        db.add_all([mem_high, mem_low])
        db.commit()

        results = search_similar(
            session=db,
            query_embedding=q_vec,
            k=5,
            min_similarity=0.45,
            category="test_thresh"
        )
        assert len(results) == 1
        assert results[0]["content"] == "High similarity item"
        assert results[0]["similarity_score"] >= 0.45
    finally:
        db.query(Memory).filter(Memory.category == "test_thresh").delete()
        db.commit()
        db.close()


def test_search_similar_category_filter_sqlite():
    db = SessionLocal()
    try:
        q_vec = _make_vector(0.2)
        mem_cat1 = Memory(category="cat_alpha", content="Alpha item", embedding=q_vec)
        mem_cat2 = Memory(category="cat_beta", content="Beta item", embedding=q_vec)
        db.add_all([mem_cat1, mem_cat2])
        db.commit()

        results = search_similar(
            session=db,
            query_embedding=q_vec,
            k=5,
            min_similarity=0.1,
            category="cat_alpha"
        )
        assert len(results) >= 1
        assert all(r["category"] == "cat_alpha" for r in results)
    finally:
        db.query(Memory).filter(Memory.category.in_(["cat_alpha", "cat_beta"])).delete()
        db.commit()
        db.close()


def test_search_similar_wrong_dimension_raises():
    db = SessionLocal()
    try:
        with pytest.raises(ValueError, match="Expected 768-dim embedding"):
            search_similar(session=db, query_embedding=[0.1] * 100)

        with pytest.raises(ValueError, match="Expected 768-dim embedding"):
            search_similar(session=db, query_embedding=[0.1] * 1536)

        agent = MemoryAgent()
        with pytest.raises(ValueError, match="Expected 768-dim embedding"):
            agent.store_memory(content="Bad dimension", embedding=[0.1] * 256)
    finally:
        db.close()


def test_lexical_fallback_null_embedding_only():
    db = SessionLocal()
    try:
        q_vec = _make_vector(0.3)
        mem_null = Memory(
            category="test_lex_null",
            content="PostgreSQL optimization indexing architecture",
            embedding=None
        )
        mem_vec = Memory(
            category="test_lex_null",
            content="PostgreSQL optimization indexing architecture with vector",
            embedding=[-x for x in q_vec]
        )
        db.add_all([mem_null, mem_vec])
        db.commit()

        results = search_similar(
            session=db,
            query_embedding=q_vec,
            k=5,
            min_similarity=0.2,
            category="test_lex_null",
            query_text="PostgreSQL optimization indexing"
        )
        assert len(results) == 1
        assert results[0]["id"] == mem_null.id
        assert results[0]["embedding"] is None
    finally:
        db.query(Memory).filter(Memory.category == "test_lex_null").delete()
        db.commit()
        db.close()


def test_lexical_fallback_cap():
    db = SessionLocal()
    try:
        q_vec = _make_vector(0.4)
        mems = [
            Memory(category="test_cap", content=f"Cap item unique keyword target {i}", embedding=None)
            for i in range(250)
        ]
        db.add_all(mems)
        db.commit()

        results = search_similar(
            session=db,
            query_embedding=q_vec,
            k=300,
            min_similarity=0.1,
            category="test_cap",
            query_text="unique keyword target"
        )
        assert len(results) <= 200
    finally:
        db.query(Memory).filter(Memory.category == "test_cap").delete()
        db.commit()
        db.close()


def test_memory_agent_uses_search_similar():
    agent = MemoryAgent()
    with patch.object(agent, "get_embedding", return_value=_make_vector(0.1)):
        with patch("backend.app.agents.memory_agent.search_similar", return_value=[{"id": "mock_id", "content": "mock"}]) as mock_search:
            results, q_vec = agent.retrieve_memories(query="test query", category="factual", top_k=5, min_score=0.45)
            assert mock_search.called
            assert len(results) == 1
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["k"] == 5
            assert call_kwargs["min_similarity"] == 0.45
            assert call_kwargs["category"] == "factual"
            assert len(call_kwargs["query_embedding"]) == 768


def test_api_memory_uses_search_similar():
    db = SessionLocal()
    try:
        with patch.object(memory_agent, "get_embedding", return_value=_make_vector(0.1)):
            with patch("backend.app.api.memory.search_similar", return_value=[{"id": "api_mem_id", "content": "api content", "category": "factual"}]) as mock_search:
                res = query_memory(query="test", category="factual", user_id="u123", db=db)
                assert len(res) == 1
                assert mock_search.called
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["k"] == 50
                assert call_kwargs["category"] == "factual"
                assert call_kwargs["user_id"] == "u123"
    finally:
        db.close()


def test_parity_sqlite_vs_numpy():
    db = SessionLocal()
    try:
        import random
        import math
        rng = random.Random(42)
        def rand_vec(dim: int = 768) -> List[float]:
            raw = [rng.gauss(0, 1) for _ in range(dim)]
            norm = math.sqrt(sum(x * x for x in raw))
            return [x / norm for x in raw]

        q_norm = rand_vec()

        sample_vectors = []
        for i in range(15):
            vec_norm = rand_vec()
            mem = Memory(
                category="test_parity",
                content=f"Parity item {i}",
                embedding=vec_norm
            )
            db.add(mem)
            expected_sim = sum(a * b for a, b in zip(q_norm, vec_norm))
            sample_vectors.append((i, mem, expected_sim))

        db.commit()

        results = search_similar(
            session=db,
            query_embedding=q_norm,
            k=5,
            min_similarity=0.0,
            category="test_parity"
        )

        sample_vectors.sort(key=lambda x: x[2], reverse=True)
        top5_expected = sample_vectors[:5]

        assert len(results) == 5
        for res, exp in zip(results, top5_expected):
            assert res["content"] == exp[1].content
            assert abs(res["similarity_score"] - exp[2]) < 1e-3
    finally:
        db.query(Memory).filter(Memory.category == "test_parity").delete()
        db.commit()
        db.close()


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL", "").startswith("postgresql"),
    reason="PostgreSQL with pgvector required (TEST_DATABASE_URL)"
)
def test_postgres_hnsw_index_used():
    from sqlalchemy import create_engine, text
    pg_url = os.environ["TEST_DATABASE_URL"]
    engine = create_engine(pg_url)
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("SET LOCAL enable_seqscan = off;"))
            dummy_vec = "[" + ",".join(["0.01"] * 768) + "]"
            plan_rows = conn.execute(text(
                f"EXPLAIN (FORMAT TEXT) SELECT id FROM memories ORDER BY embedding <=> '{dummy_vec}'::vector LIMIT 5;"
            )).fetchall()
            plan_text = "\n".join(r[0] for r in plan_rows)
            assert "ix_memories_embedding_hnsw" in plan_text
