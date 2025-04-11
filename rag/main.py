import git
import logging
from pathlib import Path


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

RESOURCES_DIR = Path("resources")
REPOSITORIES = [
    {
        "url": "https://projects.blender.org/blender/blender-manual",
        "name": "blender-manual",
        "branch": "blender-v4.4-release",
        "version": "v4.4",
        "latest": True,
        "document_dir": "manual",
    }
]
DB_FILE = "docs.duckdb"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Matches 384 dimensions
EMBEDDING_DIMENSIONS = 384  # Dimension size for the chosen model


def clone_or_pull_repo(repo: dict):
    repo_url = repo["url"]
    repo_name = repo["name"]
    branch = repo.get("branch", "main")
    local_dir = RESOURCES_DIR / repo_name

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


def main():
    """Main function to orchestrate cloning, processing, and database creation."""
    logging.info("Starting RAG DB build process...")
    try:
        for repo in REPOSITORIES:
            clone_or_pull_repo(repo)
            document_dir = RESOURCES_DIR / repo["name"] / repo["document_dir"]
            print(f"Document directory: {document_dir}")
    except Exception as e:
        logging.error(f"RAG DB build process failed: {e}")


if __name__ == "__main__":
    main()
