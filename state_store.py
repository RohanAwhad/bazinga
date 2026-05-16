"""StateStore — persists session history using TinyDB."""

import threading
from pathlib import Path

from google.genai.types import Content
from tinydb import TinyDB, where


class StateStore:
    """Persists session history keyed by (project_path, session_id)."""

    def __init__(self, db_path: str = ".bazinga_sessions.json") -> None:
        self._db = TinyDB(db_path)
        self._table = self._db.table("sessions")
        self._lock = threading.Lock()

    def save_session(
        self, project_path: str, session_id: str, history: list[Content]
    ) -> None:
        """Serialize and persist session history."""
        serialized = [content.to_json_dict() for content in history]
        record = {
            "project_path": project_path,
            "session_id": session_id,
            "history": serialized,
        }
        # Upsert: update if exists, insert if not
        match = (where("project_path") == project_path) & (
            where("session_id") == session_id
        )
        with self._lock:
            existing = self._table.search(match)
            if existing:
                self._table.update(record, match)
            else:
                self._table.insert(record)

    def load_session(
        self, project_path: str, session_id: str
    ) -> list[Content]:
        """Load and deserialize session history. Returns empty list for unknown sessions."""
        match = (where("project_path") == project_path) & (
            where("session_id") == session_id
        )
        with self._lock:
            results = self._table.search(match)
        if not results:
            return []
        serialized = results[0]["history"]
        return [Content.model_validate(item) for item in serialized]
