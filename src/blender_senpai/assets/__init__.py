from importlib import resources


def _abs(file: str) -> str:
    # __package__ is like `bl_ext.xhiroga_github_io.blender_senpai.adapters.assets`
    return str(resources.files(__package__) / file)


NODE_GROUPS = {
    "BLSP.NgonVisualizer": {
        "description": "Highlights triangles and polygons with 5 or more vertices in yellow during Viewport Display.",
        "file": _abs("visualizer.blend"),
    }
}
DESCRIPTIONS = ", ".join(
    f"{name}: {value['description']}" for name, value in NODE_GROUPS.items()
)
