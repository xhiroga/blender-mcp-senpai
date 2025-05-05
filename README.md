# Blender Senpai

![Logo](docs/assets/logo/logo.png)

Your senpai (先輩, mentor) of Blener.

## About

TODO...

## Installation

### To Blender

- Open Blender
- Go to `Edit` > `Preferences` > `Get Extensions` > `Repositories` > `+` > `Add Remote Repository`
- Add `https://xhiroga.github.io/blender-mcp-senpai/extensions/index.json`
- Search `Blender Senpai` and install it
- `Add-ons` > `Blender Senpai` > Enable it

### To Claude

```json
{
    "mcpServers": {
        "blender-senpai": {
            "command": "npx",
            "args": [
                "-y",
                "supergateway",
                "--sse",
                "http://localhost:13180/sse"
            ]
        }
    }
}
```

### To Dive

```json
{
  "mcpServers": {
    "blender-senpai": {
      "transport": "sse",
      "enabled": true,
      "command": null,
      "args": [],
      "env": {},
      "url": "http://localhost:13180/sse"
    }
  }
}
```

## Development

See [.github/pull_request_template.md](.github/pull_request_template.md).

## Test

```sh
uv run python -m pytest
```

## Release

```sh
# Update version in `pyproject.toml`
uv run --env-file .env build.py
# Install extension to Blender and check if it works.
git add docs/extensions/index.json pyproject.toml uv.lock
VERSION=$(python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
git commit -m "feat: v$VERSION"
git tag v$VERSION
git push
git push --tags
gh release create v$VERSION --generate-notes
echo "Upload zip file to https://github.com/xhiroga/blender-mcp-senpai/releases/edit/v$VERSION"
```

## Features

- [x] Indexing Blender documents
- [x] Search documents by DuckDB-VSS
- [ ] Use RAG through MCP
- [x] Install MCP server by Repository
- [ ] List resources through MCP
- [ ] Describe Blender version through MCP
- [ ] Send Blender screenshot through MCP
- [ ] Embed logo
- [ ] Store chat history and API keys securely
- [ ] Refactor: remove unused texts from i18n

## Inspiration

- https://github.com/ahujasid/blender-mcp
- https://github.com/AIGODLIKE/GenesisCore
- https://github.com/BradyAJohnston/MolecularNodes
