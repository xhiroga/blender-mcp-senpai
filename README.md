<p align="center">
  <img src="docs/assets/logo.png" alt="Blender Senpai Logo" width="240" height="240">
</p>

<h1 align="center">Blender MCP Senpai</h1>
<p align="center"><em>Your AI-assisted mentor for Blender.</em></p>

<p align="center">
  <a href="https://github.com/xhiroga/blender-mcp-senpai/actions">
    <img alt="CI" src="https://github.com/xhiroga/blender-mcp-senpai/actions/workflows/ci.yml/badge.svg">
  </a>
  <img alt="Blender 4.2+" src="https://img.shields.io/badge/Blender-4.2%2B-orange?logo=blender">
  <img alt="GPL-3.0" src="https://img.shields.io/badge/license-GPL--3.0-blue">
  <a href="https://github.com/sponsors/xhiroga">
    <img alt="Sponsor" src="https://img.shields.io/github/sponsors/xhiroga?style=social">
  </a>
  <a href="https://discord.gg/7z9HqgR8Bd">
    <img alt="Discord" src="https://img.shields.io/discord/1352831203597877311?label=Discord&logo=discord&style=flat">
  </a>
</p>

---

<h2 align="center">Feedback welcome! Feel free to open an <a href="https://github.com/xhiroga/blender-mcp-senpai/issues">Issue</a> or join our <a href="https://discord.gg/7z9HqgR8Bd">Discord</a></h2>

---

## ✨ TL;DR

- Instantly detects and highlights n-gons and topology issues  
- ChatGPT / Claude / Gemini offer real-time improvement suggestions  
- Zero-setup: just install the add-on — no external MCP server required  

---

## 🚀 Features

| | Feature | Status |
|---|---|---|
| ✅ | **Auto n-gon Highlight** – instantly spot topology issues | Implemented |
| ✅ | **AI Comments** – ChatGPT / Claude / Gemini suggest improvements | Implemented |
| ✅ | **Zero Configuration** – works out-of-the-box, no external MCP client | Implemented |
| 🚧 | Asset Store Integration | Planned |

---

## 📺 Demo

[![Blender Senpai Demo](https://img.youtube.com/vi/4oX0ftZ07LE/0.jpg)](https://www.youtube.com/watch?v=4oX0ftZ07LE)

---

## 🛠️ Quick Start

### To Blender

- Open Blender
- Go to `Edit` > `Preferences` > `Get Extensions` > `Repositories` > `+` > `Add Remote Repository`
- Add `https://xhiroga.github.io/blender-mcp-senpai/extensions/index.json`
- Search `Blender Senpai` and install it
- `Add-ons` > `Blender Senpai` > Enable it

### To Claude, Cline, Roo Code

NOTE: After configuration, you need to restart the app. Especially on Windows, please terminate the process from Task Manager.

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

## 🔧 Development

See [.github/pull_request_template.md](.github/pull_request_template.md).

### Release

```sh
# Update version in `pyproject.toml`
uv run --env-file .env build.py
# Install extension to Blender and check if it works.
git add docs/extensions/index.json pyproject.toml uv.lock
./scripts/release.sh
```
