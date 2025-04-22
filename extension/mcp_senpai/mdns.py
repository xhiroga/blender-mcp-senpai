from zeroconf import ServiceInfo, Zeroconf


def register_service(
    type: str,
    name: str,
    port: int,
    properties: dict[str, str],
    parsed_addresses: list[str],
):
    """NOTE: Since this is a simplified design, redesign if each IP address belongs to a different Network Interface."""
    zeroconf = Zeroconf(interfaces=parsed_addresses)
    service_info = ServiceInfo(
        type,
        f"{name}.{type}",
        port=port,
        properties=properties,
        parsed_addresses=parsed_addresses,
    )
    print(f"register_service: {name}.{type} at {parsed_addresses[0]}:{port}")
    zeroconf.register_service(service_info)
    # TODO: Use logger
    print(f"mDNS service registered: {name}.{type} at {parsed_addresses[0]}:{port}")
    return zeroconf, service_info


def unregister_service(zeroconf: Zeroconf, service_info: ServiceInfo):
    zeroconf.unregister_service(service_info)
    zeroconf.close()
    # TODO: Use logger
    print(f"mDNS service unregistered: {service_info.name}.{service_info.type}")


def debug():
    import http.server
    import json
    import signal
    import socket
    import sys
    import threading

    def get_local_ip():
        try:
            # Create a temporary socket to get the default route
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # This doesn't actually create a connection
            s.connect(("8.8.8.8", 80))
            print(f"{s.getsockname()=}")
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            # Fallback to localhost if no network connection
            return "127.0.0.1"

    class EchoHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            headers = {k: v for k, v in self.headers.items()}
            response = {"path": self.path, "headers": headers}
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

    HOST = "0.0.0.0"
    SERVICE_TYPE = "_echo._tcp.local."
    SERVICE_NAME = "echo-server"
    local_ip = get_local_ip()
    parsed_addresses = [local_ip]

    http_server = http.server.HTTPServer((HOST, 0), EchoHandler)
    PORT = http_server.server_address[1]

    zeroconf, service_info = register_service(
        SERVICE_TYPE,
        SERVICE_NAME,
        PORT,
        {},
        parsed_addresses,
    )

    def signal_handler(sig, frame):
        unregister_service(zeroconf, service_info)

        if http_server:
            http_server.shutdown()
            http_server.server_close()
            print("HTTP server stopped")

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    server_thread = threading.Thread(target=http_server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    print(f"HTTP server running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop")

    try:
        while True:
            signal.pause()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    debug()
