import threading

import bpy

from .server import run_server
from .utils import execute_queued_functions


def register():
    """
    Called at Blender startup and when reinstalling extensions.
    Executed in Blender's main thread (needs to be checked).
    So, for example, if you put `time.sleep(10)`, from the time you press start Blender until the layout screen appears,
    The screen will be white until the layout screen is displayed.
    """
    print("Hello from extension!", f"{bpy.app.version_string}")

    bpy.app.timers.register(execute_queued_functions)
    threading.Thread(target=run_server).start()


def unregister():
    print("Goodbye from extension!")
