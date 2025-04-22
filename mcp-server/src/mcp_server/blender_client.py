import asyncio
import json
from typing import Any, Awaitable, Callable

import websockets
from mcp import types
from websockets.asyncio.client import ClientConnection

from .service_discovery import discover_server


def stdout(level: types.LoggingLevel, message: str):
    print(f"{level}: {message}")


class BlenderClient:
    def __init__(
        self,
        log: Callable[[types.LoggingLevel, str], Awaitable[None]] = stdout,
    ) -> None:
        self.log = log
        self.websocket: ClientConnection | None = None

    async def _ensure_connection(self):
        if self.websocket is not None:
            return

        url = await discover_server()
        if url is None:
            raise ConnectionError("No server discovered")

        self.websocket = await websockets.connect(url)

    async def _send_message(self, message: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_connection()
        if self.websocket is None:
            raise ValueError("_ensure_connection looks not working")

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()

        return json.loads(response)

    async def list_resources(self) -> list[types.Resource]:
        response = await self._send_message({"type": "get_resources"})
        return response.get("data", {}).get("resources", [])

    # TODO: Maybe we can fix it to get_object, along with extensions.
    async def get_resource(self, resource_type: str, name: str) -> types.Resource:
        await self.log("debug", f"get_resource: {resource_type} {name}")
        response = await self._send_message(
            {"type": "get_resource", "resource_type": resource_type, "name": name}
        )
        return response.get("data", {}).get("resource", {})


async def debug():
    client = BlenderClient()
    resources = await client.list_resources()
    return await client.get_resource("objects", resources[0]["name"])


if __name__ == "__main__":
    print(asyncio.run(debug()))
