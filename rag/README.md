# RAG

## Develop

```sh
uv run main.py
duckdb
D SELECT * FROM 'output/**/*.parquet' LIMIT 5;
```

## Test

```sh
uv run pytest -m adhoc
```

## Deploy

```sh
# TODO: Upload documents to HuggingFace Hub
```
