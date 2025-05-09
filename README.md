# Blender Senpai

![Logo](docs/assets/logo/logo.png)

Your senpai (先輩, mentor) of Blener.

## About

Get instant answers to your Blender file questions from ChatGPT/Claude/Gemini/...!

## Features

✅ Ask questions about your currently open Blender file to ChatGPT/Claude/Gemini/...!  
✅ No complicated MCP server setup required! Just a Blender extension  
✅ Detailed explanations of Blender concepts with GIF animations  
✅ Multi-language support  
🚧 Save chat history locally  
🚧 Automatically share workspace state with AI through images  
🚧 Automatically reference version-specific Blender documentation and FAQs  
🚧 Integration with Asset Store  

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
./scripts/release.sh
```
