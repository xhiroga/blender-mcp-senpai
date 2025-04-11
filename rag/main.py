import uuid
import git
import logging
from pathlib import Path
import pyarrow.parquet as pq
import pandas as pd
import pyarrow as pa
from sentence_transformers import SentenceTransformer


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")
REPOSITORIES = [
    {
        "url": "https://projects.blender.org/blender/blender-manual",
        "name": "blender-manual",
        "branch": "blender-v4.4-release",
        "language": "en",
        "version": "v4.4",
        "document_dir": "manual",
        "hosted_url_base": "https://docs.blender.org/manual/en/4.4/",
        "is_latest": True,
    }
]
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def clone_or_pull_repo(repo: dict, input_dir: Path):
    repo_url = repo["url"]
    repo_name = repo["name"]
    branch = repo.get("branch", "main")
    local_dir = input_dir/ repo_name

    if local_dir.exists() and (local_dir / ".git").exists():
        logging.info(f"Pulling latest changes for {repo_name} from {branch} branch...")
        try:
            repo_obj = git.Repo(local_dir)
            origin = repo_obj.remotes.origin
            origin.fetch()
            repo_obj.git.checkout(branch)
            origin.pull()
            logging.info(f"Successfully updated {repo_name} to latest {branch}")
        except Exception as e:
            logging.error(f"Failed to pull repository {repo_name}: {e}")
    else:
        logging.info(f"Cloning {repo_name} from {repo_url}, branch {branch}...")
        try:
            git.Repo.clone_from(repo_url, local_dir, branch=branch)
            logging.info(f"Successfully cloned {repo_name} to {local_dir}")
        except Exception as e:
            logging.error(f"Failed to clone repository {repo_name}: {e}")


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if not text or chunk_size <= 0 or chunk_overlap < 0 or chunk_size <= chunk_overlap:
        logging.error("Invalid parameters for chunking text.")
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        step = chunk_size - chunk_overlap
        start += step

    return chunks


def get_hosted_url(file_path: Path, doc_root_in_repo: Path, base_url: str) -> str:
    try:
        relative_path_in_doc = file_path.relative_to(doc_root_in_repo)
        html_path = relative_path_in_doc.with_suffix(".html")
        url_path = str(html_path).replace("\\", "/")
        if not base_url.endswith("/"):
            base_url += "/"
        return base_url + url_path.lstrip("/")
    except ValueError:
        logging.warning(
            f"Could not determine relative path for URL generation: {file_path} relative to {doc_root_in_repo}"
        )
        return base_url


def repo_to_dataframe(repo: dict, model: SentenceTransformer) -> pd.DataFrame:
    repo_name = repo["name"]
    version = repo["version"]
    repo_dir = INPUT_DIR / repo_name
    full_doc_dir = repo_dir / repo["document_dir"]
    hosted_url_base = repo["hosted_url_base"]

    logging.info(
        f"Processing documents in {full_doc_dir} for {repo_name} ({version})..."
    )

    if not full_doc_dir.is_dir():
        logging.error(
            f"Document directory not found: {full_doc_dir}. Skipping repository {repo_name}."
        )
        return pd.DataFrame()

    rst_files = list(full_doc_dir.rglob("*.rst"))
    logging.info(f"Found {len(rst_files)} rst files.")

    texts_to_embed = []
    metadata_for_texts = []

    for file_path in rst_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                rst_content = f.read()

            text_chunks = chunk_text(rst_content, CHUNK_SIZE, CHUNK_OVERLAP)

            for i, chunk in enumerate(text_chunks):
                chunk_id = str(uuid.uuid4())
                relative_file_path_from_repo = file_path.relative_to(repo_dir)
                hosted_url = get_hosted_url(file_path, full_doc_dir, hosted_url_base)

                metadata = {
                    "id": chunk_id,
                    "source": str(relative_file_path_from_repo).replace("\\", "/"),
                    "hosted_url": hosted_url,
                    "chunk_index": i,
                    "repo_name": repo_name,
                }
                texts_to_embed.append(chunk)
                metadata_for_texts.append(metadata)

        except Exception as e:
            logging.warning(f"Error processing file {file_path}: {e}")

    logging.info(
        f"Generating embeddings for {len(texts_to_embed)} chunks from {repo_name} using {EMBEDDING_MODEL_NAME}..."
    )
    embeddings = model.encode(texts_to_embed, show_progress_bar=True, batch_size=128)

    logging.info(f"Creating DataFrame for {repo_name}...")
    embedding_lists = [emb.tolist() for emb in embeddings]

    df_data = []
    for i, meta in enumerate(metadata_for_texts):
        df_data.append(
            {
                "id": meta["id"],
                "text": texts_to_embed[i],
                "vector": embedding_lists[i],
                "language": repo["language"],
                "version": repo["version"],
                "hosted_url": meta["hosted_url"],
                "repo_name": meta["repo_name"],
                "source": meta["source"],
            }
        )

    df = pd.DataFrame(df_data)
    logging.info(f"Created DataFrame with {len(df)} rows for {repo_name}.")
    return df


def save_to_parquet(df: pd.DataFrame, filename: str):
    try:
        schema = pa.schema(
            [
                ("id", pa.string()),
                ("text", pa.string()),
                ("vector", pa.list_(pa.float32())),
                ("language", pa.string()),
                ("version", pa.string()),
                ("hosted_url", pa.string()),
                ("repo_name", pa.string()),
                ("source",  pa.string()),
            ]
        )
        table = pa.Table.from_pandas(df, schema=schema)
        pq.write_table(table, filename, compression="snappy")
        logging.info(f"Saved DataFrame to {filename}.")
    except Exception as e:
        logging.error(f"Failed to save DataFrame to {filename}: {e}")


def main():
    logging.info("Starting RAG DB build process...")
    try:
        for repo in REPOSITORIES:
            INPUT_DIR.mkdir(parents=True, exist_ok=True)
            clone_or_pull_repo(repo, INPUT_DIR)
            dataframe = repo_to_dataframe(repo, SentenceTransformer(EMBEDDING_MODEL_NAME))
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            parquet_filename = OUTPUT_DIR / f"{repo['name']}.parquet"
            save_to_parquet(dataframe, parquet_filename)

    except Exception as e:
        logging.error(f"RAG DB build process failed: {e}")


if __name__ == "__main__":
    main()
