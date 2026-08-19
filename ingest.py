"""
CareRAG — Medical Ingestion & Hybrid Indexing Pipeline
------------------------------------------------------
Team: Sa3ayda Geeks
Loads medical PDF guidelines in ./data, parses hierarchical section headings,
splits text into overlapping chunks, embeds chunks into ChromaDB (vector),
and builds a serialized BM25 lexical index (bm25_index.pkl) for Hybrid Retrieval.

Usage:
    python ingest.py
"""
import pickle
import re
import sys
import warnings
from pathlib import Path

from rank_bm25 import BM25Okapi

import config

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from langchain_community.document_loaders import PyPDFLoader

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma


logger = config.setup_logger()


# Regex pattern to detect section headings (e.g., "3.1 Diagnosis", "SECTION 4", "DOSAGE AND ADMINISTRATION")
HEADING_REGEX = re.compile(r'^(?:\d+(?:\.\d+)*\s+[A-Z].*|^[A-Z0-9\s]{4,}:?)$')


def extract_section_headers(page_text: str, current_section: str = "N/A") -> tuple[str, str]:
    """Scans page text lines to detect section headings and returns (cleaned_text, last_section)."""
    lines = page_text.splitlines()
    cleaned_lines = []
    active_section = current_section

    for line in lines:
        stripped = line.strip()
        if stripped and HEADING_REGEX.match(stripped) and len(stripped) < 80:
            active_section = stripped
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines), active_section


def get_embedding_function():
    """Returns the embedding function based on config.EMBEDDING_PROVIDER."""
    if config.EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=config.OPENAI_EMBEDDING_MODEL)
    else:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            from langchain_community.embeddings import FastEmbedEmbeddings
            return FastEmbedEmbeddings(model_name=config.LOCAL_EMBEDDING_MODEL)


def load_pdfs(data_dir: Path):
    """Loads every PDF in data_dir, extracts section titles, and attaches metadata."""
    pdf_files = sorted(data_dir.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {data_dir}/")
        logger.info("Add a guideline PDF there, then re-run this script.")
        sys.exit(1)

    all_docs = []
    for pdf_path in pdf_files:
        logger.info(f"Loading {pdf_path.name} ...")
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        active_section = "N/A"

        for page in pages:
            page.metadata["document_name"] = pdf_path.stem
            page.metadata["page_number"] = page.metadata.get("page", 0) + 1
            
            # Extract section heading
            cleaned_text, active_section = extract_section_headers(page.page_content, active_section)
            page.page_content = cleaned_text
            page.metadata["section"] = active_section

        all_docs.extend(pages)
        logger.info(f"  -> {len(pages)} pages loaded")
    return all_docs


def chunk_documents(documents):
    """Splits documents into overlapping chunks using a recursive splitter."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE * 4,       # ~4 chars per token estimate
        chunk_overlap=config.CHUNK_OVERLAP * 4,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)

    # Attach a stable chunk_id and preserve section metadata
    for i, chunk in enumerate(chunks):
        doc_name = chunk.metadata.get("document_name", "unknown")
        page = chunk.metadata.get("page_number", "?")
        section = chunk.metadata.get("section", "N/A")
        chunk.metadata["section"] = section
        chunk.metadata["chunk_id"] = f"{doc_name}-p{page}-c{i}"

    return chunks


def build_bm25_index(chunks):
    """Builds and serializes a BM25Okapi lexical search index."""
    logger.info(f"Building BM25 lexical index over {len(chunks)} chunks ...")
    corpus = [chunk.page_content for chunk in chunks]
    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)

    chunk_records = []
    for chunk in chunks:
        chunk_records.append({
            "page_content": chunk.page_content,
            "metadata": chunk.metadata
        })

    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.BM25_INDEX_PATH, "wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunk_records}, f)

    logger.info(f"BM25 index saved to {config.BM25_INDEX_PATH}")


def build_index(chunks):
    """Embeds chunks into Chroma collection and builds BM25 index."""
    embedding_fn = get_embedding_function()

    logger.info(f"Embedding {len(chunks)} chunks using '{config.EMBEDDING_PROVIDER}' provider ...")
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_fn,
        collection_name=config.COLLECTION_NAME,
        persist_directory=str(config.CHROMA_DIR),
    )
    logger.info(f"Chroma Vector index saved to {config.CHROMA_DIR}/")
    
    build_bm25_index(chunks)
    return vectordb


def main():
    print(f"\n{config.BRAND_HEADER}: Ingestion & Hybrid Indexing ===\n")
    documents = load_pdfs(config.DATA_DIR)
    chunks = chunk_documents(documents)
    logger.info(f"Created {len(chunks)} chunks from {len(documents)} pages.")
    build_index(chunks)
    logger.info('Next step: run  python query.py "your question here"  to test hybrid retrieval.')


if __name__ == "__main__":
    main()
