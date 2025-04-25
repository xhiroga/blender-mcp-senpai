import asyncio
import json
from typing import Any, Awaitable, Callable, TypedDict

import websockets
from mcp import types
from websockets.asyncio.client import ClientConnection


class Resource(TypedDict):
    uri: str
    name: str
    mimeType: str


class ReadResourceContents(TypedDict):
    content: str
    mime_type: str


async def stdout(level: types.LoggingLevel, message: str):
    print(f"{level}: {message}")


class BlenderClient:
    def __init__(
        self,
        log: Callable[[types.LoggingLevel, str], Awaitable[None]] = stdout,
        url: str = "ws://127.0.0.1:13180/ws",
    ) -> None:
        self.log = log
        self.url = url
        self.websocket: ClientConnection | None = None

    async def _ensure_connection(self):
        if self.websocket is not None:
            return

        # self.url = await discover_server()
        # if self.url is None:
        #     raise ConnectionError("No server discovered")

        self.websocket = await websockets.connect(self.url)

    async def _send_message(self, message: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_connection()
        if self.websocket is None:
            raise ValueError("_ensure_connection looks not working")

        await self.websocket.send(json.dumps(message))
        response = await self.websocket.recv()

        return json.loads(response)

    async def execute_code(self, code: str):
        response = await self._send_message({"type": "execute_code", "code": code})
        return response.get("payload", {})

    async def list_resources(self) -> list[Resource]:
        response = await self._send_message({"type": "get_resources"})
        return response.get("payload", {})

    async def get_resource(
        self, resource_type: str, name: str
    ) -> list[ReadResourceContents]:
        await self.log("info", f"get_resource: {resource_type=} {name=}")
        response = await self._send_message(
            {"type": "get_resource", "resource_type": resource_type, "name": name}
        )
        await self.log("error", f"get_resource: {response=}")

        return response.get("payload", {})

    async def import_file(self, path: str):
        response = await self._send_message({"type": "import_file", "path": path})
        return response.get("payload", {})


async def debug():
    client = BlenderClient()
    resources = await client.list_resources()
    return await client.get_resource("objects", resources[0]["name"])


if __name__ == "__main__":
    print(asyncio.run(debug()))
