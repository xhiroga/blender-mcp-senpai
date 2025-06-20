.PHONY: dev

dev: web/node_modules
	cd web && pnpm build
	uv run -m src.blender_senpai.server

web/node_modules:
	cd web && pnpm install
