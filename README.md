# AcademicRAG — Setup & Run Guide

A minimal, production-ready academic RAG application.  
Upload PDF / DOCX / TXT documents and ask questions — answers are strictly grounded in the document with page-level citations.

---

## Project Structure

```
.
├── backend/
│   ├── main.py            # FastAPI app (upload + chat endpoints, static serving)
│   ├── rag_engine.py      # Extraction, chunking, ChromaDB, OpenAI generation
│   ├── requirements.txt
│   ├── .env.example       # Copy to .env and fill in your API key
│   └── chroma_db/         # Auto-created — persisted vector store
└── static/
    ├── index.html         # Single-page frontend
    └── app.js
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10 or newer |
| pip | any recent |
| OpenAI API key | required |

---

## 1. Clone / Download

```bash
git clone <repo-url>
cd <project-root>
```

---

## 2. Set Up the Python Environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3. Configure the OpenAI API Key

```bash
cp .env.example .env
```

Open `backend/.env` and replace the placeholder:

```env
OPENAI_API_KEY=sk-...your-real-key...
```

---

## 4. Run the Backend

```bash
# From the backend/ directory, with the venv activated:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts at **http://localhost:8000**.

---

## 5. Open the App

Navigate to **http://localhost:8000** in your browser.

- The FastAPI server serves the `static/` frontend directly at `/`.
- No separate frontend build step is needed.

---

## API Reference

### `POST /api/upload`
Upload a document for ingestion.

- **Body:** `multipart/form-data` with field `file` (.pdf, .docx, .txt; max 20 MB)
- **Response:**
  ```json
  { "filename": "lecture.pdf", "chunks": 42, "message": "..." }
  ```

### `POST /api/chat`
Ask a question.

- **Body:** `application/json`
  ```json
  { "question": "What is the main argument of chapter 2?" }
  ```
- **Response:**
  ```json
  {
    "answer": "The main argument is ...",
    "sources": ["lecture.pdf — Page 5", "lecture.pdf — Page 6"]
  }
  ```

Interactive API docs are available at **http://localhost:8000/docs**.

---

## How It Works

```
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
```

---

## Resetting the Vector Store

To wipe all indexed documents and start fresh:

```bash
rm -rf backend/chroma_db/
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key (required) |

---

## Notes

- ChromaDB data persists across server restarts in `backend/chroma_db/`.
- The LLM is instructed **never to fabricate** — if context is insufficient, it says so explicitly.
- Each uploaded document is chunked and embedded independently; you can upload multiple files before asking questions.
