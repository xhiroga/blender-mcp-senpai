import asyncio
import contextlib
import socket
from logging import getLogger
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router as api_router
from .fast_mcp import get_mcp
from .log_config import configure

logger = getLogger(__name__)


class Server:
    def __init__(self, locale: str, port: int = 13180):
        self.server = None
        self.host = "127.0.0.1"
        self.port = port
        self.locale = locale

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
                logger.warning(f"Port {default_port} is already in use")
                pass
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            s.listen(1)
            return s.getsockname()[1]

    def run(self):
        # In Python, there is no default event loop except for main thread.
        # Known Issue: Occasionally, `curl: (18) transfer closed with outstanding read data remaining` occurs For now, restarting the OS fixes the issue, but...
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.port = self._get_port(self.port)

        mcp = get_mcp()

        @contextlib.asynccontextmanager
        async def lifespan(app: FastAPI):
            async with contextlib.AsyncExitStack() as stack:
                await stack.enter_async_context(mcp.session_manager.run())
                yield

        app = FastAPI(lifespan=lifespan)
        # Starletteの仕様として、パスプレフィックス（リクエストがあったパスの最も右側のスラッシュまでの部分）でマウント先を確定させる
        # したがって、localhost:13180/mcp というリクエストは、"/" にマウントされる
        # 一方で、localhost:13180/mcp/ や localhost:13180/mcp/mcp というリクエストは、"/mcp" にマウントされる
        # 一見困りそうだが、`streamable_http_app()` は、"/mcp" にマウントされるため、結果的に"/mcp/mcp" でアクセスするため問題ない。
        app.mount("/mcp", mcp.streamable_http_app())
        app.mount("/api", api_router)

        web_dist = Path(__file__).parent / "web"
        if web_dist.exists():
            app.mount(
                "/", StaticFiles(directory=str(web_dist), html=True), name="static"
            )
        else:
            logger.warning(f"Web dist directory not found at {web_dist}")

        logger.info(
            f"Starting FastAPI server with React UI and SSE endpoint on {self.host}:{self.port}"
        )

        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            loop="asyncio",
            log_level="info",
        )
        self.server = uvicorn.Server(config)

        # This will block until the server is stopped
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True
            # If do not set force_exit, Uvicorn will not exit until the connection is closed when the browser opens the Gradio page.
            self.server.force_exit = True


if __name__ == "__main__":
    import os

    os.environ["DEBUG"] = "1"
    configure(mode="standalone")

    locale = "en_JP"
    server = Server(locale, port=23181)
    try:
        server.run()
    finally:
        server.stop()
