import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.dialects import postgresql
from backend.app.agents.memory_agent import MemoryAgent
from backend.app.database.models import Memory
from backend.app.database.connection import SessionLocal

def test_cosine_similarity_identical():
    agent = MemoryAgent()
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0, 3.0]
    score = agent._cosine_similarity(vec_a, vec_b)
    assert abs(score - 1.0) < 1e-4

def test_cosine_similarity_orthogonal():
    agent = MemoryAgent()
    vec_a = [1.0, 0.0]
    vec_b = [0.0, 1.0]
    score = agent._cosine_similarity(vec_a, vec_b)
    assert abs(score - 0.0) < 1e-4

def test_cosine_similarity_mismatched_length():
    agent = MemoryAgent()
    assert agent._cosine_similarity([1.0, 2.0], [1.0]) == 0.0

def test_store_memory_populates_embedding_and_text():
    agent = MemoryAgent()
    test_vec = [0.25] * 768
    result = agent.store_memory(
        content="Pgvector enables 100x fast vector indexing in PostgreSQL",
        category="architecture",
        embedding=test_vec
    )
    assert "id" in result
    assert result["category"] == "architecture"
    assert result["content"] == "Pgvector enables 100x fast vector indexing in PostgreSQL"
    assert result["embedding"] is not None
    assert len(result["embedding"]) == 768
    assert result["embedding_searchable_text"] is not None

def test_retrieve_memories_similarity_ranking():
    agent = MemoryAgent()
    cat = "test_ranking_cat"

    # Store target memory and dissimilar memory
    vec_target = [0.5] * 768
    vec_dissimilar = [-0.5] * 768

    agent.store_memory("High relevance vector document", category=cat, embedding=vec_target)
    agent.store_memory("Opposite vector document", category=cat, embedding=vec_dissimilar)

    # Patch get_embedding to return vec_target
    with patch.object(agent, "get_embedding", return_value=vec_target):
        results, query_vec = agent.retrieve_memories(
            query="Find relevant document",
            category=cat,
            top_k=5,
            min_score=0.10
        )

    assert len(results) >= 1
    # First result should be the high relevance document
    assert results[0]["content"] == "High relevance vector document"
    assert results[0]["similarity_score"] > 0.9

def test_retrieve_memories_category_filtering():
    agent = MemoryAgent()
    cat_target = "cat_filter_target"
    cat_other = "cat_filter_other"

    vec = [0.3] * 768
    agent.store_memory("Target category memory", category=cat_target, embedding=vec)
    agent.store_memory("Other category memory", category=cat_other, embedding=vec)

    with patch.object(agent, "get_embedding", return_value=vec):
        results, _ = agent.retrieve_memories(
            query="Search",
            category=cat_target,
            top_k=10,
            min_score=0.10
        )

    assert len(results) >= 1
    assert all(r["category"] == cat_target for r in results)

def test_pgvector_sql_generation():
    """Verify that Memory.embedding.cosine_distance compiles with pgvector's <=> operator on PostgreSQL."""
    query_vector = [0.1] * 768
    dist_expr = Memory.embedding.cosine_distance(query_vector)
    sim_expr = (1.0 - dist_expr).label("similarity_score")

    db = SessionLocal()
    try:
        q = db.query(Memory, sim_expr).filter(Memory.embedding.isnot(None)).order_by(dist_expr.asc()).limit(5)
        compiled_sql = str(q.statement.compile(dialect=postgresql.dialect()))
        # Check for <=> cosine distance operator in compiled PostgreSQL statement
        assert "<=>" in compiled_sql
        assert "memories.embedding" in compiled_sql
    finally:
        db.close()

def test_pgvector_query_branch_fallback_on_error():
    """Verify that if native pgvector query fails (e.g. extension missing), it falls back to Python scan."""
    agent = MemoryAgent()
    vec = [0.2] * 768
    agent.store_memory("Fallback test memory item", category="fallback_test", embedding=vec)

    db_session = SessionLocal()
    # Mock dialect to appear as postgresql but simulate query error in pgvector branch
    mock_bind = MagicMock()
    mock_bind.dialect.name = "postgresql"

    with patch.object(db_session, "bind", mock_bind):
        with patch.object(db_session, "query", side_effect=RuntimeError("Simulated pgvector operator failure")):
            with patch("backend.app.agents.memory_agent.SessionLocal", return_value=db_session):
                # Should not raise exception; handles gracefully and returns fallback or logs
                results, q_vec = agent.retrieve_memories("Fallback query", category="fallback_test")
                assert isinstance(results, list)
                assert isinstance(q_vec, list)
