# Blender MCP Senpai

![Logo](docs/assets/logo/logo.png)

Your senpai (先輩, mentor) of Blener.

## About

TODO...

## Installation

### To Blender

- Open Blender
- Go to `Edit` > `Preferences` > `Get Extensions` > `Repositories` > `+` > `Add Remote Repository`
- Add `https://xhiroga.github.io/blender-mcp-senpai/extensions/index.json`
- Search `MCP Senpai` and install it

### To Claude / Cursor / Other AI Agents

```json
{
    "mcpServers": {
        "blender-mcp-senpai": {
            "command": "uvx",
            "args": [
                "--refresh",
                "--from",
                "git+https://github.com/xhiroga/blender-mcp-senpai",
                "blender-mcp-senpai",
                "--development"
            ]
        }
    }
}
```

NOTE: As of 2025-04-24, Claude Desktop fails when running uvx remotely.The cause is unknown as other clients and local runs succeed.

If not working, try to debug with

```sh
npx @modelcontextprotocol/inspector@latest uvx --refresh --from "git+https://github.com/xhiroga/blender-mcp-senpai" blender-mcp-senpai --development
# URLs are enclosed in double quotes to prevent subdirectory specifications from being regarded as comments.
```

## Development

```sh
# Paths searched by uvx are relative to the path where npx was run
npx @modelcontextprotocol/inspector@latest uvx --with-editable . blender-mcp-senpai --development
```

## Features

- [x] Indexing Blender documents
- [x] Search documents by DuckDB-VSS
- [ ] Use RAG through MCP
- [x] Install MCP server by Repository
- [ ] List resources through MCP
- [ ] Describe Blender version through MCP
- [ ] Send Blender screenshot through MCP

## Inspiration

- https://github.com/ahujasid/blender-mcp
- https://github.com/AIGODLIKE/GenesisCore
