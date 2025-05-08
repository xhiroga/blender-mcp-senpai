import os
import threading
import tomllib
import webbrowser
from logging import getLogger

import bpy
from bpy.types import Operator, Panel

from .log_config import configure
from .server import server
from .utils import execute_queued_functions

logger = getLogger(__name__)


def read_manifest() -> dict:
    """Read the blender_manifest.toml file and return its contents."""
    manifest_path = os.path.join(os.path.dirname(__file__), "blender_manifest.toml")
    try:
        with open(manifest_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}


class BLENDER_SENPAI_OT_open_server(Operator):
    bl_idname = "blender_senpai.open_server"
    bl_label = "Open Server"
    bl_description = "Open server URL in browser"

    def execute(self, context):
        url = f"http://{server.host}:{server.port}"
        webbrowser.open(url)
        return {"FINISHED"}


class BLENDER_SENPAI_PT_server(Panel):
    bl_label = "Server"
    bl_idname = "BLENDER_SENPAI_PT_server"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Blender Senpai"

    extension_version: str
    extension_commit: str

    def draw(self, context):
        layout = self.layout
        layout.operator(
            BLENDER_SENPAI_OT_open_server.bl_idname,
            text=f"Open http://{server.host}:{server.port}",
            icon="URL",
        )

        layout.label(text=f"Version: {self.extension_version}")
        layout.label(text=f"Commit: {self.extension_commit}")


classes = (BLENDER_SENPAI_OT_open_server, BLENDER_SENPAI_PT_server)


def register():
    """
    Called at Blender startup and when reinstalling extensions.
    Executed in Blender's main thread (needs to be checked).
    So, for example, if you put `time.sleep(10)`, from the time you press start Blender until the layout screen appears,
    The screen will be white until the layout screen is displayed.
    """
    configure(mode="extension")

    manifest = read_manifest()
    BLENDER_SENPAI_PT_server.extension_version = manifest.get("version", "unknown")
    BLENDER_SENPAI_PT_server.extension_commit = manifest.get("commit", "unknown")[:7]

    logger.info(
        f"Hello from extension! Blender :{bpy.app.version_string}, Extension: {BLENDER_SENPAI_PT_server.extension_version}, Git commit: {BLENDER_SENPAI_PT_server.extension_commit}"
    )

    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.app.timers.register(execute_queued_functions)
    threading.Thread(target=server.run).start()


def unregister():
    logger.info("Goodbye from extension!")
    server.stop()

    for cls in classes:
        bpy.utils.unregister_class(cls)
