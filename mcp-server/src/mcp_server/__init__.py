import asyncio

from . import server


def main():
    # FastMCP, but decided against it because it requires a call to add_resource each time a resource is added.
    asyncio.run(server.main())


# Optionally expose other important items at package level
__all__ = ["main"]
