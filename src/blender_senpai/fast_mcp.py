from logging import getLogger

from mcp.server.fastmcp import FastMCP

from .tools import tool_functions

logger = getLogger(__name__)


# The function may access global state internally (e.g., logger config, though FastMCP only modifies its internal logger)
# Therefore, we use a factory method pattern for the singleton to control execution order
def get_mcp() -> FastMCP:
    mcp = FastMCP(name="Blender Senpai", stateless_http=True)

    for tool in tool_functions.values():
        mcp.add_tool(tool)
        logger.info(f"Registered tool: {tool.__name__}")

    return mcp
