# Blender MCP Senpai - Blender Extension

## Build

```sh
uv run --env-file .env build.py
```

## Debug

```sh
# Install extension

## Linux
avahi-discover | grep blender-mcp-sp
curl http://blender-mcp-sp.local:8000/healthz
```

## Test

```sh
uv run python -m pytest
```

## References

- https://github.com/BradyAJohnston/MolecularNodes
