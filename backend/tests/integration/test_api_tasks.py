import pytest

def test_healthcheck(api_client):
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"

def test_list_tasks(api_client):
    response = api_client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_plugins(api_client):
    response = api_client.get("/api/plugins")
    assert response.status_code == 200
    plugins = response.json()
    assert isinstance(plugins, list)
    assert len(plugins) >= 2

def test_list_agents(api_client):
    response = api_client.get("/api/agents")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)
    assert len(agents) >= 5


def test_list_tasks_pagination(api_client, db_session):
    from backend.app.database.models import Task

    created_ids = []
    try:
        for i in range(5):
            t = Task(prompt=f"Pagination test task {i}", plugin_name="default", status="completed")
            db_session.add(t)
            db_session.commit()
            db_session.refresh(t)
            created_ids.append(t.id)

        # Page 1: limit 2
        resp1 = api_client.get("/api/tasks?skip=0&limit=2")
        assert resp1.status_code == 200
        page1 = resp1.json()
        assert len(page1) == 2

        # Page 2: skip 2, limit 2
        resp2 = api_client.get("/api/tasks?skip=2&limit=2")
        assert resp2.status_code == 200
        page2 = resp2.json()
        assert len(page2) == 2

        # Ensure page 1 and page 2 have distinct items
        ids_page1 = {item["id"] for item in page1}
        ids_page2 = {item["id"] for item in page2}
        assert ids_page1.isdisjoint(ids_page2)

    finally:
        for tid in created_ids:
            task = db_session.query(Task).filter(Task.id == tid).first()
            if task:
                db_session.delete(task)
        db_session.commit()


def test_list_tasks_pagination_validation(api_client):
    # limit must be >= 1
    resp_limit_zero = api_client.get("/api/tasks?limit=0")
    assert resp_limit_zero.status_code == 422

    # skip must be >= 0
    resp_negative_skip = api_client.get("/api/tasks?skip=-1")
    assert resp_negative_skip.status_code == 422

