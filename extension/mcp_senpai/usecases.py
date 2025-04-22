import io
import json
from contextlib import redirect_stdout
from typing import TypedDict

import bpy

from .utils import mainthreadify


class Resource(TypedDict):
    uri: str
    name: str
    mimeType: str
    text: str


class ReadResourceResult(TypedDict):
    contents: list[Resource]


@mainthreadify()
def execute_bpy_code(code: str):
    capture_buffer = io.StringIO()
    with redirect_stdout(capture_buffer):
        exec(code, {"bpy": bpy})
    value = capture_buffer.getvalue()
    print(f"execute_bpy_code: {value}")
    return value


def get_objects() -> list[Resource]:
    return [
        Resource(
            uri=f"blender://objects/{name}",
            name=name,
            mimeType="application/json",
        )
        for name in bpy.data.objects.keys()
    ]


def get_object(name: str) -> ReadResourceResult:
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
    return ReadResourceResult(
        contents=[
            Resource(
                uri=f"blender://objects/{name}",
                name=name,
                mimeType="application/json",
                text=json.dumps(info),
            )
        ]
    )
