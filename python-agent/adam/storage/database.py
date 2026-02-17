"""
SQLite database management for Adam.
Provides encrypted storage using SQLCipher when available, falls back to standard SQLite.
"""

import sqlite3
import hashlib
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
from datetime import datetime


class AdamDatabase:
    """
    SQLite database manager with optional encryption support.

    Uses SQLCipher if available, otherwise standard SQLite with
    application-level encryption for sensitive data.
    """

    def __init__(self, db_path: Path, key: str = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
            key: Optional encryption key (for SQLCipher)
        """
        self.db_path = Path(db_path)
        self.key = key
        self._connection: Optional[sqlite3.Connection] = None
        self._use_sqlcipher = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._connection is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            if self.key:
                try:
                    import sqlcipher3

                    self._connection = sqlcipher3.connect(str(self.db_path))
                    self._connection.execute(f"PRAGMA key='{self.key}'")
                    self._use_sqlcipher = True
                except ImportError:
                    self._connection = sqlite3.connect(str(self.db_path))
            else:
                self._connection = sqlite3.connect(str(self.db_path))

            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.row_factory = sqlite3.Row

        return self._connection

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database operations with auto-commit."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def init_schema(self) -> None:
        """Initialize database schema."""
        with self.connection() as conn:
            conn.executescript("""
                -- Sessions table
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    profile TEXT DEFAULT 'balanced',
                    model TEXT,
                    metadata JSON
                );
                
                -- Messages table
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant', 'tool')),
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Audit log table
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    event_data JSON,
                    session_id TEXT,
                    hash TEXT
                );
                
                -- State table for key-value storage
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
                CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type);
            """)

    def create_session(
        self, session_id: str, profile: str = "balanced", model: str = None, metadata: dict = None
    ) -> str:
        """Create a new session."""
        with self.connection() as conn:
            conn.execute(
                """INSERT INTO sessions (id, profile, model, metadata) 
                   VALUES (?, ?, ?, ?)""",
                (session_id, profile, model, json.dumps(metadata or {})),
            )
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row:
                return dict(row)
        return None

    def add_message(self, message_id: str, session_id: str, role: str, content: str) -> None:
        """Add a message to a session."""
        with self.connection() as conn:
            conn.execute(
                """INSERT INTO messages (id, session_id, role, content) 
                   VALUES (?, ?, ?, ?)""",
                (message_id, session_id, role, content),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,)
            )

    def get_messages(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a session."""
        with self.connection() as conn:
            rows = conn.execute(
                """SELECT * FROM messages 
                   WHERE session_id = ? 
                   ORDER BY created_at DESC 
                   LIMIT ?""",
                (session_id, limit),
            ).fetchall()
            return [dict(row) for row in reversed(rows)]

    def log_event(self, event_type: str, event_data: dict = None, session_id: str = None) -> None:
        """Log an audit event."""
        with self.connection() as conn:
            data_str = json.dumps(event_data or {}, sort_keys=True)
            hash_val = hashlib.sha256(
                f"{event_type}{data_str}{datetime.utcnow().isoformat()}".encode()
            ).hexdigest()[:16]

            conn.execute(
                """INSERT INTO audit_log (event_type, event_data, session_id, hash) 
                   VALUES (?, ?, ?, ?)""",
                (event_type, json.dumps(event_data or {}), session_id, hash_val),
            )

    def get_audit_log(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """Get audit log entries."""
        with self.connection() as conn:
            if event_type:
                rows = conn.execute(
                    """SELECT * FROM audit_log 
                       WHERE event_type = ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?""",
                    (event_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM audit_log 
                       ORDER BY timestamp DESC 
                       LIMIT ?""",
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]

    def set_state(self, key: str, value: str) -> None:
        """Set a state value."""
        with self.connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO state (key, value, updated_at) 
                   VALUES (?, ?, CURRENT_TIMESTAMP)""",
                (key, value),
            )

    def get_state(self, key: str) -> Optional[str]:
        """Get a state value."""
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def close(self) -> None:
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
