# Additional stdlib imports for asset handling
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

from .adapters.blender import filtered, load_node_group
from .assets import DESCRIPTIONS, NODE_GROUPS
from .log_config import configure
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


@mainthreadify()
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
def execute_code(code: str) -> Result:
    """Execute the given Python code in Blender and return the standard output."""
    logger.info(f"{code=}")
    try:
        capture_buffer = io.StringIO()
        with redirect_stdout(capture_buffer):
            exec(code, {"bpy": bpy})
        execute_bpy_code = capture_buffer.getvalue()
        logger.info(f"{execute_bpy_code=}")
        return {"status": "ok", "payload": execute_bpy_code}

    except Exception as e:
        logger.error(f"{e}")
        return {"status": "error", "payload": str(e)}


# bpy.context is managed per thread, so it needs to be executed in the main thread even though it's not an update operation
@mainthreadify()
@tool(
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def get_context() -> Result[Any]:
    """Get the current Blender context."""
    payload = {
        "blend_data": {
            "file_path": bpy.context.blend_data.filepath,
        },
        # ex. 'OBJECT', 'EDIT_MESH', 'SCULPT', ...
        "mode": bpy.context.mode,
        "preferences": {},
        "tool_settings": {},
        "scene": {},
        "window": {},
    }

    # First, prioritize settings that are often mentioned in videos for beginners.
    inputs = bpy.context.preferences.inputs
    inputs_info = {}
    # Orbit Method
    inputs_info["view_rotate_method"] = inputs.view_rotate_method
    # Orbit Sensitivity
    if inputs.view_rotate_method == "TRACKBALL":
        inputs_info["view_rotate_sensitivity_trackball"] = (
            inputs.view_rotate_sensitivity_trackball
        )
    elif inputs.view_rotate_method == "NUMPAD":
        inputs_info["view_rotate_sensitivity_turntable"] = (
            inputs.view_rotate_sensitivity_turntable
        )
    # Orbit Around Selection
    inputs_info["use_rotate_around_active"] = inputs.use_rotate_around_active

    # Auto
    inputs_info["use_auto_perspective"] = inputs.use_auto_perspective
    inputs_info["use_mouse_depth_navigate"] = inputs.use_mouse_depth_navigate

    # Zoom to Mouse Position
    inputs_info["use_zoom_to_mouse"] = inputs.use_zoom_to_mouse

    payload["preferences"]["inputs"] = inputs_info

    scene_info = {}
    # ex. 'GLOBAL', 'LOCAL', 'NORMAL', ...
    scene_info["transform_orientation_slots"] = [
        {"type": slot.type} for slot in bpy.context.scene.transform_orientation_slots
    ]

    tool_settings = {}
    for attr in dir(bpy.context.tool_settings):
        if not attr.startswith("_"):
            value = getattr(bpy.context.tool_settings, attr)
            if type(value) in [bool, int, float, str]:
                tool_settings[attr] = value
                # mesh_select_mode: ex. (True, False, False)
                # transform_pivot_point: ex. 'BOUNDING_BOX_CENTER', 'CURSOR', 'INDIVIDUAL_ORIGINS', ...
                # use_snap: bool
                # use_proportional_***: bool
                # snap_elements: ex. {'INCREMENT'}, ...
                # snap_elements_base: ex. {'INCREMENT'}, ...
                # snap_elements_individual: ex. set(), ...
                # snap_target: ex. 'CLOSEST', ...
                # snap_uv_element: ex. {'INCREMENT'}, ...

    payload["tool_settings"] = tool_settings

    window = bpy.context.window
    window_info = {"screen": {"areas": []}}
    for area in window.screen.areas:
        area_info = {"type": area.type, "ui_type": area.ui_type, "spaces": []}
        for space in area.spaces:
            space_info = filtered(space)
            match space.type:
                case "VIEW_3D":
                    space_info["overlay"] = filtered(space.overlay)
                    space_info["region_3d"] = filtered(space.region_3d)
                    space_info["shading"] = filtered(space.shading)
            area_info["spaces"].append(space_info)
        window_info["screen"]["areas"].append(area_info)
    payload["window"] = window_info

    logger.info(f"{payload=}")
    return {"status": "ok", "payload": payload}


@tool(
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)
def get_objects() -> Result[list[Resource]]:
    """Get a list of objects in the current Blender scene."""
    resources = []
    for name in bpy.data.objects.keys():
        resources.append(
            Resource(
                uri=f"blender://objects/{name}",
                name=name,
                mimeType="application/json",
            )
        )
    logger.info(f"{resources=}")
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
    logger.info(f"{name=}")
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
    logger.info(f"{info=}")
    return {
        "status": "ok",
        "payload": [
            {
                "content": json.dumps(info),
                "mime_type": "text/plain",
            }
        ],
    }


@mainthreadify()
@tool(
    parameters={
        "type": "object",
        "properties": {
            "names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Object name (key in bpy.data.objects)",
                "example": ["Cube", "Suzanne"],
            },
            "node_group_name": {
                "type": "string",
                "enum": list(NODE_GROUPS.keys()),
                "description": f"Node group name to apply. {DESCRIPTIONS}",
                "example": list(NODE_GROUPS.keys())[0],
            },
        },
        "required": ["names", "node_group_name"],
    },
)
def modify_with_geometry_nodes(names: list[str], node_group_name: str) -> Result:
    """Apply geometry nodes to objects."""
    logger.info(f"{names=}, {node_group_name=}")

    try:
        node_group = load_node_group(node_group_name)

        applied_names = []
        for obj_name in names:
            obj = bpy.data.objects.get(obj_name)
            if obj is None:
                logger.warning(f"{obj_name=} not found")
                continue

            # Find existing modifier or create a new one.
            mod = next(
                (
                    m
                    for m in obj.modifiers
                    if m.type == "NODES" and m.node_group == node_group
                ),
                None,
            )
            if mod is None:
                mod = obj.modifiers.new(name=node_group.name, type="NODES")
            mod.node_group = node_group
            mod.show_render = False
            applied_names.append(obj_name)

        return {
            "status": "ok",
            "payload": f"{node_group=} applied to {', '.join(applied_names)}",
        }

    except Exception as e:
        logger.error(f"{e}")
        return {"status": "error", "payload": str(e)}


@mainthreadify()
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
def import_file(file_path: str) -> Result[list[ReadResourceContents]]:
    """Import a 3D file and return the imported objects."""
    logger.info(f"{file_path=}")
    try:
        if not os.path.exists(file_path):
            logger.error(f"{file_path=} not found")
            return {"status": "error", "payload": f"{file_path=} not found"}

        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext in [".glb", ".gltf"]:
            bpy.ops.import_scene.gltf(filepath=file_path)
        elif file_ext == ".obj":
            bpy.ops.import_scene.obj(filepath=file_path)
        elif file_ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=file_path)
        else:
            logger.error(f"Unsupported file format: {file_ext}")
            return {
                "status": "error",
                "payload": f"Unsupported file format: {file_ext}",
            }

        imported_objects = bpy.context.selected_objects
        payload = []
        for obj in imported_objects:
            payload.extend(get_object(obj.name))

        logger.info(f"{payload=}")
        return {"status": "ok", "payload": payload}

    except Exception as e:
        logger.error(f"{e}")
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
    configure(mode="standalone")
    print(f"{tools=}")
    print(f"{tool_functions=}")
