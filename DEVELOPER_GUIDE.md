# 🛠️ CareRAG — Open Source Developer & Architecture Guide

Welcome to the **CareRAG Developer Guide**! This document provides an in-depth technical overview of CareRAG's codebase, module architecture, hybrid retrieval mechanics, evaluation framework, and extension pipelines for developers and open-source contributors.

---

## 🏗️ Architecture Overview

```
                      +---------------------------------------+
                      |   Clinical Guidelines (PDFs / data)   |
                      +---------------------------------------+
                                          |
                                    [ Ingestion ]
                                          |
                      +-------------------+-------------------+
                      |                                       |
           [ Dense Embedding ]                       [ BM25 Lexical ]
        BAAI/bge-small-en-v1.5                      Tokenizer & TF-IDF
                      |                                       |
            [ ChromaDB VectorStore ]                 [ BM25 Index Pickle ]
                      |                                       |
                      +-------------------+-------------------+
                                          |
                                   [ User Query ]
                                          |
                           [ Cross-Lingual Translation ]
                           (Arabic -> English Search)
                                          |
                            [ Hybrid RRF Search Engine ]
                              Reciprocal Rank Fusion
                                          |
                              [ Top-K Context Chunks ]
                                          |
                           [ Grounded Gemini Engine ]
                             JSON Schema Guardrails
                                          |
                          +---------------+---------------+
                          |                               |
                 [ Structured Output ]         [ SQLite Persistence ]
```

---

## 📁 Repository Structure & Module Breakdown

```
RAG/
├── config.py                 # Central configuration (paths, RRF k, models, logging)
├── ingest.py                 # PDF loader, character splitter, local embedding, ChromaDB & BM25 index generator
├── query.py                  # Cross-lingual query translator & Hybrid RRF retriever module
├── generate.py               # Grounded Gemini generation engine with Pydantic response schema
├── pipeline.py               # End-to-end CLI RAG execution engine
├── session_manager.py        # SQLite persistence layer for session & chat history management
├── app.py                    # FastAPI web server & REST API endpoints
├── schema/
│   └── response_schema.json  # Draft-07 JSON Schema for grounded clinical responses
├── eval/
│   ├── eval_dataset.json     # Ground truth benchmark dataset (20 test cases)
│   └── evaluate.py           # Automated evaluation bench (Faithfulness, Relevance, Citation Precision)
└── static/
    ├── index.html            # Web UI markup (Header, Viewport, Drawer, Modals)
    ├── style.css             # Glassmorphic styling system & responsive animations
    └── app.js                # Frontend client app, i18n localization & state management
```

---

## 🧠 Core Technical Components

### 1. Ingestion Engine (`ingest.py`)
- **PDF Extraction**: Uses `langchain_community.document_loaders.PyPDFLoader` to extract page-by-page text with metadata (`document_name`, `page_number`).
- **Text Chunking**: Uses `RecursiveCharacterTextSplitter` with `CHUNK_SIZE=400` tokens (~1600 characters) and `CHUNK_OVERLAP=50` tokens.
- **Local Embedding**: Computes dense vector embeddings using `FastEmbed` with `BAAI/bge-small-en-v1.5` (384 dimensions, zero API cost).
- **BM25 Lexical Indexing**: Tokenizes document content, computes inverse document frequency scores, and serializes the index to `chroma_db/bm25_index.pkl` via `rank_bm25`.

> [!CAUTION]
> **Hardware Resource & Memory Warning**:  
> Ingesting large medical PDFs creates hundreds of text chunks and calculates high-dimensional dense embeddings locally. On low-budget or resource-constrained devices (< 4GB RAM or entry-level CPUs), ingestion can lead to high CPU utilization and memory spikes.  
> **Recommended Workaround**: Developers with low-spec hardware should host or run the ingestion pipeline on **[Lightning AI](https://lightning.ai)** cloud workspaces (free cloud CPU/GPU environments) or split massive textbooks before running `python ingest.py`.

### 2. Cross-Lingual Retrieval Engine (`query.py`)
- **Query Translation Layer**: Detects non-English (Arabic) Unicode ranges (`[\u0600-\u06FF]`) and uses Gemini (`gemini-2.5-flash-lite`) to translate the question into a dense English medical search query.
- **Hybrid Search**: Performs parallel vector search in ChromaDB and lexical search in `rank_bm25`.
- **Reciprocal Rank Fusion (RRF)**: Merges rank positions using the standard RRF formula:
  $$\text{RRF\_Score}(d) = \sum_{m \in M} \frac{1}{k + \text{rank}_m(d)}$$
  where $k = 60$.

### 3. Grounded Generation Engine (`generate.py`)
- **Strict Guardrails**: Enforces zero outside knowledge usage. If context is missing, output `confidence: "insufficient"`.
- **Structured Schema**: Uses Pydantic (`GroundedResponseModel`) with `response_mime_type="application/json"`:
  ```python
  class CitationModel(BaseModel):
      document_name: str
      page_number: int
      section: str
      chunk_id: str

  class GroundedResponseModel(BaseModel):
      recommendation: str
      evidence: str
      citations: List[CitationModel]
      confidence: Literal["high", "medium", "low", "insufficient"]
  ```

### 4. Session Persistence & REST API (`session_manager.py` & `app.py`)
- **SQLite Database**: Stores sessions and messages in `sessions/care_rag_sessions.db`.
- **API Endpoints**:
  - `GET /api/sessions`: List all past consultations.
  - `GET /api/sessions/{id}`: Fetch consultation thread with citations.
  - `POST /api/query`: Execute end-to-end RAG inquiry.
  - `DELETE /api/sessions/{id}`: Permanently erase consultation thread.
  - `GET /api/sessions/{id}/export?format=json|markdown`: Download consultation exports.

---

## ⚡ Automated Benchmark Suite (`eval/evaluate.py`)

Run the automated evaluation benchmark suite to measure RAG pipeline accuracy across 20 clinical test cases:

```bash
python eval/evaluate.py
```

### Metrics Evaluated:
1. **Faithfulness**: Verifies whether the recommendation contains zero hallucinated facts outside the retrieved context.
2. **Answer Relevance**: Measures semantic alignment between the question and output.
3. **Citation Precision**: Ensures cited document names and page numbers match the actual source chunks.
4. **Refusal Precision**: Confirms the model correctly refuses out-of-scope questions (`confidence: "insufficient"`).

---

## 🛠️ Local Development Setup

1. **Clone repository**:
   ```bash
   git clone https://github.com/gheryani102/RAG.git
   cd RAG
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv .ragve
   source .ragve/bin/activate  # On Windows: .ragve\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Add your GEMINI_API_KEY in .env
   ```

4. **Ingest Guidelines & Build Database**:
   ```bash
   python ingest.py
   ```

5. **Start FastAPI Development Server**:
   ```bash
   python app.py
   ```
   Open `http://127.0.0.1:8000` in your web browser.

---

## 🤝 Contributing Guidelines

We welcome community pull requests!
1. Fork the repo and create a feature branch (`git checkout -b feature/amazing-feature`).
2. Run `python eval/evaluate.py` to ensure zero regression in evaluation metrics.
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request!
