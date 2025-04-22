from typing import Literal

from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

from .usecases import execute_bpy_code, get_object, get_objects

app = FastAPI()


class BlenderCommand(BaseModel):
    type: Literal["get_resources", "get_resource", "execute"]
    code: str | None = None
    resource_type: str | None = None
    name: str | None = None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    while True:
        command = BlenderCommand.model_validate(await websocket.receive_json())

        match command.type:
            case "get_resources":
                objects = get_objects()
                await websocket.send_json(
                    {
                        "type": "resources",
                        "data": {"resources": objects},
                    }
                )

            case "get_resource":
                if command.resource_type == "objects" and command.name:
                    resource = get_object(command.name)
                    await websocket.send_json(
                        {
                            "type": "resource",
                            "data": {"resource": resource},
                        }
                    )

            case "execute":
                if command.code:
                    executed = await execute_bpy_code(command.code)
                    await websocket.send_json(
                        {"type": "executed", "data": {"executed": executed}}
                    )

            case _:
                raise ValueError(f"Undefined command: {command}")
