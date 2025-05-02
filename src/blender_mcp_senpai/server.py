import logging
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import cast

from mcp import GetPromptResult
from mcp.server import InitializationOptions
from mcp.server.lowlevel import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import LoggingLevel, Prompt, PromptMessage, Resource, TextContent, Tool
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

    async def log(level: LoggingLevel, message: str):
        """
        Since it is not possible to log to stdout, use the logging method provided by MCP.
        NOTE: To avoid `LookupError: <ContextVar name='request_ctx`, ...>, do NOT use `log()` before `server.run()`.
        """
        if development:
            logging.log(getattr(logging, level.upper()), message)
        else:
            await server.request_context.session.send_log_message(
                level=level, data=message
            )

    blender_client = BlenderClient(log)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="execute_code",
                description="Execute code in the current Blender file",
                inputSchema={
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
            ),
            Tool(
                name="get_objects",
                description="List all objects in the current Blender file",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_object",
                description="Get details of a specific object in the current Blender file",
                inputSchema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            ),
            Tool(
                name="import_file",
                description="Import a file into the current Blender file",
                inputSchema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(tool: str, arguments: dict) -> list[TextContent]:
        await log("debug", f"call_tool: {tool=} {arguments=}")

        match tool:
            case "execute_code":
                code = arguments["code"]
                result = await blender_client.execute_code(code)
                return [TextContent(type="text", text=str(result))]

            case "get_objects":
                resources = await blender_client.list_resources()
                return [TextContent(type="text", text=str(resources))]

            case "get_object":
                object_name = arguments["name"]
                result = await blender_client.get_resource("objects", object_name)
                return [TextContent(type="text", text=str(result))]

            case "import_file":
                file_path = arguments["path"]
                result = await blender_client.import_file(file_path)
                return [TextContent(type="text", text=str(result))]

            case _:
                raise ValueError(f"Tool not found: {tool}")

    @server.list_resources()
    async def handle_list_resources() -> list[Resource]:
        await log("debug", "handle_list_resources")
        return [
            Resource(
                uri=cast(AnyUrl, resource["uri"]),
                name=resource["name"],
                mimeType=resource["mimeType"],
            )
            for resource in await blender_client.list_resources()
        ]

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> str:
        await log(
            "debug",
            f"handle_read_resource: {uri=}, {uri.scheme=}, {uri.host=}, {uri.path=}",
        )
        if uri.scheme != "blender":
            raise ValueError("Unsupported scheme")

        if uri.host and uri.path:
            object_name_url_decoded = urllib.parse.unquote(uri.path[1:])
            contents = await blender_client.get_resource(
                uri.host, object_name_url_decoded
            )  # uri.path is like "/Camera"

            # TODO: Handling of cases with multiple CONTENTS
            return contents[0]["content"]

        raise ValueError("Unsupported resource")

    @server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        await log("debug", "list_prompts")
        return [
            Prompt(
                name="text_and_image_help",
                description="Help with text and image",
                arguments=[],
            )
        ]

    @server.get_prompt()
    async def get_prompt(_name: str) -> GetPromptResult:
        prompt = await blender_client.get_prompt()
        return GetPromptResult(
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt),
                )
            ]
        )

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=MCP_SERVER_NAME,
                server_version="2025-03-26",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
