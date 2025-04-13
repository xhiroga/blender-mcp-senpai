import asyncio
import json
import socket
import threading

import bpy
import websockets
from zeroconf import ServiceInfo, Zeroconf

# WebSocket server configuration
HOST = "0.0.0.0"
PORT = 8765
SERVICE_NAME = "blender-sensei-mcp"
SERVICE_TYPE = "_blender-sensei._tcp.local."

# Global variables
server = None
zeroconf = None
service_info = None
server_task = None


async def get_blender_info():
    """Get Blender version and scene information"""
    return {
        "version": bpy.app.version_string,
        "scene": {
            "name": bpy.context.scene.name,
            "objects": len(bpy.context.scene.objects),
            "frames": {
                "start": bpy.context.scene.frame_start,
                "end": bpy.context.scene.frame_end,
                "current": bpy.context.scene.frame_current,
            },
        },
    }


async def handle_client(websocket, path):
    """Handle WebSocket client connections"""
    try:
        # Send initial Blender info
        info = await get_blender_info()
        await websocket.send(json.dumps(info))

        # Keep connection open and handle any incoming messages
        async for message in websocket:
            # For now, just echo back the received message
            await websocket.send(f"Received: {message}")
    except websockets.exceptions.ConnectionClosed:
        pass


def start_mdns():
    """Start mDNS advertising"""
    global zeroconf, service_info

    # Get local IP address
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    # Create service info
    service_info = ServiceInfo(
        SERVICE_TYPE,
        f"{SERVICE_NAME}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(local_ip)],
        port=PORT,
        properties={},
    )

    # Register service
    zeroconf = Zeroconf()
    zeroconf.register_service(service_info)
    print(
        f"mDNS service registered: {SERVICE_NAME}.{SERVICE_TYPE} at {local_ip}:{PORT}"
    )


def stop_mdns():
    """Stop mDNS advertising"""
    global zeroconf, service_info

    if zeroconf and service_info:
        zeroconf.unregister_service(service_info)
        zeroconf.close()
        print("mDNS service unregistered")


async def start_server():
    """Start WebSocket server"""
    global server

    server = await websockets.serve(handle_client, HOST, PORT)
    print(f"WebSocket server started at ws://{HOST}:{PORT}")

    # Start mDNS advertising
    start_mdns()

    # Keep the server running
    await asyncio.Future()


def run_server():
    """Run the WebSocket server in a separate thread"""
    global server_task

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server_task = loop.create_task(start_server())
    loop.run_forever()


def start_websocket_server():
    """Start the WebSocket server in a background thread"""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread


def stop_websocket_server():
    """Stop the WebSocket server and mDNS advertising"""
    global server, server_task

    if server:
        server.close()
        print("WebSocket server stopped")

    stop_mdns()
