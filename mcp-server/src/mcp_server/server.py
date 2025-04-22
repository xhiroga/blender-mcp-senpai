import mcp.types as types
from mcp.server import InitializationOptions
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from pydantic import AnyUrl

from .blender_client import BlenderClient

MCP_SERVER_NAME = "blender-mcp-senpai"


async def main():
    blender_client = BlenderClient()
    server = Server("blender-mcp-senpai")

    @server.list_resources()
    async def handle_list_resources() -> list[types.Resource]:
        return await blender_client.list_resources()

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl):
        if uri.scheme != "blender":
            raise ValueError("Unsupported scheme")

        if uri.path == "objects":
            return await blender_client.get_resource("objects", uri.path)

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
