<div align="center">

# 🎓 AcademicRAG — Setup & Run Guide
### Context-Aware Academic Question Answering with Page-Level Citations

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB-FF6F00?style=for-the-badge)](https://www.trychroma.com/)
[![OpenAI](https://img.shields.io/badge/LLM-GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)

**A minimal, production-ready academic RAG application.**  
Upload PDF / DOCX / TXT documents and ask questions — answers are strictly grounded in the document with page-level citations.

[Project Structure](#-project-structure) • [Prerequisites](#-prerequisites) • [Setup & Run](#-setup--run-guide) • [API Reference](#-api-reference) • [How It Works](#-how-it-works)

</div>

---

## 🌟 Key Highlights

- **📄 Multi-Format Ingestion:** Supports `.pdf`, `.docx`, and `.txt` documents (up to **20 MB** per upload).
- **🎯 Zero-Hallucination Guardrails:** The LLM is instructed **never to fabricate** — if context is insufficient, it says so explicitly.
- **📌 Page-Level Citations:** Every response traces answers back to exact source files and page numbers (`lecture.pdf – Page 5`).
- **💾 Persistent Vector Storage:** ChromaDB data persists across server restarts in `backend/chroma_db/`.
- **⚡ Single-Server Architecture:** FastAPI serves both the REST API and the `static/` frontend directly at `/` with no separate frontend build step needed.

---

## 📂 Project Structure

~~~text
.
├── backend/
│   ├── main.py              # FastAPI app (upload + chat endpoints, static serving)
│   ├── rag_engine.py        # Extraction, chunking, ChromaDB, OpenAI generation
│   ├── requirements.txt
│   ├── .env.example         # Copy to .env and fill in your API key
│   └── chroma_db/           # Auto-created — persisted vector store
└── static/
    ├── index.html           # Single-page frontend
    └── app.js
~~~

---

## 📋 Prerequisites

| Tool | Version |
| :--- | :--- |
| **Python** | `3.10` or newer |
| **pip** | any recent |
| **OpenAI API key** | required |

---

## 🚀 Setup & Run Guide

### 1. Clone / Download
~~~bash
git clone https://github.com/TheOne07x/RAG-based-Intelligent-Learning-System.git
cd RAG-based-Intelligent-Learning-System
~~~

### 2. Set Up the Python Environment
~~~bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
~~~

### 3. Configure the OpenAI API Key
~~~bash
cp .env.example .env
~~~
Open `backend/.env` and replace the placeholder:
~~~env
OPENAI_API_KEY=sk-...your-real-key...
~~~

### 4. Run the Backend
~~~bash
# From the backend/ directory, with the venv activated:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
~~~
The server starts at **[http://localhost:8000](http://localhost:8000)**.

### 5. Open the App
Navigate to **[http://localhost:8000](http://localhost:8000)** in your browser.
- The FastAPI server serves the `static/` frontend directly at `/`.
- No separate frontend build step is needed.

---

## 🔌 API Reference

Interactive API docs are available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### `POST /api/upload`
Upload a document for ingestion.
- **Body:** `multipart/form-data` with field `file` (`.pdf`, `.docx`, `.txt`; max `20 MB`)
- **Response:**
~~~json
{ "filename": "lecture.pdf", "chunks": 42, "message": "..." }
~~~

### `POST /api/chat`
Ask a question.
- **Body:** `application/json`
~~~json
{ "question": "What is the main argument of chapter 2?" }
~~~
- **Response:**
~~~json
{
  "answer": "The main argument is ...",
  "sources": ["lecture.pdf – Page 5", "lecture.pdf – Page 6"]
}
~~~

---

## ⚙️ How It Works

### Visual Pipeline
~~~mermaid
flowchart LR
    subgraph Upload ["📥 Upload Flow"]
        A["File (.pdf / .docx / .txt)"] --> B["PyMuPDF / python-docx / txt reader"]
        B --> C["Page-Level Documents"]
        C --> D["RecursiveCharacterTextSplitter<br/>(800 chars / 150 overlap)"]
        D --> E["text-embedding-3-small embeddings"]
        E --> F[("ChromaDB<br/>(persisted to backend/chroma_db/)")]
    end

    subgraph Chat ["💬 Chat Flow"]
        Q["Question"] --> QE["text-embedding-3-small query embedding"]
        QE --> R["ChromaDB top-4 cosine retrieval"]
        F <--> R
        R --> LLM["GPT-4o-mini with strict system prompt"]
        LLM --> OUT["{ answer, sources[] }"]
    end
~~~

### Step-by-Step Execution Flow
~~~text
Upload flow:
  File → PyMuPDF/python-docx/txt reader → page-level Documents
       → RecursiveCharacterTextSplitter (800 chars / 150 overlap)
       → text-embedding-3-small embeddings
       → ChromaDB (persisted to backend/chroma_db/)

Chat flow:
  Question → text-embedding-3-small query embedding
           → ChromaDB top-4 cosine retrieval
           → GPT-4o-mini with strict system prompt
           → { answer, sources[] }
~~~

---

## 🧹 Resetting the Vector Store

To wipe all indexed documents and start fresh:
~~~bash
rm -rf backend/chroma_db/
~~~

---

## 🔑 Environment Variables

| Variable | Description |
| :--- | :--- |
| `OPENAI_API_KEY` | Your OpenAI API key (required) |

---

## 📝 Notes

- ChromaDB data persists across server restarts in `backend/chroma_db/`.
- The LLM is instructed **never to fabricate** — if context is insufficient, it says so explicitly.
- Each uploaded document is chunked and embedded independently; you can upload multiple files before asking questions.

---

<div align="center">
  <sub>Built with FastAPI, ChromaDB & OpenAI • <b>Almas Qureshi</b></sub>
</div>
