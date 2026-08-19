# 🩺 CareRAG — End-User & Clinician Guide

Welcome to **CareRAG**, an advanced AI-powered Clinical Decision Support Platform designed for healthcare professionals, clinical researchers, and medical students. CareRAG enables you to query clinical guidelines and medical literature with 100% grounded accuracy, zero hallucinations, verifiable citations, and full bilingual (English & Arabic) support.

---

## 🌟 Key Features at a Glance

- **100% Evidence-Grounded Answers**: Every recommendation is generated strictly from verified clinical guideline PDFs.
- **Cross-Lingual Arabic & English Querying**: Ask questions in Arabic or English and receive structured recommendations in your chosen language.
- **Verifiable Citation Chips**: Click on any citation chip (`[WHO_Hypertension... Page 9]`) to open the **Citation Evidence Drawer** and inspect the exact excerpt from the source document.
- **Confidence Badges**: Instantly verify system confidence (`HIGH`, `MEDIUM`, `LOW`, or `INSUFFICIENT context`).
- **Interactive Glassmorphic UI**: Enjoy a modern web interface with Light Mode / Dark Mode switching, smooth layout transitions, and a collapsible sidebar.
- **Exportable Consultation Threads**: Export your clinical consultations to **Markdown (`.md`)** or **JSON (`.json`)** with a single click.
- **Session Management & Deletion**: Store past consultation histories in a persistent sidebar with full control to delete sessions via a confirmation pop-up modal.

---

## 🚀 How to Launch CareRAG

1. Ensure the backend server is running (or open `http://127.0.0.1:8000` in your web browser).
2. The **CareRAG Medical Decision Engine** dashboard will load immediately.

> [!CAUTION]
> **Hardware Caution for Initial Guideline Ingestion**:  
> If you are setting up CareRAG on a new machine, initial document indexing (`python ingest.py`) processes PDF guidelines and generates vector embeddings locally. On low-spec hardware (< 4GB RAM or entry-level CPUs), ingestion may temporarily utilize significant CPU and memory resources.  
> **Recommended Solution**: Consider running or hosting the project on **[Lightning AI](https://lightning.ai)** (free cloud compute workspaces) if your local device has limited RAM or processing power.

---

## 📖 Step-by-Step Usage Guide

### 1. Starting a New Clinical Consultation
- Upon opening CareRAG, a **New Clinical Consultation** thread is active.
- To start fresh at any time, click the **`+ New Consultation`** button in the top left of the sidebar.

### 2. Asking a Clinical Question
- Type your clinical question into the bottom text area (e.g., *"What is the recommended target blood pressure for high-risk cardiovascular patients?"* or *"ما هي مستويات ضغط الدم المستهدفة لدى مرضى السكري؟"*).
- Click **`Send Inquiry`** (or press `Enter`).
- The engine will search uploaded clinical guidelines, translate non-English queries if necessary, retrieve exact evidence passages, and synthesize a grounded response.

### 3. Understanding the Recommendation Card
Each response card presents structured information:
- **Recommendation Header**: Clear clinical guidance synthesized strictly from guidelines.
- **Confidence Badge**:
  - 🟢 **HIGH / MEDIUM / LOW**: Indicates sufficient grounded evidence was found.
  - 🔴 **INSUFFICIENT**: Displayed when the uploaded guidelines do not contain enough evidence to answer safely. CareRAG will refuse to guess.
- **Supporting Evidence Excerpt**: Direct excerpt quoted from the source text.
- **Citation Chips**: Clickable buttons specifying document title, section, and page number.

### 4. Inspecting Citation Evidence
- Click on any **Citation Chip** attached to an answer card.
- The **Citation Evidence Details Drawer** will slide in from the right edge.
- You can inspect:
  - **Source Document Name**
  - **Exact Page Number**
  - **Document Section Header**
  - **Full Grounded Evidence Excerpt**

### 5. Switching Languages (Arabic / English)
- Click the **`🌐 العربية` / `🌐 English`** button in the top header.
- The interface immediately toggles reading direction (RTL for Arabic, LTR for English) and translates all system labels.

### 6. Toggling Light Mode & Dark Mode
- Click the **`☀️ Light` / `🌙 Dark`** theme switcher button in the top header.
- The button displays the target theme you will switch to upon clicking.

### 7. Exporting Consultation History
- Click **`📄 Export MD`** in the top bar to download a formatted Markdown document of the consultation.
- Click **`📊 Export JSON`** to download a structured JSON file containing all message turns and citation metadata.

### 8. Managing & Deleting Past Consultations
- All past consultations are listed chronologically in the **Past Consultations** sidebar.
- Click any session to load its full history into the main workspace.
- To delete a consultation, click the **trash icon (`🗑️`)** on the session card.
- A confirmation pop-up modal will appear (**"Delete Consultation?"** / **"حذف الاستشارة؟"**). Click **`Delete`** to permanently erase the thread and associated data.

---

## ❓ Frequently Asked Questions (FAQ)

- **Q: Will CareRAG make up answers if the medical text doesn't cover my question?**  
  *A: No. CareRAG enforces strict guardrails. If context is insufficient, it displays an INSUFFICIENT confidence badge and refuses to guess.*

- **Q: Can I ask questions in Arabic?**  
  *A: Yes! CareRAG uses cross-lingual retrieval. It automatically translates your Arabic question to match English medical PDFs, retrieves the exact evidence, and responds in fluent medical Arabic.*

- **Q: Where is my consultation history saved?**  
  *A: All sessions are saved locally in a secure SQLite database (`sessions/care_rag_sessions.db`).*
