import os
import sys
import json
import subprocess
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock
from typing import Dict, Any, Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import verify_admin_key, hash_key_identifier
from backend.app.database.models import MCPServer, AuditLog
from backend.app.mcp.client import mcp_manager
from backend.app.mcp.security import (
    validate_command_and_args,
    get_sanitized_environment,
    validate_sse_url,
    kill_process_group,
    wrap_untrusted_mcp_output,
    MCPSecurityError,
    DENIED_ARG_FLAGS,
)
from backend.app.mcp.catalog import load_catalog, build_server_from_catalog
from backend.app.main import validate_production_environment, validate_mcp_entry


def test_disallowed_command_rejected() -> None:
    for bad_cmd in ["bash", "powershell", "curl", "cmd", "sh", "eval", "wget"]:
        with pytest.raises(MCPSecurityError):
            validate_command_and_args(bad_cmd, ["--version"])


def test_each_denied_flag_rejected() -> None:
    for flag in DENIED_ARG_FLAGS:
        with pytest.raises(MCPSecurityError):
            validate_command_and_args("python", [flag, "print('exploit')"])
        with pytest.raises(MCPSecurityError):
            validate_command_and_args("node", [flag, "console.log('exploit')"])


def test_shell_metacharacters_rejected() -> None:
    for char in [";", "|", "&", "$", "`", "<", ">", "\n", "\r"]:
        with pytest.raises(MCPSecurityError):
            validate_command_and_args("python", [f"arg{char}test"])
        with pytest.raises(MCPSecurityError):
            validate_command_and_args(f"node{char}", ["valid_arg"])


def test_env_override_rejected_and_parent_secrets_stripped() -> None:
    old_env = {k: os.environ.get(k) for k in ["GEMINI_API_KEY", "TAVILY_API_KEY", "DATABASE_URL", "API_SECRET_KEY", "ADMIN_API_KEY"]}
    try:
        os.environ["GEMINI_API_KEY"] = "super-secret-gemini-key"
        os.environ["TAVILY_API_KEY"] = "super-secret-tavily-key"
        os.environ["DATABASE_URL"] = "postgresql://user:pass@secret-db/prod"
        os.environ["API_SECRET_KEY"] = "super-secret-api-key"
        os.environ["ADMIN_API_KEY"] = "super-secret-admin-key"

        sanitized = get_sanitized_environment(declared_env_keys=[])

        assert "GEMINI_API_KEY" not in sanitized
        assert "TAVILY_API_KEY" not in sanitized
        assert "DATABASE_URL" not in sanitized
        assert "API_SECRET_KEY" not in sanitized
        assert "ADMIN_API_KEY" not in sanitized
        assert "PATH" in sanitized
        assert "HOME" in sanitized
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_user_input_can_never_reach_command_position() -> None:
    catalog = load_catalog()
    assert len(catalog) >= 1

    entry = catalog[0]
    entry_id = entry["id"]

    spec = build_server_from_catalog(entry_id, {})
    assert spec["command"] == entry["command"]
    assert spec["command"] in ["npx", "node", "python"]

    with pytest.raises(ValueError):
        build_server_from_catalog("sqlite_explorer", {"db_path": "injected; malicious.sh"})


