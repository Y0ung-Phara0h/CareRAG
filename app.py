"""
CareRAG — FastAPI REST API & Single-Page Web Application Server
--------------------------------------------------------------
Team: Sa3ayda Geeks
Provides REST API endpoints for clinical query, multi-turn session management,
and file exporting while serving the glassmorphic static web UI.
"""
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query as APIQuery
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from query import load_index, retrieve
from generate import generate_grounded_answer
from session_manager import SessionManager

logger = config.setup_logger()

# Initialize FastAPI App
app = FastAPI(
    title=f"{config.PROJECT_NAME} Clinical Decision Support API",
    description=f"REST API server for grounded clinical RAG and session management by {config.TEAM_NAME}.",
    version="1.0.0"
)

# Initialize SessionManager & Vector Index
session_mgr = SessionManager()
try:
    vector_db = load_index()
    logger.info("ChromaDB & BM25 vector index loaded successfully for REST API.")
except Exception as e:
    logger.warning(f"Could not initialize vector DB at server startup: {e}")
    vector_db = None


# --- Pydantic API DTOs ---

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Consultation"


# --- REST Endpoints ---

@app.get("/api/health")
def health_check():
    """Health check endpoint returning server and index readiness status."""
    return {
        "status": "healthy",
        "project": config.PROJECT_NAME,
        "team": config.TEAM_NAME,
        "index_loaded": vector_db is not None
    }


@app.get("/api/sessions")
def list_sessions():
    """Lists all persistent consultation sessions ordered by last update."""
    return session_mgr.list_sessions()


@app.post("/api/sessions")
def create_session(req: CreateSessionRequest):
    """Creates a new consultation session."""
    session = session_mgr.create_session(title=req.title or "New Consultation")
    return session.dict()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    """Retrieves full session metadata and message thread."""
    session = session_mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session.dict()


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Deletes a consultation session."""
    deleted = session_mgr.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "success", "session_id": session_id}


@app.post("/api/query")
def process_query(req: QueryRequest):
    """Executes clinical hybrid RAG, records user/assistant turns, and returns grounded response."""
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Question string cannot be empty.")

    # 1. Manage Session
    if req.session_id:
        session = session_mgr.get_session(req.session_id)
        if not session:
            session = session_mgr.create_session(title=req.question[:30])
    else:
        session = session_mgr.create_session(title=req.question[:30])

    active_session_id = session.session_id

    # 2. Retrieve history for prompt context
    history = session_mgr.get_recent_history(active_session_id, max_turns=config.MAX_HISTORY_TURNS)

    # 3. Hybrid Search
    global vector_db
    if vector_db is None:
        try:
            vector_db = load_index()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Index not available: {e}")

    retrieved_chunks = retrieve(vector_db, req.question)

    # 4. Grounded Generation
    grounded_res = generate_grounded_answer(req.question, retrieved_chunks, chat_history=history)

    # 5. Persist Turns in SQLite
    raw_citations = grounded_res.get("citations", [])
    formatted_citations = []
    for c in raw_citations:
        if isinstance(c, dict):
            formatted_citations.append({
                "document_name": c.get("document", c.get("document_name", "Unknown")),
                "page_number": c.get("page", c.get("page_number", 1)),
                "section": c.get("section", "N/A"),
                "chunk_id": c.get("chunk_id", f"{c.get('document', 'doc')}-p{c.get('page', 1)}")
            })
        else:
            formatted_citations.append(c)

    session_mgr.add_message(active_session_id, role="user", content=req.question)
    session_mgr.add_message(
        active_session_id,
        role="assistant",
        content=grounded_res.get("recommendation", ""),
        citations=formatted_citations
    )

    return {
        "session_id": active_session_id,
        "recommendation": grounded_res.get("recommendation", ""),
        "evidence": grounded_res.get("evidence", ""),
        "citations": grounded_res.get("citations", []),
        "confidence": grounded_res.get("confidence", "insufficient")
    }


@app.get("/api/sessions/{session_id}/export")
def export_session(session_id: str, format: str = APIQuery("markdown")):
    """Exports session thread to JSON or Markdown file and returns it for download."""
    try:
        export_file = session_mgr.export_session(session_id, format_type=format)
        media_type = "application/json" if format.lower() == "json" else "text/markdown"
        return FileResponse(export_file, filename=export_file.name, media_type=media_type)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    """Deletes a session and all its messages permanently."""
    success = session_mgr.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": f"Session {session_id} deleted."}


# --- Serve Static UI Files ---
static_dir = config.BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
