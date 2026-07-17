import sqlite3
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/tasks.db")

class TaskStateService:
    """Lightweight SQLite-based task state tracker for asynchronous ingestion."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the tasks table."""
        with self._get_conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    result TEXT,
                    error_message TEXT
                )
                """
            )
            conn.commit()

    def create_task(self) -> str:
        """Create a new task with PENDING status and return the task_id."""
        task_id = str(uuid.uuid4())
        now = datetime.utcnow()
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO tasks (task_id, status, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, "PENDING", now, now)
            )
            conn.commit()
        return task_id

    def update_task_status(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None, 
        error_message: Optional[str] = None
    ) -> None:
        """Update the status of a given task."""
        now = datetime.utcnow()
        result_str = json.dumps(result) if result is not None else None
        
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = ?, result = ?, error_message = ?
                WHERE task_id = ?
                """,
                (status, now, result_str, error_message, task_id)
            )
            conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task by ID."""
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            task = dict(row)
            if task.get("result"):
                try:
                    task["result"] = json.loads(task["result"])
                except json.JSONDecodeError:
                    pass
            return task
