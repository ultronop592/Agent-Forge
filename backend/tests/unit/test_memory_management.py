import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.connection import SessionLocal
from backend.app.database.models import Memory

client = TestClient(app)


def test_memory_add_delete_and_stats():
    # 1. Add a test memory
    add_res = client.post("/api/memory", json={
        "category": "factual",
        "content": "Test constraint: rate limit is 50 requests per minute"
    })
    assert add_res.status_code == 200
    created = add_res.json()
    assert "id" in created
    mem_id = created["id"]

    # 2. Check stats endpoint
    stats_res = client.get("/api/memory/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total" in stats
    assert stats["total"] >= 1
    assert stats["categories"]["factual"] >= 1

    # 3. Query memory by category
    query_res = client.get("/api/memory?category=factual")
    assert query_res.status_code == 200
    ids = [m["id"] for m in query_res.json()]
    assert mem_id in ids

    # 4. Delete the specific memory
    del_res = client.delete(f"/api/memory/{mem_id}")
    assert del_res.status_code == 200
    assert del_res.json()["id"] == mem_id

    # 5. Verify deletion (404 on re-delete)
    del_again = client.delete(f"/api/memory/{mem_id}")
    assert del_again.status_code == 404

    # 6. Verify deleted from list
    post_del_res = client.get("/api/memory?category=factual")
    post_ids = [m["id"] for m in post_del_res.json()]
    assert mem_id not in post_ids


def test_memory_clear_category():
    # Seed 2 test memories in a unique category
    client.post("/api/memory", json={"category": "test_cat", "content": "Memory A"})
    client.post("/api/memory", json={"category": "test_cat", "content": "Memory B"})

    # Check they exist
    res = client.get("/api/memory?category=test_cat")
    assert len(res.json()) >= 2

    # Clear category
    clear_res = client.delete("/api/memory?category=test_cat")
    assert clear_res.status_code == 200
    assert clear_res.json()["count"] >= 2

    # Verify cleared
    res2 = client.get("/api/memory?category=test_cat")
    assert len(res2.json()) == 0
