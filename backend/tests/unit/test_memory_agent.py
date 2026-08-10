import pytest
from backend.app.agents.memory_agent import MemoryAgent

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
