.PHONY: dev

dev: frontend/node_modules
	cd frontend && pnpm build
	uv run -m src.blender_senpai.server

frontend/node_modules:
	cd frontend && pnpm install
