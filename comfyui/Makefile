include .env	# COMFY_BASE_PATH, TMP

# Set default TMP to /tmp if it's empty
TMP ?= /tmp

.PHONY: run init compile

run:
	uv run ComfyUI/main.py --enable-cors-header --extra-model-paths-config extra_model_paths.yaml --fast --listen --port 13188

init: ComfyUI ComfyUI/user/default/workflows ComfyUI/custom_nodes/ComfyUI-Hunyuan3DWrapper ComfyUI/custom_nodes/ComfyUI_essentials compile $(COMFY_BASE_PATH)/models/diffusion_models/hunyuan3d-dit-v2-0-fp16.safetensors

compile: ComfyUI ComfyUI/custom_nodes/ComfyUI-Hunyuan3DWrapper
	cd ComfyUI/custom_nodes/ComfyUI-Hunyuan3DWrapper/hy3dgen/texgen/custom_rasterizer && \
	uv run --project $(PWD)/pyproject.toml --python $(shell which python3.11) setup.py bdist_wheel && \
	uv add --project $(PWD)/pyproject.toml --python $(shell which python3.11) dist/*.whl

ComfyUI:
	git -C $@ pull || git clone https://github.com/comfyanonymous/ComfyUI $@

$(TMP):
	mkdir -p $@

ComfyUI/user/default/workflows: ComfyUI/user/default/workflows/.installed
ComfyUI/user/default/workflows/.installed:
	mkdir -p ComfyUI/user/default/workflows
	ln -fsr workflows/* ComfyUI/user/default/workflows
	touch $@

ComfyUI/custom_nodes/ComfyUI-Hunyuan3DWrapper:
	git -C $@ pull || git clone https://github.com/kijai/ComfyUI-Hunyuan3DWrapper $@

ComfyUI/custom_nodes/ComfyUI_essentials:
	git -C $@ pull || git clone https://github.com/cubiq/ComfyUI_essentials $@

$(COMFY_BASE_PATH)/models/diffusion_models/hunyuan3d-dit-v2-0-fp16.safetensors:
	uv run huggingface-cli download Kijai/Hunyuan3D-2_safetensors hunyuan3d-dit-v2-0-fp16.safetensors --revision main --local-dir $(TMP)/Kijai/Hunyuan3D-2_safetensors
	mv $(TMP)/Kijai/Hunyuan3D-2_safetensors/hunyuan3d-dit-v2-0-fp16.safetensors $@
