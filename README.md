# 🩺 CareRAG — Production-Grade Clinical Decision Support Engine

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/LLM-Gemini%202.5--Flash-orange.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **CareRAG** is an advanced, production-grade Retrieval-Augmented Generation (RAG) platform tailored for clinical decision support. Built with a **Hybrid RRF Search Engine (ChromaDB + BM25)**, **Cross-Lingual Arabic/English Query Translation**, **Strict Pydantic Schema Guardrails (0% Hallucination)**, and an interactive **Glassmorphic Web Interface**.

---

## 🌟 Key Highlights & Capabilities

- **🔬 Hybrid Retrieval Engine**: Fuses dense vector embeddings (`BAAI/bge-small-en-v1.5`) with lexical search (`BM25`) using **Reciprocal Rank Fusion (RRF)**.
- **🌍 Cross-Lingual Query Translator**: Accepts clinical queries in **Arabic** or **English**, seamlessly translating Arabic search terms to query English medical guidelines while returning grounded Arabic recommendations.
- **🛡️ Verifiable Citations & Safe Refusal**: Guarantees zero hallucinations. If guideline context is missing, CareRAG issues a safe refusal (`confidence: "insufficient"`).
- **🎨 Glassmorphic Web App**: Includes Light/Dark theme switching, responsive collapsible sidebar, interactive citation evidence drawer, and session thread exports (`.md` / `.json`).
- **💾 SQLite Session Store**: Persistent conversation management with pop-up confirmation modals for session deletion.

---

## 🏗️ System Architecture

```
                                  [ PDF Medical Guidelines ]
                                              │
                                   ┌──────────┴──────────┐
                                   ▼                     ▼
                         [ Dense Vector Search ]  [ Lexical BM25 Search ]
                         (BAAI/bge-small-en-v1.5)   (Rank-BM25 Tokenizer)
                                   │                     │
                                   └──────────┬──────────┘
                                              ▼
                                 [ Reciprocal Rank Fusion ]
                                        (RRF k=60)
                                              │
                                              ▼
                                 [ Grounded Gemini Engine ]
                                  (Pydantic Schema JSON)
                                              │
                                              ▼
                                 [ CareRAG Web Interface ]
```

---

## 📁 Repository Map

| File / Folder | Description |
|---|---|
| [`config.py`](config.py) | Central system configuration, model names, paths, and RRF settings |
| [`ingest.py`](ingest.py) | PDF text loader, chunker, vector database indexing & BM25 generator |
| [`query.py`](query.py) | Cross-lingual query translator & Hybrid RRF retrieval engine |
| [`generate.py`](generate.py) | Grounded Gemini generation engine with structured Pydantic schema |
| [`pipeline.py`](pipeline.py) | End-to-end CLI execution engine |
| [`session_manager.py`](session_manager.py) | SQLite session store for history tracking and export generation |
| [`app.py`](app.py) | FastAPI backend serving REST API endpoints and static frontend UI |
| [`eval/`](eval/) | Evaluation suite with 20 ground-truth clinical benchmark test cases |
| [`static/`](static/) | Glassmorphic web user interface assets (HTML, CSS, JavaScript) |
| [`USER_GUIDE.md`](USER_GUIDE.md) | Step-by-step guide for healthcare workers and clinicians |
| [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) | Technical architecture & open-source contributor guide |

---

## ⚡ Quick Start Guide

### 1. Prerequisites & Virtual Environment Setup
Ensure Python 3.10+ is installed on your system.

```bash
# Clone the repository
git clone https://github.com/gheryani102/RAG.git
cd RAG

# Create virtual environment
python -m venv .ragve

# Activate virtual environment
# Windows CMD:
.ragve\Scripts\activate
# macOS/Linux:
source .ragve/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and add your Google Gemini API key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
EMBEDDING_PROVIDER=local
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
```

### 3. Ingest Guidelines & Build Vector Database
Index the clinical guidelines into ChromaDB and generate the BM25 index:
```bash
python ingest.py
```

> [!CAUTION]
> **Hardware & Memory Caution for Low-Spec Devices**:  
> Running `python ingest.py` generates local dense embeddings (`FastEmbed` / `BAAI/bge-small-en-v1.5`) and builds a BM25 index in memory. If you are running on **low-spec or low-budget hardware** (< 4GB RAM or entry-level CPUs) or processing **large medical textbooks** (1,000+ pages), ingestion can cause high CPU load and memory pressure.  
> **Recommended Solutions for Low-Spec Machines**:
> 1. **Cloud Execution (Recommended)**: Host or run your ingestion environment on **[Lightning AI](https://lightning.ai)** (free cloud CPU/GPU Workspaces) to handle heavy document embedding without straining local hardware.
> 2. **Batch Processing**: Split very large PDF documents into smaller sections or ingest files in smaller batches.
> 3. **Increase Chunk Size**: Increase `CHUNK_SIZE` in `config.py` (e.g. from `400` to `600`) to decrease the total number of processed chunks.
> 4. **Close Heavy Apps**: Close memory-intensive background applications prior to executing `python ingest.py`.

### 4. Launch CareRAG Web Server
Run the FastAPI web application server:
```bash
python app.py
```
Open your browser and navigate to **`http://127.0.0.1:8000`**.

---

## 🧪 Running the Benchmark Evaluation

Evaluate CareRAG's faithfulness, answer relevance, citation precision, and refusal behavior against 20 clinical test cases:

```bash
python eval/evaluate.py
```

---

## 📡 REST API Documentation

- `POST /api/query`: Submits a question, retrieves context, and returns a grounded response card.
- `GET /api/sessions`: Returns list of past consultation sessions.
- `GET /api/sessions/{session_id}`: Retrieves full chat history and citations for a specific session.
- `DELETE /api/sessions/{session_id}`: Deletes a consultation session from the database.
- `GET /api/sessions/{session_id}/export?format=json|markdown`: Downloads session thread as JSON or Markdown.

---

## 📜 License & Citation

Distributed under the **MIT License**. Created by **Sa3ayda Geeks** for the AI Clinical Decision Support Competition.