def test_admin_key_separation_and_failure_modes(api_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_start = AsyncMock(return_value=True)
    monkeypatch.setattr("backend.app.api.mcp.mcp_manager.register_and_start", mock_start)
    monkeypatch.setattr("backend.app.mcp.client.mcp_manager.register_and_start", mock_start)
    saved_admin_key = settings.admin_api_key
    try:
        settings.admin_api_key = ""
        resp_unset = api_client.post(
            "/api/mcp/servers",
            json={"catalog_id": "fetch_service"},
            headers={"X-Admin-Key": "any-key"}
        )
        assert resp_unset.status_code == 403

        settings.admin_api_key = "correct-admin-key-789"
        resp_missing = api_client.post(
            "/api/mcp/servers",
            json={"catalog_id": "fetch_service"}
        )
        assert resp_missing.status_code == 403

        resp_wrong = api_client.post(
            "/api/mcp/servers",
            json={"catalog_id": "fetch_service"},
            headers={"X-Admin-Key": "wrong-key"}
        )
        assert resp_wrong.status_code == 403

        resp_success = api_client.post(
            "/api/mcp/servers",
            json={"catalog_id": "fetch_service"},
            headers={"X-Admin-Key": "correct-admin-key-789"}
        )
        assert resp_success.status_code in [200, 400]
    finally:
        settings.admin_api_key = saved_admin_key


def test_audit_log_recorded_on_enable(api_client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_start = AsyncMock(return_value=True)
    monkeypatch.setattr("backend.app.api.mcp.mcp_manager.register_and_start", mock_start)
    monkeypatch.setattr("backend.app.mcp.client.mcp_manager.register_and_start", mock_start)

    db_session.query(MCPServer).filter(MCPServer.name == "Web Fetch Service").delete()
    db_session.commit()

    saved_admin_key = settings.admin_api_key
    test_key = "audit-test-admin-key-456"
    expected_actor = hash_key_identifier(test_key)
    try:
        settings.admin_api_key = test_key
        resp = api_client.post(
            "/api/mcp/servers",
            json={"catalog_id": "fetch_service"},
            headers={"X-Admin-Key": test_key}
        )
        assert resp.status_code == 200

        log = db_session.query(AuditLog).filter(AuditLog.actor == expected_actor).first()
        assert log is not None
        assert log.actor == expected_actor
        assert "audit-test-admin-key" not in log.actor
    finally:
        settings.admin_api_key = saved_admin_key


def test_production_startup_guards() -> None:
    with pytest.raises(RuntimeError, match="ADMIN_API_KEY is empty"):
        validate_production_environment(
            environment="production",
            api_secret_key="",
            admin_api_key="",
            allowed_origins=["https://agentforge.vercel.app"]
        )

    with pytest.raises(RuntimeError, match="ALLOWED_ORIGINS cannot be empty"):
        validate_production_environment(
            environment="production",
            api_secret_key="valid-api",
            admin_api_key="valid-admin",
            allowed_origins=[]
        )

    with pytest.raises(RuntimeError, match="wildcard"):
        validate_production_environment(
            environment="production",
            api_secret_key="valid-api",
            admin_api_key="valid-admin",
            allowed_origins=["*"]
        )

    validate_production_environment(
        environment="production",
        api_secret_key="valid-api",
        admin_api_key="valid-admin",
        allowed_origins=["https://agentforge.vercel.app"]
    )


def test_poisoned_db_row_disabled_at_startup() -> None:
    is_valid = validate_mcp_entry(
        name="malicious_server",
        command="python",
        args=["-c", "import os; os.system('echo hack')"]
    )
    assert is_valid is False

    is_valid_bash = validate_mcp_entry(
        name="bash_server",
        command="bash",
        args=["-i"]
    )
    assert is_valid_bash is False


def test_poisoned_mcp_servers_json_entry_rejected() -> None:
    poisoned_entry = {
        "name": "poisoned_json",
        "command": "node",
        "args": ["-e", "process.exit(1)"]
    }
    assert validate_mcp_entry(
        poisoned_entry["name"],
        poisoned_entry["command"],
        poisoned_entry["args"]
    ) is False


def test_sse_url_validation_rejects_ssrf() -> None:
    with pytest.raises(MCPSecurityError, match="Only 'https' is permitted"):
        validate_sse_url("http://example.com/sse")

    with pytest.raises(MCPSecurityError, match="loopback"):
        validate_sse_url("https://127.0.0.1/sse")

    with pytest.raises(MCPSecurityError, match="loopback"):
        validate_sse_url("https://localhost/sse")

    with pytest.raises(MCPSecurityError, match="169.254.169.254"):
        validate_sse_url("https://169.254.169.254/latest/meta-data")

    with pytest.raises(MCPSecurityError, match="private"):
        validate_sse_url("https://10.0.0.5:8443/sse")

    with pytest.raises(MCPSecurityError, match="not in the allowed hosts"):
        validate_sse_url("https://evil.com/sse", allowed_hosts=["safe.mcp.io"])


def test_kill_process_group_handles_none_gracefully() -> None:
    kill_process_group(None)


def test_wrap_untrusted_mcp_output() -> None:
    raw_output = {"content": [{"type": "text", "text": "result"}]}
    wrapped = wrap_untrusted_mcp_output(raw_output)
    assert wrapped.get("_is_untrusted_mcp_output") is True


def test_child_process_cannot_see_parent_secrets(tmp_path: Path) -> None:
    test_script = tmp_path / "print_env.py"
    test_script.write_text("import os, json\nprint(json.dumps(dict(os.environ)))\n", encoding="utf-8")

    old_env = {k: os.environ.get(k) for k in ["GEMINI_API_KEY", "DATABASE_URL", "API_SECRET_KEY", "ADMIN_API_KEY"]}
    try:
        os.environ["GEMINI_API_KEY"] = "gemini-secret-123"
        os.environ["DATABASE_URL"] = "postgres://secret"
        os.environ["API_SECRET_KEY"] = "api-secret-123"
        os.environ["ADMIN_API_KEY"] = "admin-secret-123"

        safe_env = get_sanitized_environment(declared_env_keys=[])
        proc = subprocess.run([sys.executable, str(test_script)], env=safe_env, capture_output=True, text=True)
        child_env = json.loads(proc.stdout)

        assert "GEMINI_API_KEY" not in child_env
        assert "DATABASE_URL" not in child_env
        assert "API_SECRET_KEY" not in child_env
        assert "ADMIN_API_KEY" not in child_env
        assert "PATH" in child_env
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@pytest.mark.asyncio
async def test_timeout_kills_misbehaving_child(tmp_path: Path) -> None:
    test_script = tmp_path / "hang.py"
    test_script.write_text("import time\ntime.sleep(60)\n", encoding="utf-8")
    safe_env = get_sanitized_environment([])
    proc = await asyncio.create_subprocess_exec(sys.executable, str(test_script), env=safe_env)
    try:
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(proc.wait(), timeout=0.2)
    finally:
        kill_process_group(proc)
        await asyncio.sleep(0.1)
