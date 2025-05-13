## 🔥 Issue

<!-- Links to issues, requests, and bugs -->

## 📝 Summary

<!-- What does this PR solve? -->

## 🔄 Changes

<!-- List the main changes. If there are UI changes, include screenshots. -->

## ✅ Manual QA

- [ ] `uv run -m pytest`
- [ ] `uv run -m src.blender_senpai.server`
  - [ ] `curl -N http://localhost:${PORT}/sse`
  - [ ] `npx @modelcontextprotocol/inspector@latest npx -y supergateway --sse http://localhost:${PORT}/sse`
  - [ ] `execute_code -> import bpy; bpy.ops.mesh.primitive_cube_add();` successfully executed TWICE
  - [ ] `get_objects` successfully executed
- [ ] `uv run --env-file .env build.py` successfully built and install to Blender
  - [ ] `curl -N http://localhost:${PORT}/sse`
  - [ ] `npx @modelcontextprotocol/inspector@latest npx -y supergateway --sse http://localhost:${PORT}/sse`
  - [ ] `execute_code -> import bpy; bpy.ops.mesh.primitive_cube_add();` successfully executed TWICE
  - [ ] `get_objects` successfully executed
- [ ] Open Dive
  - [ ] `execute_code -> import bpy; bpy.ops.mesh.primitive_cube_add();` successfully executed TWICE
  - [ ] `get_objects` successfully executed

### ✨ `.blend`

- [ ] Blender is set to English language for creation and editing
- [ ] Assets to be appended have the prefix `BLSP.` in their names
- [ ] Assets to be appended have Fake User enabled
- [ ] Unnecessary objects (lights, cameras, etc.) have been removed
- [ ] `File > Clean Up > Purge Unused Data...` has been executed before saving
- [ ] When updating assets, create new ones with version numbers (e.g., `BLSP.SomeAsset.V2`) instead of updating existing ones
- [ ] Also edit `src/blender_senpai/assets/__init__.py` to update the asset list

## 👂 etc

<!-- Please note any additional information. -->
