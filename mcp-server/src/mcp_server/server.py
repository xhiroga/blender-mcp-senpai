import logging
from datetime import datetime
from pathlib import Path

from mcp import types
from mcp.server import InitializationOptions
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from pydantic import AnyUrl

from .blender_client import BlenderClient

MCP_SERVER_NAME = "blender-mcp-senpai"


async def main(development: bool):
    server: Server = Server(MCP_SERVER_NAME)

    if development:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logging.basicConfig(
            filename=log_dir / f"mcp_server_{timestamp}.log",
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    async def log(level: types.LoggingLevel, message: str):
        """
        Since it is not possible to log to stdout, use the logging method provided by MCP.
        NOTE: To avoid `LookupError: <ContextVar name='request_ctx`, ...> DO NOT use `log()` before `server.run()`.
        """
        if development:
            logging.log(getattr(logging, level.upper()), message)
        else:
            await server.request_context.session.send_log_message(
                level=level, data=message
            )

    blender_client = BlenderClient(log)

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        await log("debug", "handle_list_resources")
        return await blender_client.list_resources()

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl):
        await log(
            "debug",
            f"handle_read_resource: {uri=}, {uri.scheme=}, {uri.host=}, {uri.path=}",
        )
        if uri.scheme != "blender":
            raise ValueError("Unsupported scheme")

        if uri.host and uri.path:
            return await blender_client.get_resource(
                uri.host, uri.path[1:]
            )  # uri.path is like "/Camera"

        raise ValueError("Unsupported resource")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=MCP_SERVER_NAME,
                server_version="0.0.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
