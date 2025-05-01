import asyncio
import concurrent.futures
import queue
from functools import wraps
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

T = TypeVar("T")
P = ParamSpec("P")

execution_queue = queue.Queue()


def execute_queued_functions():
    while not execution_queue.empty():
        function = execution_queue.get()
        function()
    INTERVAL = 0
    return INTERVAL


def mainthreadify(
    *, timeout: float = None
) -> Callable[[Callable[P, T]], Callable[P, Coroutine[Any, Any, T]]]:
    """
    Execute a function in the main thread and return the result in Future.
    In Blender, UI-related processes are performed in the main thread,
    I/O processes such as network communication should be executed in a separate thread.

    However, `bpy` is NOT thread-safe.
    - [Use a Timer to react to events in another thread](https://docs.blender.org/api/current/bpy.app.timers.html#use-a-timer-to-react-to-events-in-another-thread)
    - [Thread Safety with bpy API](https://devtalk.blender.org/t/thread-safety-with-bpy-api/16468/3)

    Therefore, the update process using `bpy` is done in the main thread.
    Python has a knack for waiting for `future` across threads, which is summarized in this function.

    NOTE: All exceptions in functions executed in the main thread MUST be caught!!!
    """

    def decorator(function: Callable[P, T]) -> Callable[P, Coroutine[Any, Any, T]]:
        @wraps(function)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Coroutine[Any, Any, T]:
            print(f"decorator: {function.__name__}")
            loop = asyncio.get_running_loop()
            conc_future = concurrent.futures.Future()
            execution_queue.put(
                lambda: conc_future.set_result(function(*args, **kwargs))
            )
            future = asyncio.wrap_future(conc_future, loop=loop)
            print(f"{future=}")
            return future

        return wrapper

    return decorator
