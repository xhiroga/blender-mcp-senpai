from logging import getLogger

from mcp.server.fastmcp import FastMCP

from .tools import tool_functions

logger = getLogger(__name__)


# The function may access global state internally (e.g., logger config, though FastMCP only modifies its internal logger)
# Therefore, we use a factory method pattern for the singleton to control execution order
def get_sse_app():
    fast_mcp = FastMCP("Blender Senpai")

    for tool in tool_functions.values():
        fast_mcp.add_tool(tool)
        logger.debug(f"Registered tool: {tool.__name__}")

    return fast_mcp.sse_app()
