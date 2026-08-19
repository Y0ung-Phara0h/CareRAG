"""
CareRAG — Hybrid Retrieval Engine & CLI
----------------------------------------
Team: Sa3ayda Geeks
Loads ChromaDB vector index and BM25 lexical index, executes Reciprocal Rank
Fusion (RRF) to merge candidate results, and returns top-k context chunks
carrying section metadata.

Usage:
    python query.py "What is the target blood pressure for a patient with known cardiovascular disease?"
"""
import pickle
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma

import config
from ingest import get_embedding_function

logger = config.setup_logger()


def load_index():
    """Loads the persisted ChromaDB vector index."""
    if not config.CHROMA_DIR.exists():
        logger.error(f"Vector database not found at {config.CHROMA_DIR}/")
        logger.info("Please run 'python ingest.py' first to index your documents.")
        sys.exit(1)

    embedding_fn = get_embedding_function()
    return Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=embedding_fn,
        persist_directory=str(config.CHROMA_DIR),
    )


def load_bm25_index():
    """Loads the persisted BM25 index and chunk records."""
    if not config.BM25_INDEX_PATH.exists():
        logger.warning(f"BM25 index not found at {config.BM25_INDEX_PATH}. Falling back to vector-only search.")
        return None

    try:
        with open(config.BM25_INDEX_PATH, "rb") as f:
            data = pickle.load(f)
        return data
    except Exception as e:
        logger.error(f"Failed to load BM25 index: {e}")
        return None


def search_bm25(bm25_data: dict, question: str, k: int = 10) -> list:
    """Executes BM25 lexical search and returns top-k Document objects."""
    if not bm25_data:
        return []

    bm25 = bm25_data["bm25"]
    chunks = bm25_data["chunks"]

    tokenized_query = question.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # Rank indices descending by score
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    results = []
    for idx in top_indices:
        record = chunks[idx]
        doc = Document(page_content=record["page_content"], metadata=record["metadata"])
        results.append((doc, float(scores[idx])))
    return results


def reciprocal_rank_fusion(vector_results: list, bm25_results: list, k_constant: int = None, top_k: int = None) -> list:
    """Merges ChromaDB vector results and BM25 lexical results using RRF score."""
    k_constant = k_constant or config.RRF_K_CONSTANT
    top_k = top_k or config.TOP_K

    rrf_scores = {}
    doc_map = {}

    # Helper to generate unique key per chunk
    def get_chunk_key(doc: Document) -> str:
        return doc.metadata.get("chunk_id") or hash(doc.page_content)

    # Process vector results
    for rank, (doc, _score) in enumerate(vector_results, 1):
        key = get_chunk_key(doc)
        doc_map[key] = doc
        rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (k_constant + rank))

    # Process BM25 results
    for rank, (doc, _score) in enumerate(bm25_results, 1):
        key = get_chunk_key(doc)
        doc_map[key] = doc
        rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (k_constant + rank))

    # Sort merged results by RRF score descending
    sorted_keys = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)[:top_k]

    fused_results = []
    for key in sorted_keys:
        fused_results.append((doc_map[key], rrf_scores[key]))

    return fused_results


import re

def translate_query_to_english_if_needed(question: str) -> str:
    """If the question contains Arabic or non-English script, translate it to an English search query for ChromaDB/BM25 retrieval."""
    if not re.search(r'[\u0600-\u06FF]', question):
        return question

    try:
        from google import genai
        from google.genai import types
        api_key = config.GEMINI_API_KEY
        if not api_key:
            return question

        client = genai.Client(api_key=api_key)
        prompt = f"Translate the following medical question into a clear, concise English search query for medical literature retrieval. Output ONLY the English translation and nothing else:\n\n{question}"
        response = client.models.generate_content(
            model=getattr(config, "GEMINI_MODEL", "gemini-2.5-flash-lite"),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0
            )
        )
        translated = response.text.strip() if response and response.text else question
        logger.info(f"Cross-Lingual Query Translation: '{question}' -> '{translated}'")
        return translated if translated else question
    except Exception as e:
        logger.warning(f"Query translation failed: {e}. Falling back to original question.")
        return question


def retrieve(vectordb, question: str, k: int = None):
    """Executes Hybrid Search combining ChromaDB vector search and BM25 lexical search via RRF.
    Translates Arabic/non-English questions to English for optimal retrieval against English PDF guidelines.
    """
    k = k or config.TOP_K
    fetch_k = k * 3

    search_query = translate_query_to_english_if_needed(question)

    # Dense Vector search
    try:
        vector_results = vectordb.similarity_search_with_relevance_scores(search_query, k=fetch_k)
    except Exception:
        vector_results = [(doc, 0.0) for doc in vectordb.similarity_search(search_query, k=fetch_k)]

    # Lexical BM25 search
    bm25_data = load_bm25_index()
    if bm25_data:
        bm25_results = search_bm25(bm25_data, search_query, k=fetch_k)
        return reciprocal_rank_fusion(vector_results, bm25_results, top_k=k)
    else:
        return vector_results[:k]


def print_results(results):
    """Prints retrieved chunks with RRF scores and citation metadata."""
    if not results:
        logger.info("No matching chunks found in the index.")
        return

    logger.info(f"Top {len(results)} hybrid retrieved chunks:")
    for i, (doc, score) in enumerate(results, 1):
        meta = doc.metadata
        doc_name = meta.get("document_name", "Unknown")
        page = meta.get("page_number", "?")
        section = meta.get("section", "N/A")
        chunk_id = meta.get("chunk_id", "N/A")
        print(f"[{i}] RRF_score={score:.4f}  Document: {doc_name}, Page: {page}, Section: '{section}', ChunkID: {chunk_id}")
        preview = doc.page_content.strip().replace("\n", " ")[:200]
        print(f'    "{preview}..."\n')


def main():
    if len(sys.argv) < 2:
        print('Usage: python query.py "your question here"')
        print('Example: python query.py "What is the target blood pressure for a patient with known cardiovascular disease?"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\n{config.BRAND_HEADER}: Hybrid Retrieval CLI ===\n")
    logger.info(f"Question: {question}")

    vectordb = load_index()
    results = retrieve(vectordb, question)
    print_results(results)


if __name__ == "__main__":
    main()
