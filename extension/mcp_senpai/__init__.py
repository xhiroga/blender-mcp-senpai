import bpy

from . import websocket_server

# Global variable to store the server thread
server_thread = None


def register():
    global server_thread
    print("Hello from extension!", f"{bpy.app.version_string}")

    # Start the WebSocket server
    server_thread = websocket_server.start_websocket_server()
    print("WebSocket server started")


def unregister():
    global server_thread
    print("Goodbye from extension!")

    # Stop the WebSocket server
    if server_thread:
        websocket_server.stop_websocket_server()
        print("WebSocket server stopped")
