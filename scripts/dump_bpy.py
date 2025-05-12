import json
import time
import types
from pathlib import Path
from typing import Any, Dict

import bpy
import mathutils

_MATHUTILS_TYPES = (
    mathutils.Vector,
    mathutils.Matrix,
    mathutils.Quaternion,
    mathutils.Euler,
    mathutils.Color,
)


def _is_module(obj: Any) -> bool:
    """ex. bpy"""
    return isinstance(obj, types.ModuleType)


def _is_bpy_struct(obj: Any) -> bool:
    """ex. bpy.context, bpy.data, bpy.ops..."""
    return isinstance(obj, bpy.types.bpy_struct)


def _is_bpy_collection(obj: Any) -> bool:
    """ex. bpy.context.blend_data.collections, ..."""
    return isinstance(obj, bpy.types.bpy_prop_collection)


def _is_mathutils(obj: Any) -> bool:
    return isinstance(obj, _MATHUTILS_TYPES)


def dump(obj: Any, *, depth: int = 0, max_depth: int = 8) -> Any:
    # mathutils types sometimes crash when repr is called from C side; return placeholder
    # check BEFORE depth limit to avoid hitting repr(obj) on these types
    if _is_mathutils(obj):
        return f"<{obj.__class__.__name__}>"

    if depth > max_depth:
        return repr(obj)

    if _is_module(obj) or _is_bpy_struct(obj):
        out: Dict[str, Any] = {}
        for attr in dir(obj):
            if attr.startswith("_"):
                continue

            try:
                value = getattr(obj, attr)
                if attr == "bl_rna" or attr == "rna_type":
                    dumped = repr(value)
                else:
                    dumped = dump(value, depth=depth + 1, max_depth=max_depth)
                out[attr] = dumped

            except Exception as e:
                out[attr] = f"<error: {e}>"

        return out

    if _is_bpy_collection(obj):
        out: Dict[str, Any] = {}
        for key, value in obj.items():
            out[key] = dump(value, depth=depth + 1, max_depth=max_depth)
        return out

    return repr(obj)


if __name__ == "__main__":
    log_dir = Path(bpy.utils.user_resource("CONFIG", path="dumps", create=True))
    file = log_dir / f"bpy_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(file, "w") as f:
        json.dump(dump(bpy, depth=0, max_depth=8), f, ensure_ascii=False, indent=2)
    print(f"dumped to {file}")
