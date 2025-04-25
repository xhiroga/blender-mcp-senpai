import io
import json
import os
from contextlib import redirect_stdout
from typing import Literal, TypedDict, TypeVar

import bpy

from .utils import mainthreadify

T = TypeVar("T")


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
def execute_code(code: str) -> Result:
    try:
        capture_buffer = io.StringIO()
        with redirect_stdout(capture_buffer):
            exec(code, {"bpy": bpy})
        execute_bpy_code = capture_buffer.getvalue()
        print(f"{execute_bpy_code=}")
        return {"status": "ok", "payload": execute_bpy_code}

    except Exception as e:
        return {"status": "error", "payload": str(e)}


def get_objects() -> list[Resource]:
    return [
        Resource(
            uri=f"blender://objects/{name}",
            name=name,
            mimeType="application/json",
        )
        for name in bpy.data.objects.keys()
    ]


def get_object(name: str) -> list[ReadResourceContents]:
    """
    Return data that can be displayed in the Properties editor.
    """
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
    return [
        {
            "content": json.dumps(info),
            "mime_type": "text/plain",
        }
    ]


@mainthreadify()
def import_file(file_path: str) -> Result[list[ReadResourceContents]]:
    try:
        if not os.path.exists(file_path):
            return {"status": "error", "payload": f"{file_path=} not found"}

        file_ext = os.path.splitext(file_path)[1].lower()

        # ファイル形式に応じたインポート処理
        if file_ext in [".glb", ".gltf"]:
            bpy.ops.import_scene.gltf(filepath=file_path)
        elif file_ext == ".obj":
            bpy.ops.import_scene.obj(filepath=file_path)
        elif file_ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=file_path)
        else:
            return {
                "status": "error",
                "payload": f"Unsupported file format: {file_ext}",
            }

        imported_objects = bpy.context.selected_objects
        payload = []
        for obj in imported_objects:
            payload.extend(get_object(obj.name))

        return {"status": "ok", "payload": payload}

    except Exception as e:
        return {"status": "error", "payload": str(e)}
