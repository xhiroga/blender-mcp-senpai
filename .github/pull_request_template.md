# Pull Request Template

## 🔥 Issue

<!-- Links to issues, requests, and bugs -->

## 📝 Summary

<!-- What does this PR solve? -->

## 🔄 Changes

<!-- List the main changes. If there are UI changes, include screenshots. -->

## ✅ Manual QA

- [ ] `uv run --env-file .env build.py` successfully built
- [ ] `uv run -m src.blender_senpai.server`
  - [ ] `curl -N http://localhost:13180/sse`
  - [ ] `npx @modelcontextprotocol/inspector@latest npx -y supergateway --sse http://localhost:13180/sse`
- [ ] `uv run -m src.blender_senpai.webui` successfully started

## 👂 etc

<!-- Please note any additional information. -->
