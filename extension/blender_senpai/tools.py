import inspect
import io
import json
import os
import sys
from contextlib import redirect_stdout
from functools import wraps
from logging import getLogger
from typing import Any, Callable, Literal, ParamSpec, TypedDict, TypeVar

import bpy

from .system_prompt import SYSTEM_PROMPT
from .utils import mainthreadify

logger = getLogger(__name__)

T = TypeVar("T")
P = ParamSpec("P")


def tool(*, parameters: dict[str, Any]):
    def decorator(function: Callable[P, T]) -> Callable[P, T]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            return function(*args, **kwargs)

        wrapper.__is_tool__ = True
        wrapper.__parameters__ = parameters
        return wrapper

    return decorator


class Result(TypedDict):
    status: Literal["ok", "error"]
    payload: T | str


class Resource(TypedDict):
    uri: str
    name: str
    mimeType: str


class ReadResourceContents(TypedDict):
    content: str
    mime_type: str


@tool(
    parameters={
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Execute the given Python code.",
                "example": "bpy.ops.mesh.primitive_cube_add()",
            }
        },
        "required": ["code"],
    },
)
@mainthreadify()
def execute_code(code: str) -> Result:
    """Execute the given Python code in Blender and return the standard output."""
    logger.info(f"execute_code: {code[:100]=}")
    try:
        capture_buffer = io.StringIO()
        with redirect_stdout(capture_buffer):
            exec(code, {"bpy": bpy})
        execute_bpy_code = capture_buffer.getvalue()
        logger.info(f"execute_code: {execute_bpy_code[:100]=}")
        return {"status": "ok", "payload": execute_bpy_code}

    except Exception as e:
        logger.error(f"execute_code: {e}")
        return {"status": "error", "payload": str(e)}


@tool(
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def get_objects() -> Result[list[Resource]]:
    """Get a list of objects in the current Blender scene."""
    logger.info("get_objects")
    resources = []
    for name in bpy.data.objects.keys():
        resources.append(
            Resource(
                uri=f"blender://objects/{name}",
                name=name,
                mimeType="application/json",
            )
        )
    logger.info(f"get_objects: {resources=}")
    return {"status": "ok", "payload": resources}


@tool(
    parameters={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Object name (key in bpy.data.objects)",
                "example": "Cube",
            }
        },
        "required": ["name"],
    },
)
def get_object(name: str) -> Result[list[ReadResourceContents]]:
    """Get detailed information about the specified object."""
    logger.info(f"get_object: {name=}")
    object = bpy.data.objects[name]
    properties = {
        # Transform
        # Vector is not JSON serializable, so convert to list
        "location": list(object.location),
        "rotation_quaternion": list(object.rotation_quaternion),
        "mode": object.mode,
        "scale": list(object.scale),
    }
    # Currently NOT supported: Delta transform, Relations, Instancing, Motion paths, shading, Visibility, Viewport Display, Line Art, Animation, Custom Properties

    def kfs(fcurve: bpy.types.FCurve):
        return [
            {
                "frame": keyframe.co[0],
                "value": keyframe.co[1],
                "interpolation": keyframe.interpolation,
                "easing": keyframe.easing,
            }
            for keyframe in fcurve.keyframe_points
        ]

    if object.animation_data:
        animation = {}
        if object.animation_data.action:
            action = object.animation_data.action
            action_value = {
                "name": object.animation_data.action.name,
                "frame_range": list(object.animation_data.action.frame_range),
                **(
                    {"x_location": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("location", index=0)) is not None
                    else {}
                ),
                **(
                    {"y_location": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("location", index=1)) is not None
                    else {}
                ),
                **(
                    {"z_location": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("location", index=2)) is not None
                    else {}
                ),
                **(
                    {"x_euler_rotation": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("rotation_euler", index=0))
                    is not None
                    else {}
                ),
                **(
                    {"y_euler_rotation": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("rotation_euler", index=1))
                    is not None
                    else {}
                ),
                **(
                    {"z_euler_rotation": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("rotation_euler", index=2))
                    is not None
                    else {}
                ),
                **(
                    {"x_scale": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("scale", index=0)) is not None
                    else {}
                ),
                **(
                    {"y_scale": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("scale", index=1)) is not None
                    else {}
                ),
                **(
                    {"z_scale": kfs(fcurve)}
                    if (fcurve := action.fcurves.find("scale", index=2)) is not None
                    else {}
                ),
            }
            animation["action"] = action_value
        properties["animation"] = animation

    modifiers = []
    for modifier in object.modifiers:
        modifiers.append(
            {
                "name": modifier.name,
            }
        )
    # Currently NOT supported: Effects, Particles, Physics, Object Constrains

    info = {
        "properties": properties,
        "modifiers": modifiers,
    }
    logger.info(f"get_object: {info=}")
    return {
        "status": "ok",
        "payload": [
            {
                "content": json.dumps(info),
                "mime_type": "text/plain",
            }
        ],
    }


@tool(
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the file to import",
                "example": "/path/to/model.glb",
            }
        },
        "required": ["file_path"],
    },
)
@mainthreadify()
def import_file(file_path: str) -> Result[list[ReadResourceContents]]:
    """Import a 3D file and return the imported objects."""
    logger.info(f"import_file: {file_path=}")
    try:
        if not os.path.exists(file_path):
            logger.error(f"import_file: {file_path=} not found")
            return {"status": "error", "payload": f"{file_path=} not found"}

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in [".glb", ".gltf"]:
            bpy.ops.import_scene.gltf(filepath=file_path)
        elif file_ext == ".obj":
            bpy.ops.import_scene.obj(filepath=file_path)
        elif file_ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=file_path)
        else:
            logger.error(f"import_file: Unsupported file format: {file_ext}")
            return {
                "status": "error",
                "payload": f"Unsupported file format: {file_ext}",
            }

        imported_objects = bpy.context.selected_objects
        payload = []
        for obj in imported_objects:
            payload.extend(get_object(obj.name))

        logger.info(f"import_file: {payload=}")
        return {"status": "ok", "payload": payload}

    except Exception as e:
        logger.error(f"import_file: {e}")
        return {"status": "error", "payload": str(e)}


def get_prompt() -> Result[str]:
    return {"status": "ok", "payload": SYSTEM_PROMPT}


class Tool(TypedDict):
    type: Literal["function"]
    function: TypedDict(
        "Function", {"name": str, "description": str, "parameters": dict[str, Any]}
    )


def _get_tools() -> list[Tool]:
    tools: list[Tool] = []
    for name, func in inspect.getmembers(sys.modules[__name__]):
        if hasattr(func, "__is_tool__"):
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": inspect.getdoc(func) or "",
                        "parameters": func.__parameters__,
                    },
                }
            )
    return tools


tools = _get_tools()
tool_functions: dict[str, Callable[P, T]] = {
    name: func
    for name, func in inspect.getmembers(sys.modules[__name__])
    if hasattr(func, "__is_tool__")
}

if __name__ == "__main__":
    print(f"{tools=}")
    print(f"{tool_functions=}")
