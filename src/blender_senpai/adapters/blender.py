import logging
from typing import Any

import bpy

from ..assets import NODE_GROUPS

logger = logging.getLogger(__name__)


def filtered(struct: bpy.types.bpy_struct) -> dict[str, Any]:
    filtered = {}
    for attr in dir(struct):
        if not attr.startswith("_"):
            value = getattr(struct, attr)
            if type(value) in [bool, int, float, str]:
                filtered[attr] = value
            elif type(value) in [tuple, list]:
                if all(isinstance(item, (bool, int, float, str)) for item in value):
                    filtered[attr] = list(value)
    return filtered


def _scan_required_materials(node_group: bpy.types.GeometryNodeTree) -> tuple[str, ...]:
    material_names: set[str] = set()
    for node in node_group.nodes:
        if hasattr(node, "material") and node.material is not None:
            material_names.add(node.material.name)
    logger.debug(f"{node_group.name=}: {material_names=}")
    return tuple(sorted(material_names))


def _append_node_group(node_group_name: str):
    file = NODE_GROUPS[node_group_name]["file"]
    logger.debug(f"{file=}")

    with bpy.data.libraries.load(file, link=False) as (src, dst):
        if (node_group_name in src.node_groups) and (
            node_group_name not in bpy.data.node_groups
        ):
            dst.node_groups.append(node_group_name)

    node_group = bpy.data.node_groups[node_group_name]
    required_materials = _scan_required_materials(node_group)

    with bpy.data.libraries.load(file, link=False) as (src, dst):
        for material_name in required_materials:
            if material_name not in src.materials:
                logger.warning(f"{material_name} not found in {file}; skipping")
                continue
            dst.materials.append(material_name)

    return node_group


def load_node_group(node_group_name: str) -> bpy.types.GeometryNodeTree:
    logger.info(f"{node_group_name=}")
    node_group = bpy.data.node_groups.get(node_group_name)
    if node_group:
        return node_group

    return _append_node_group(node_group_name)
