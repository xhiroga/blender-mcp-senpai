.PHONY: dev

frontend/node_modules:
	cd frontend && pnpm install

dev: frontend/node_modules
	cd frontend && pnpm build
	uv run -m src.blender_senpai.server
