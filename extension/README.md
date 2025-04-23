# Blender MCP Senpai - Blender Extension

## Build

```sh
# TODO: Dealing with the complication of extensions in Bledner, which is launched for builds.
uv run --env-file .env build.py
```

## Debug

```console
# Install extension

## Linux
avahi-browse -a | grep blender

# OR directly
uv run -m mcp_senpai.server
wscat -c ws://localhost:13180/ws
> {"type": "get_resources"}
...
> {"type": "get_resource", "resource_type": "objects", "name": "Cube"}
...
```

## Test

```sh
uv run python -m pytest
```

## ToDo

- [ ] Keep log files locally.
- [ ] Sometimes mDNS can be observed from WSL, sometimes not.

## References

- https://github.com/BradyAJohnston/MolecularNodes
