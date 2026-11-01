"""
Database connection and initialization module for Scholarship Intelligence Crawler.
"""
import json
import sqlite3
from pathlib import Path
from config.settings import DB_PATH, SOURCE_REGISTRY_PATH


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Returns a configured SQLite connection with foreign keys enabled and dict-like rows."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def initialize_database(db_path: Path = DB_PATH, recreate: bool = False):
    """Initializes tables using schema.sql and loads source registry."""
    if recreate and db_path.exists():
        db_path.unlink()

    schema_path = Path(__file__).resolve().parent / "schema.sql"
    with get_connection(db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        
        # Populate sources table from source_registry.json if not present
        if SOURCE_REGISTRY_PATH.exists():
            sources = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
            for src in sources:
                conn.execute(
                    """
                    INSERT INTO sources (domain, provider, source_type, official, root_url, last_checked_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(domain) DO UPDATE SET
                        provider = excluded.provider,
                        source_type = excluded.source_type,
                        official = excluded.official,
                        root_url = excluded.root_url
                    """,
                    (
                        src["domain"],
                        src.get("provider", "Unknown Provider"),
                        src["source_type"],
                        1 if src.get("official") else 0,
                        src["root_url"]
                    )
                )
        conn.commit()
    print(f"Database initialized successfully at {db_path}")


if __name__ == "__main__":
    initialize_database()
