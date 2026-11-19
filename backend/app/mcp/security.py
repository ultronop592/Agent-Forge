import os
import re
import sys
import signal
import socket
import logging
import ipaddress
import urllib.parse
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("agentforge.mcp.security")

DENIED_ARG_FLAGS = {
    "-c",
    "-e",
    "--eval",
    "-r",
    "--require",
    "--import",
    "--loader",
    "-m",
    "--input-type",
    "-i",
    "--interactive"
}

SHELL_METASYMBOLS = {"|", ";", "&", "$", "`", "<", ">", "\n", "\r"}


class MCPSecurityError(Exception):
    pass


def validate_command_and_args(
    command: str,
    args: List[str],
    allowed_commands: Optional[List[str]] = None,
    expected_pinned_package: Optional[str] = None
) -> None:
    if not command or not isinstance(command, str):
        raise MCPSecurityError("Command must be a non-empty string.")

    cmd_base = os.path.basename(command).lower()
    if cmd_base.endswith(".exe"):
        cmd_base = cmd_base[:-4]

    allowed = [c.strip().lower() for c in (allowed_commands or ["npx", "node", "python"])]
    if cmd_base not in allowed:
        raise MCPSecurityError(f"Command '{command}' is not in the allowed commands list: {allowed}")

    for char in SHELL_METASYMBOLS:
        if char in command:
            raise MCPSecurityError(f"Command contains forbidden character: '{char}'")

    for arg in args:
        if not isinstance(arg, str):
            raise MCPSecurityError(f"All arguments must be strings, got: {type(arg)}")

        for char in SHELL_METASYMBOLS:
            if char in arg:
                raise MCPSecurityError(f"Argument '{arg}' contains forbidden shell metacharacter: '{char}'")

        arg_lower = arg.lower()
        if arg_lower in DENIED_ARG_FLAGS:
            raise MCPSecurityError(f"Denied inline evaluation flag: '{arg}'")

        for flag in DENIED_ARG_FLAGS:
            if arg_lower.startswith(f"{flag}=") or arg_lower.startswith(f"{flag}:"):
                raise MCPSecurityError(f"Denied inline evaluation flag: '{arg}'")

    if expected_pinned_package:
        package_found = any(expected_pinned_package in a for a in args)
        if not package_found:
            raise MCPSecurityError(
                f"Missing expected pinned package '{expected_pinned_package}' in arguments."
            )


def get_sanitized_environment(declared_env_keys: Optional[List[str]] = None) -> Dict[str, str]:
    safe_env: Dict[str, str] = {}

    for var_name in ["PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"]:
        val = os.environ.get(var_name)
        if val is not None:
            safe_env[var_name] = val

    temp_dir = os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"
    safe_env["HOME"] = temp_dir
    safe_env["TMPDIR"] = temp_dir
    safe_env["TEMP"] = temp_dir
    safe_env["TMP"] = temp_dir

    if declared_env_keys:
        for key in declared_env_keys:
            if key in os.environ:
                safe_env[key] = os.environ[key]

    return safe_env


def get_posix_preexec_fn() -> Optional[Callable[[], None]]:
    if sys.platform == "win32":
        return None

    try:
        import resource

        def _limits() -> None:
            os.setsid()
            max_memory_bytes = 256 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory_bytes, max_memory_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
            resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
            resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))

        return _limits
    except (ImportError, AttributeError):
        logger.warning("Resource limits module unavailable; running without rlimit enforcement.")
        return None


def kill_process_group(process: Any) -> None:
    if not process:
        return

    pid = getattr(process, "pid", None)
    if pid is None:
        return

    if sys.platform != "win32":
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
            return
        except ProcessLookupError:
            return
        except Exception as e:
            logger.debug(f"Process group termination fallback for pid {pid}: {e}")

    try:
        process.terminate()
    except ProcessLookupError:
        pass
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def validate_sse_url(url: str, allowed_hosts: Optional[List[str]] = None) -> str:
    if not url or not isinstance(url, str):
        raise MCPSecurityError("URL must be a non-empty string.")

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        raise MCPSecurityError(f"Insecure scheme '{parsed.scheme}'. Only 'https' is permitted for SSE MCP servers.")

    hostname = parsed.hostname
    if not hostname:
        raise MCPSecurityError("URL is missing a valid hostname.")

    if allowed_hosts:
        normalized_allowed = [h.strip().lower() for h in allowed_hosts if h.strip()]
        if normalized_allowed and hostname.lower() not in normalized_allowed:
            raise MCPSecurityError(f"Host '{hostname}' is not in the allowed hosts list: {normalized_allowed}")

    port = parsed.port or 443
    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise MCPSecurityError(f"DNS resolution failed for host '{hostname}': {e}")

    for entry in addr_info:
        sockaddr = entry[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise MCPSecurityError(f"Resolved address '{ip_str}' is invalid.")

        if ip.is_loopback:
            raise MCPSecurityError(f"Host '{hostname}' resolved to loopback address: {ip_str}")
        if ip.is_private:
            raise MCPSecurityError(f"Host '{hostname}' resolved to private IP address: {ip_str}")
        if ip.is_link_local:
            raise MCPSecurityError(f"Host '{hostname}' resolved to link-local address: {ip_str}")
        if ip.is_reserved:
            raise MCPSecurityError(f"Host '{hostname}' resolved to reserved IP address: {ip_str}")
        if ip.is_multicast:
            raise MCPSecurityError(f"Host '{hostname}' resolved to multicast address: {ip_str}")
        if str(ip) == "169.254.169.254":
            raise MCPSecurityError("Access to cloud metadata address 169.254.169.254 is forbidden.")

    return url


def wrap_untrusted_mcp_output(output: Any) -> Any:
    # TODO (Prompt B): Implement full untrusted content boundary wrapper and prompt sanitizer
    if isinstance(output, dict):
        return {**output, "_is_untrusted_mcp_output": True}
    return output
