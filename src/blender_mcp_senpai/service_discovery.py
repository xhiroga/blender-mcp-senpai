import asyncio
import base64
import secrets
from typing import List, Tuple

import aiohttp
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

STATUS_CODE_SWITCHING_PROTOCOLS = 101


class BlenderServiceListener(ServiceListener):
    def __init__(self) -> None:
        self.services: List[Tuple[str, int]] = []

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info and info.port is not None:
            print(info)
            self.services.append((info.parsed_addresses()[0], info.port))


async def discover_server() -> str | None:
    zeroconf = Zeroconf()
    listener = BlenderServiceListener()

    try:
        _browser = ServiceBrowser(zeroconf, "_blender-senpai._tcp.local.", listener)
        await asyncio.sleep(1)  # Wait for discovery

        for host, port in listener.services:
            url = f"ws://{host}:{port}/ws"
            if await check_server_without_connection(url):
                return url

        return None
    finally:
        zeroconf.close()


async def check_server_without_connection(url: str) -> bool:
    try:
        http_url = url.replace("ws://", "http://").replace("wss://", "https://")
        key = base64.b64encode(secrets.token_bytes(16)).decode()
        headers = {
            "Connection": "Upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Key": key,
            "Sec-WebSocket-Version": "13",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(http_url, headers=headers) as response:
                print(response)
                return response.status == STATUS_CODE_SWITCHING_PROTOCOLS
    except Exception:
        return False


if __name__ == "__main__":
    print(asyncio.run(discover_server()))
