import socket

import uvicorn

from .app import app
from .mdns import register_service, unregister_service


def find_available_port():
    """Find an available port on the system."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
        return port


class Server:
    def __init__(self):
        self.server = None
        self.type = "_blender-mcp-sp._tcp.local."
        self.name = None
        self.port = None
        self.zeroconf = None
        self.service_info = None

    def run(self):
        # Find an available port
        self.port = find_available_port()
        self.name = f"blender-{self.port}"

        # Register mDNS service before starting the server
        self.zeroconf, self.service_info = register_service(
            self.type,
            self.name,
            self.port,
            {},
            ["0.0.0.0"],
        )

        # Create server configuration with the found port
        config = uvicorn.Config(app, host="0.0.0.0", port=self.port, loop="asyncio")
        self.server = uvicorn.Server(config)

        # Run the server (this will block until the server is stopped)
        self.server.run()

    def stop(self):
        if self.zeroconf and self.service_info:
            unregister_service(self.zeroconf, self.service_info)

        if self.server:
            self.server.should_exit = True


server = Server()
