import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = [
    "get_connection",
    "log_message",
    "generate_conversation_id",
]

# ---------------------------------------------------------------------------
# DB 初期化
# ---------------------------------------------------------------------------

# Blender が動作している場合は公式 API で Config ディレクトリを取得
# そうでない場合はホームディレクトリ直下に fallback する


def _get_config_dir() -> Path:
    try:
        import bpy  # type: ignore

        return Path(bpy.utils.user_resource("CONFIG", path="mcp_senpai"))
    except Exception:  # pragma: no cover – bpy が無い環境
        return Path.home() / ".mcp_senpai"


_CONFIG_DIR = _get_config_dir()
_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = _CONFIG_DIR / "chat_history.db"

# シングルトン接続（check_same_thread=False でマルチスレッド対応）
_connection: sqlite3.Connection | None = None


def _init_db(conn: sqlite3.Connection):
    """テーブルが無ければ作成する"""

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation TEXT NOT NULL,
            ts           INTEGER NOT NULL,
            role         TEXT NOT NULL,
            content      TEXT NOT NULL,
            metadata     TEXT
        );
        """
    )
    # FTS5 テーブル（全文検索）
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
            USING fts5(content, conversation, role, content='messages', content_rowid='id');
            """
        )
    except sqlite3.OperationalError as e:
        # SQLite ビルドに FTS5 が無いケースを無視
        logger.debug("FTS5 not available: %s", e)

    conn.commit()


def get_connection() -> sqlite3.Connection:
    """スレッドごとに共有の接続を返す"""

    global _connection
    if _connection is None:
        _connection = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _init_db(_connection)
    return _connection


# ---------------------------------------------------------------------------
# パブリック API
# ---------------------------------------------------------------------------


def generate_conversation_id() -> str:
    """UUID4 で新しい conversation_id を発行"""

    return str(uuid.uuid4())


def log_message(
    conversation_id: str,
    role: str,
    content: str,
    *,
    ts: int | None = None,
    metadata: str | None = None,
):
    """messages テーブルと FTS テーブルにレコードを追加する"""

    ts_value = ts if ts is not None else int(datetime.utcnow().timestamp() * 1000)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO messages (conversation, ts, role, content, metadata)
        VALUES (?, ?, ?, ?, ?);
        """,
        (conversation_id, ts_value, role, content, metadata),
    )
    # FTS5 はテーブル定義で自動同期されるため insert は不要
    conn.commit()
