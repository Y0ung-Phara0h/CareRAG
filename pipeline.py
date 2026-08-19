"""
CareRAG — End-to-End Grounded RAG Pipeline & Multi-Turn Session CLI
-------------------------------------------------------------------
Team: Sa3ayda Geeks
Combines hybrid retrieval (ChromaDB + BM25), grounded generation (Gemini),
and persistent SQLite multi-turn session management.

Usage:
    python pipeline.py "What blood pressure threshold should trigger starting medication?"
    python pipeline.py --session <session_id> "What is the second line treatment?"
"""
import json
import sys
from typing import Optional

import config
from query import load_index, retrieve, print_results
from generate import generate_grounded_answer
from session_manager import SessionManager

logger = config.setup_logger()


def run_pipeline(question: str, session_id: Optional[str] = None) -> dict:
    """Executes the complete RAG pipeline with hybrid retrieval, history truncation, and session storage."""
    sm = SessionManager()

    if session_id:
        session = sm.get_session(session_id)
        if not session:
            logger.warning(f"Session '{session_id}' not found. Creating a new session.")
            session = sm.create_session(title=question[:30])
    else:
        session = sm.create_session(title=question[:30])

    active_session_id = session.session_id
    logger.info(f"Active Session ID: {active_session_id}")

    # Fetch prior history for sliding-window prompt context
    recent_history = sm.get_recent_history(active_session_id, max_turns=config.MAX_HISTORY_TURNS)

    print("=" * 65)
    print(f" {config.BRAND_HEADER} — Clinical Pipeline ===")
    print("=" * 65)
    logger.info(f"Question: {question}\n")

    # Step 1: Hybrid Retrieval (ChromaDB + BM25 via RRF)
    logger.info("--- Step 1: Hybrid Document Retrieval (ChromaDB + BM25) ---")
    try:
        vectordb = load_index()
        results = retrieve(vectordb, question)
        print_results(results)
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        logger.info("Make sure you have run 'python ingest.py' first to build the indices.")
        sys.exit(1)

    # Step 2: Grounded Generation (Gemini) with Multi-Turn Context
    logger.info("--- Step 2: Grounded Generation (Gemini) ---")
    response = generate_grounded_answer(question, results, chat_history=recent_history)

    # Step 3: Record turns in persistent SQLite SessionManager
    sm.add_message(active_session_id, role="user", content=question)

    citations = response.get("citations", [])
    sm.add_message(
        active_session_id,
        role="assistant",
        content=response.get("recommendation", ""),
        citations=citations
    )

    # Step 4: Formatted Output
    print("\n" + "=" * 65)
    print(f" === Final CareRAG Clinical Response (Session: {active_session_id[:8]}) ===")
    print("=" * 65)
    print(f"\nRecommendation:\n  {response.get('recommendation')}\n")
    print(f"Confidence Level: {response.get('confidence', 'UNKNOWN').upper()}\n")

    evidence = response.get("evidence")
    if evidence:
        print(f"Evidence Excerpt:\n  \"{evidence}\"\n")

    if citations:
        print("Citations:")
        for i, cit in enumerate(citations, 1):
            doc = cit.get("document", "Unknown")
            sec = cit.get("section", "N/A")
            page = cit.get("page", "?")
            print(f"  [{i}] Document: {doc} | Page: {page} | Section: {sec}")
    else:
        print("Citations: None (Refusal / Insufficient Evidence)")

    print("\nStructured JSON Response:")
    print(json.dumps(response, indent=2))
    print("=" * 65)
    return response


def main():
    if len(sys.argv) < 2:
        print('Usage: python pipeline.py "your question here"')
        print('       python pipeline.py --session <session_id> "follow up question"')
        sys.exit(1)

    session_id = None
    args = sys.argv[1:]
    if args[0] == "--session" and len(args) >= 3:
        session_id = args[1]
        question = " ".join(args[2:])
    else:
        question = " ".join(args)

    run_pipeline(question, session_id=session_id)


if __name__ == "__main__":
    main()
