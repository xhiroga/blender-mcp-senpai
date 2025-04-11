from pathlib import Path

import duckdb
import pytest
from sentence_transformers import SentenceTransformer


def query(query: str, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", table: str = 'output/**/*.parquet', embedding_column: str = "vector", limit: int = 5, ):
    model = SentenceTransformer(model_name)
    query_vector = model.encode(query)
    embedding_dim = model.get_sentence_embedding_dimension()

    sql = f"""
        SELECT 
            *,
            array_cosine_distance(
                {embedding_column}::float[{embedding_dim}], 
                {query_vector.tolist()}::float[{embedding_dim}]
            ) as distance
        FROM '{table}'
        ORDER BY distance
        LIMIT {limit}
    """

    df = duckdb.sql(sql).to_df()
    return df


@pytest.mark.adhoc()
def test_query():
    if not Path("output").exists():
        return
    df = query(
        "What is Blender?",
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        table="output/**/*.parquet",
        embedding_column="vector",
        limit=5,
    )
    assert df is not None
    assert any("Blender" in text for text in df["text"].tolist())
