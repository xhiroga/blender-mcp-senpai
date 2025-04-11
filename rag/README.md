# RAG

## Develop

```sh
uv run main.py
duckdb
D SELECT *, array_cosine_distance(embeddings::float[384], ...) as distance FROM 'file://./datasets/**/*.parquet' ORDER BY distance LIMIT 5
```

## Deploy

```sh
# TODO: Upload documents to HuggingFace Hub
```
