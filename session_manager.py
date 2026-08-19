"""
CareRAG — SessionManager Module
--------------------------------
Team: Sa3ayda Geeks
Provides SQLite persistent storage for chat sessions, user/assistant messages,
citation metadata, sliding-window turn history, and JSON/Markdown exporters.
"""
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

import config

logger = config.setup_logger()


class CitationModel(BaseModel):
    document_name: str
    page_number: int
    section: str = "N/A"
    chunk_id: str


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    citations: Optional[List[CitationModel]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ChatSession(BaseModel):
    session_id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[ChatMessage] = Field(default_factory=list)


class SessionManager:
    """Manages creation, loading, history tracking, and exporting of CareRAG chat sessions using SQLite."""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.SESSION_DB_PATH
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes SQLite database tables for sessions and messages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    citations_json TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)
            conn.commit()

    def create_session(self, title: str = "New Consultation") -> ChatSession:
        """Creates a new session in SQLite database."""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now, now)
            )
            conn.commit()
        logger.info(f"Created session {session_id[:8]}... ('{title}')")
        return ChatSession(session_id=session_id, title=title, created_at=now, updated_at=now, messages=[])

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retrieves a full session with chronologically ordered messages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, title, created_at, updated_at FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None

            s_id, title, created_at, updated_at = row
            cursor.execute("SELECT role, content, citations_json, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
            msg_rows = cursor.fetchall()

            messages = []
            for role, content, citations_json, ts in msg_rows:
                citations = None
                if citations_json:
                    try:
                        raw_citations = json.loads(citations_json)
                        citations = [CitationModel(**c) for c in raw_citations]
                    except Exception:
                        citations = None
                messages.append(ChatMessage(role=role, content=content, citations=citations, timestamp=ts))

            return ChatSession(session_id=s_id, title=title, created_at=created_at, updated_at=updated_at, messages=messages)

    def list_sessions(self) -> List[dict]:
        """Lists all persistent sessions ordered by updated_at descending."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [{"session_id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]} for r in rows]

    def add_message(self, session_id: str, role: str, content: str, citations: list = None) -> ChatMessage:
        """Appends a user or assistant message to a session atomically."""
        now = datetime.now().isoformat()
        citations_json = None
        if citations:
            raw_cits = [c.dict() if hasattr(c, "dict") else c for c in citations]
            citations_json = json.dumps(raw_cits)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (session_id, role, content, citations_json, timestamp) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, citations_json, now)
            )
            cursor.execute("UPDATE sessions SET updated_at = ? WHERE session_id = ?", (now, session_id))
            conn.commit()

        parsed_citations = [CitationModel(**c) if isinstance(c, dict) else c for c in (citations or [])]
        return ChatMessage(role=role, content=content, citations=parsed_citations, timestamp=now)

    def get_recent_history(self, session_id: str, max_turns: int = None) -> List[ChatMessage]:
        """Returns the most recent N turns for prompt sliding-window context."""
        max_turns = max_turns or config.MAX_HISTORY_TURNS
        session = self.get_session(session_id)
        if not session or not session.messages:
            return []
        return session.messages[-(max_turns * 2):]

    def export_session(self, session_id: str, format_type: str = "json") -> Path:
        """Exports a session to JSON or Markdown file under config.EXPORTS_DIR."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found.")

        export_dir = config.EXPORTS_DIR
        export_dir.mkdir(parents=True, exist_ok=True)

        safe_title = "".join(c if c.isalnum() else "_" for c in session.title)[:30]
        filename = f"{safe_title}_{session_id[:8]}"

        if format_type.lower() == "json":
            file_path = export_dir / f"{filename}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(session.model_dump_json(indent=2))
        elif format_type.lower() in ["md", "markdown"]:
            file_path = export_dir / f"{filename}.md"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"# CareRAG Consultation History: {session.title}\n\n")
                f.write(f"- **Session ID**: `{session.session_id}`\n")
                f.write(f"- **Created At**: {session.created_at}\n")
                f.write(f"- **Updated At**: {session.updated_at}\n\n")
                f.write("--- \n\n")
                for msg in session.messages:
                    f.write(f"### **{msg.role.upper()}** ({msg.timestamp[:19]})\n")
                    f.write(f"{msg.content}\n\n")
                    if msg.citations:
                        f.write("**Citations & Sources**:\n")
                        for cit in msg.citations:
                            f.write(f"- `{cit.document_name}` (Page {cit.page_number}, Section: *{cit.section}*, ChunkID: `{cit.chunk_id}`)\n")
                        f.write("\n")
                    f.write("---\n\n")
        else:
            raise ValueError("Unsupported format. Use 'json' or 'markdown'.")

        logger.info(f"Session exported to {file_path}")
        return file_path

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session from the SQLite database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0


if __name__ == "__main__":
    sm = SessionManager()
    sess = sm.create_session("Unit Test Consultation")
    sm.add_message(sess.session_id, "user", "What is the target BP?")
    sm.add_message(
        sess.session_id,
        "assistant",
        "Target BP is <130/80 mmHg.",
        citations=[{"document_name": "HTN_Guide", "page_number": 5, "section": "3.1 Target BP", "chunk_id": "HTN-p5-c0"}]
    )
    history = sm.get_recent_history(sess.session_id)
    print(f"Retrieved {len(history)} history messages.")
    export_path = sm.export_session(sess.session_id, "markdown")
    print(f"Exported to: {export_path}")
