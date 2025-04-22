import argparse
import asyncio

from . import server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    # FastMCP, but decided against it because it requires a call to add_resource each time a resource is added.
    asyncio.run(server.main(args.development))


# Optionally expose other important items at package level
__all__ = ["main"]
