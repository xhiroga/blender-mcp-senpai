from typing import Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .tools import execute_code, get_object, get_objects, import_file

app = FastAPI()


class BlenderCommand(BaseModel):
    type: Literal[
        "get_resources", "get_resource", "execute_code", "import_file", "get_prompt"
    ]
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
                        result = get_objects()
                        await websocket.send_json(result)

                    case "get_resource":
                        if command.resource_type == "objects" and command.name:
                            result = get_object(command.name)
                            await websocket.send_json(result)

                    case "import_file":
                        if command.path:
                            result = await import_file(command.path)
                            await websocket.send_json(result)

                    case "get_prompt":
                        result = get_prompt()
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
