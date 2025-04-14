import asyncio
import concurrent.futures
import queue
from typing import Any, Callable, TypeVar

import bpy

T = TypeVar("T")

execution_queue = queue.Queue()


async def mainthreadify(
    function: Callable[..., T], *args: Any, timeout: float = None, **kwargs: Any
) -> T:
    """
    Execute a function in the main thread and return the result in Future.
    In Blender, UI-related processes are performed in the main thread,
    I/O processes such as network communication should be executed in a separate thread.

    However, `bpy` is NOT thread-safe.
    - [Use a Timer to react to events in another thread](https://docs.blender.org/api/current/bpy.app.timers.html#use-a-timer-to-react-to-events-in-another-thread)
    - [Thread Safety with bpy API](https://devtalk.blender.org/t/thread-safety-with-bpy-api/16468/3)

    Therefore, the update process using `bpy` is done in the main thread.
    Python has a knack for waiting for `future` across threads, which is summarized in this function.
    """
    loop = asyncio.get_running_loop()
    conc_future = concurrent.futures.Future()
    execution_queue.put(lambda: conc_future.set_result(function(*args, **kwargs)))
    return asyncio.wrap_future(conc_future, loop=loop)


def execute_queued_functions():
    while not execution_queue.empty():
        function = execution_queue.get()
        function()
    return 1.0


def register():
    """
    Called at Blender startup and when reinstalling extensions.
    Executed in Blender's main thread (needs to be checked).
    So, for example, if you put `time.sleep(10)`, from the time you press start Blender until the layout screen appears,
    The screen will be white until the layout screen is displayed.
    """
    print("Hello from extension!", f"{bpy.app.version_string}")

    bpy.app.timers.register(execute_queued_functions)


def unregister():
    print("Goodbye from extension!")
