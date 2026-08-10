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
