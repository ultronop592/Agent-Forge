import json
import os
import re
from typing import List, Dict, Any, Optional

CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "mcp_catalog.json"
)

_catalog_cache: Optional[List[Dict[str, Any]]] = None


def load_catalog(force_reload: bool = False) -> List[Dict[str, Any]]:
    global _catalog_cache
    if _catalog_cache is not None and not force_reload:
        return _catalog_cache

    if not os.path.exists(CATALOG_PATH):
        _catalog_cache = []
        return _catalog_cache

    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        _catalog_cache = data.get("catalog", [])
        return _catalog_cache


def get_catalog_entry(catalog_id: str) -> Optional[Dict[str, Any]]:
    catalog = load_catalog()
    for entry in catalog:
        if entry.get("id") == catalog_id:
            return entry
    return None


def build_server_from_catalog(catalog_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    entry = get_catalog_entry(catalog_id)
    if not entry:
        raise ValueError(f"Catalog entry '{catalog_id}' not found.")

    params = parameters or {}
    declared_params = entry.get("parameters", {})
    validated_args: List[str] = list(entry.get("fixed_args", []))

    for param_name, schema in declared_params.items():
        if param_name in params:
            val = params[param_name]
            expected_type = schema.get("type", "string")
            if expected_type == "string" and not isinstance(val, str):
                raise ValueError(f"Parameter '{param_name}' must be a string.")
            
            pattern = schema.get("pattern")
            if pattern and isinstance(val, str):
                if not re.match(pattern, val):
                    raise ValueError(f"Parameter '{param_name}' does not match validation pattern: {pattern}")
            
            validated_args.append(str(val))
        elif schema.get("required", False):
            raise ValueError(f"Missing required parameter '{param_name}' for catalog entry '{catalog_id}'.")

    return {
        "catalog_id": catalog_id,
        "name": entry.get("name", catalog_id),
        "command": entry.get("command"),
        "args": validated_args,
        "required_env": entry.get("required_env", []),
        "pinned_package": entry.get("pinned_package"),
        "needs_network": entry.get("needs_network", False),
    }
