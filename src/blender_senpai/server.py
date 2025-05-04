import asyncio
import socket
from logging import getLogger

import gradio as gr
import uvicorn

from .fast_mcp import fast_mcp
from .webui import interface

logger = getLogger(__name__)


class Server:
    def __init__(self):
        self.server = None
        self.port = None

    @staticmethod
    def _get_port(default_port=None):
        """Get a port: if default_port is provided and free, use it; otherwise find an available port."""
        if default_port is not None:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", default_port))
                    s.listen(1)
                return default_port
            except OSError:
                pass
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            return s.getsockname()[1]

    def run(self, default_host="127.0.0.1", default_port=13180):
        # In Python, there is no default event loop except for main thread.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.port = self._get_port(default_port)

        app = fast_mcp.sse_app()
        gradio_app = gr.mount_gradio_app(app, interface, path="")

        logger.info(
            f"Starting FastAPI server with Gradio UI and SSE endpoint on {default_host}:{self.port}"
        )

        config = uvicorn.Config(
            gradio_app,
            host=default_host,
            port=self.port,
            loop="asyncio",
            log_level="info",
        )
        self.server = uvicorn.Server(config)

        # This will block until the server is stopped
        self.server.run()

    def stop(self):
        if self.server:
            # If do not set force_exit, Uvicorn will not exit until the connection is closed when the browser opens the Gradio page.
            self.server.force_exit = True
            self.server.should_exit = True


server = Server()


if __name__ == "__main__":
    try:
        server.run()
    finally:
        server.stop()
