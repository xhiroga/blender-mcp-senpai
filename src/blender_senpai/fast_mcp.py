from logging import getLogger

from mcp.server.fastmcp import FastMCP

from .tools import tool_functions

logger = getLogger(__name__)


fast_mcp = FastMCP("Blender Senpai")

for tool in tool_functions.values():
    fast_mcp.add_tool(tool)
    logger.debug(f"Registered tool: {tool.__name__}")
