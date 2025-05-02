# Blender Senpai - Blender Extension

## Build

```sh
# TODO: Dealing with the complication of extensions in Blender, which is launched for builds.
uv run --env-file .env build.py
```

## Debug

```console
# Install extension

## Linux
avahi-browse -a | grep blender

# OR directly
uv run -m blender_senpai.server
wscat -c ws://localhost:13180/ws
> {"type": "get_resources"}
...
> {"type": "get_resource", "resource_type": "objects", "name": "Cube"}
...
> {"type": "execute_code", "code": "import bpy; bpy.data.objects['Cube'].location = (1, 2, 3)"}
...
> {"type": "import_file", "path": "path/to/your/glb/file.glb"}
```

## Test

```sh
uv run python -m pytest
```

## ToDo

- [ ] Embed logo
- [ ] Store chat history and API keys securely
- [ ] Sometimes mDNS can be observed from WSL, sometimes not
- [ ] Refactor: remove unused texts from i18n

## Release

```sh
# Update version in `pyproject.toml`
uv run --env-file .env build.py
git add $(git rev-parse --show-toplevel)/docs/extensions/index.json
VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
git commit -m "feat: v$VERSION"
git tag v$VERSION
git push
git push --tags
gh release create v$VERSION --generate-notes
echo "Upload zip file to https://github.com/xhiroga/blender-mcp-senpai/releases/edit/v$VERSION"
```

## References

- https://github.com/BradyAJohnston/MolecularNodes
