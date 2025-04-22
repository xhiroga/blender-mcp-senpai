# Blender MCP Senpai

Your senpai (先輩, mentor) of Blener.

## About

TODO...

## Installation

### To Blender

- Open Blender
- Go to `Edit` > `Preferences` > `Get Extensions` > `Repositories` > `+`
- Add `https://xhiroga.github.io/blender-mcp-senpai/extensions/index.json`
- Search `MCP Senpai` and install it

### To Claude / Cursor / Other AI Agents

```json
{
    "mcpServers": {
        "blender-mcp-senpai": {
            "command": "uvx",
            "args": [
                "mcp-server",
                "--repository",
                "https://github.com/xhiroga/blender-mcp-senpai"
            ]
        }
    }
}
```

## Features

- [x] Indexing Blender documents
- [x] Search documents by DuckDB-VSS
- [ ] Use RAG through MCP
- [x] Install MCP server by Repository
- [ ] List resources through MCP
- [ ] Describe Blender version through MCP
- [ ] Send Blender screenshot through MCP
