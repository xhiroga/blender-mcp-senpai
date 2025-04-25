from typing import Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .usecases import execute_code, get_object, get_objects, import_glb

app = FastAPI()


class BlenderCommand(BaseModel):
    type: Literal["get_resources", "get_resource", "execute_code", "import_glb"]
    code: str | None = None
    resource_type: str | None = None
    name: str | None = None
    path: str | None = None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                data = await websocket.receive_json()
                command = BlenderCommand.model_validate(data)
                print(f"{command=}")

                match command.type:
                    case "execute_code":
                        if command.code:
                            result = await execute_code(command.code)
                            await websocket.send_json(result)

                    case "get_resources":
                        objects = get_objects()
                        await websocket.send_json(
                            {
                                "type": "resources",
                                "data": objects,
                            }
                        )

                    case "get_resource":
                        if command.resource_type == "objects" and command.name:
                            resource = get_object(command.name)
                            await websocket.send_json(
                                {
                                    "type": "resource",
                                    "data": resource,
                                }
                            )

                    case "import_glb":
                        if command.path:
                            result = await import_glb(command.path)
                            await websocket.send_json(result)

                    case _:
                        raise ValueError(f"Undefined command: {command}")
            except Exception as e:
                # I'm most afraid of communication stops, so I'll catch them all.
                await websocket.send_json({"type": "error", "data": str(e)})

    # Messages at the time of WebSocket abnormal disconnection of the ASGI protocol are processed with `except` instead of `case`, because the disconnection code is binary and not JSON.
    # ex. {'type': 'websocket.disconnect', 'code': <CloseCode.ABNORMAL_CLOSURE: 1006>, 'reason': ''}
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected with {e.code=}: {e.reason=}")
