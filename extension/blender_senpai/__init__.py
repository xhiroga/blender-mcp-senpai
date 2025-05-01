import os
import threading
import tomllib

import bpy

from .server import server
from .utils import execute_queued_functions


def read_manifest() -> dict:
    """Read the blender_manifest.toml file and return its contents."""
    manifest_path = os.path.join(os.path.dirname(__file__), "blender_manifest.toml")
    try:
        with open(manifest_path, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        return {}


def register():
    """
    Called at Blender startup and when reinstalling extensions.
    Executed in Blender's main thread (needs to be checked).
    So, for example, if you put `time.sleep(10)`, from the time you press start Blender until the layout screen appears,
    The screen will be white until the layout screen is displayed.
    """
    manifest = read_manifest()
    print(
        f"Hello from extension! Blender {bpy.app.version_string} | Extension v{manifest.get('version', 'unknown')} | Git commit: {manifest.get('commit', 'unknown')}"
    )

    bpy.app.timers.register(execute_queued_functions)
    threading.Thread(target=server.run).start()


def unregister():
    print("Goodbye from extension!")
    server.stop()
