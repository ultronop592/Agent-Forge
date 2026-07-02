from fastapi import APIRouter
from typing import List, Dict, Any
from backend.app.plugins.registry import plugin_registry

router = APIRouter(prefix="/plugins", tags=["plugins"])

@router.get("")
def list_plugins() -> List[Dict[str, Any]]:
    plugins = plugin_registry.get_all_plugins()
    return [
        {
            "plugin_id": p.plugin_id,
            "name": p.name,
            "description": p.description
        }
        for p in plugins
    ]
