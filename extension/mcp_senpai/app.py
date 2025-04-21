import io
from contextlib import redirect_stdout

import bpy
from fastapi import FastAPI, HTTPException, Request

from .usecases import get_object, get_objects
from .utils import mainthreadify

app = FastAPI()


@mainthreadify()
def execute_bpy_code(code: str):
    capture_buffer = io.StringIO()
    with redirect_stdout(capture_buffer):
        exec(code, {"bpy": bpy})
    value = capture_buffer.getvalue()
    print(f"execute_bpy_code: {value}")
    return value


@app.get("/healthz")
async def healthz():
    return {
        "version": bpy.app.version_string,
        "binary_path": bpy.app.binary_path,
    }


@app.post("/execute")
async def execute(request: Request):
    data = await request.json()
    code = data["code"]
    print(f"execute: {code}")
    executed = await execute_bpy_code(code)
    print(f"executed: {executed}")
    return {"executed": executed}


@app.get("/resources/")
async def get_resources():
    objects = get_objects()
    return {"resources": objects}


@app.get("/resources/{resource_type}/{name}")
async def get_resource(resource_type: str, name: str):
    if resource_type == "objects":
        resource = get_object(name)
        return {"resource": resource}
    else:
        raise HTTPException(
            status_code=404, detail=f"Resource type '{resource_type}' not supported"
        )
