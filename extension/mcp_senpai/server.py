import socket

import uvicorn

from .app import app
from .mdns import register_service, unregister_service


def get_port(default_port=None):
    """Get a port: if default_port is provided and free, use it; otherwise find an available port."""
    if default_port is not None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("", default_port))
                s.listen(1)
            return default_port
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        return s.getsockname()[1]


class Server:
    def __init__(self):
        self.server = None
        self.type = "_blender-senpai._tcp.local."
        self.name = None
        self.port = None
        self.zeroconf = None
        self.service_info = None

    def run(self, default_port=13180):
        self.port = get_port(default_port)

        self.name = f"blender-{self.port}"

        self.zeroconf, self.service_info = register_service(
            self.type,
            self.name,
            self.port,
            {},
            ["0.0.0.0"],
        )

        config = uvicorn.Config(app, host="0.0.0.0", port=self.port, loop="asyncio")
        self.server = uvicorn.Server(config)

        # This will block until the server is stopped
        self.server.run()

    def stop(self):
        if self.zeroconf and self.service_info:
            unregister_service(self.zeroconf, self.service_info)

        if self.server:
            self.server.should_exit = True


server = Server()


if __name__ == "__main__":
    server.run()
