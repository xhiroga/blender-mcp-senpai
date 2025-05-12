VERSION=$(uv run python -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")
git commit -m "feat: v$VERSION"
git tag v$VERSION
git push
git push --tags
gh release create v$VERSION --generate-notes
gh release upload v$VERSION output/blender_senpai-*.zip
