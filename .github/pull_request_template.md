# Pull Request Template

## 🔥 Issue

<!-- Links to issues, requests, and bugs -->

## 📝 Summary

<!-- What does this PR solve? -->

## 🔄 Changes

<!-- List the main changes. If there are UI changes, include screenshots. -->

## ✅ Manual QA

- [ ] `uv run -m pytest`
- [ ] `uv run --env-file .env build.py` successfully built
  - [ ] `curl -N http://localhost:${PORT}/sse`
  - [ ] `npx @modelcontextprotocol/inspector@latest npx -y supergateway --sse http://localhost:${PORT}/sse`
  - [ ] `execute_code -> import bpy; bpy.ops.mesh.primitive_cube_add();` successfully executed
- [ ] `uv run -m src.blender_senpai.server`
  - [ ] `curl -N http://localhost:${PORT}/sse`
  - [ ] `npx @modelcontextprotocol/inspector@latest npx -y supergateway --sse http://localhost:${PORT}/sse`
  - [ ] `execute_code -> import bpy; bpy.ops.mesh.primitive_cube_add();` successfully executed
- [ ] Open Claude Desktop
  - [ ] `execute_code -> import bpy; bpy.ops.mesh.primitive_cube_add();` successfully executed TWICE

## 👂 etc

<!-- Please note any additional information. -->
