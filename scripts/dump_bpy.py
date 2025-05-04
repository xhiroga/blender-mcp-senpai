import json
import time
import types
from pathlib import Path
from typing import Any, Dict

import bpy


def _is_module(obj: Any) -> bool:
    """ex. bpy"""
    return isinstance(obj, types.ModuleType)


def _is_bpy_struct(obj: Any) -> bool:
    """ex. bpy.context, bpy.data, bpy.ops..."""
    return isinstance(obj, bpy.types.bpy_struct)


def _is_traversable(obj: Any) -> bool:
    return _is_module(obj) or _is_bpy_struct(obj)


def dump(obj: Any, *, depth: int = 0, max_depth: int = 5) -> dict[str, Any]:
    if depth > max_depth:
        return repr(obj)

    if not _is_traversable(obj):
        return repr(obj)

    out: Dict[str, Any] = {}
    for attr in dir(obj):
        if attr.startswith("_"):
            continue

        try:
            value = getattr(obj, attr)
        except Exception as e:
            out[attr] = f"<error: {e}>"
            continue

        out[attr] = dump(value, depth=depth + 1, max_depth=max_depth)

    return out


if __name__ == "__main__":
    log_dir = Path(bpy.utils.user_resource("CONFIG", path="dumps", create=True))
    with open(log_dir / f"bpy_{time.strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
        json.dump(dump(bpy, depth=0, max_depth=5), f, ensure_ascii=False, indent=2)
