import json

import bpy

from ._types import Resource


def get_objects() -> list[Resource]:
    return [
        Resource(
            uri=f"blender://objects/{name}",
            name=name,
            mimeType="application/json",
        )
        for name in bpy.data.objects.keys()
    ]


def get_object(name: str) -> Resource:
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
    return Resource(
        uri=f"blender://objects/{name}",
        name=name,
        mimeType="application/json",
        text=json.dumps(info),
    )


def get_mesh(name: str) -> dict:
    return {
        "name": name,
    }


def get_material(name: str) -> dict:
    return {
        "name": name,
    }
