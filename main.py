"""
main.py – FastAPI application entry point.
Exposes:
  POST /api/upload  – ingest a document
  POST /api/chat    – ask a question
  GET  /            – serve the single-page frontend
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Load .env from the same directory as this file, regardless of cwd
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Guard: make sure the key is present before doing anything
if not os.getenv("GOOGLE_API_KEY"):
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. "
        "Copy backend/.env.example to backend/.env and add your Gemini API key."
    )

from rag_engine import answer_question, ingest_document  # noqa: E402 (after env load)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Academic RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend static files from ../static
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE_MB = 20


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


class UploadResponse(BaseModel):
    filename: str
    chunks: int
    message: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "Academic RAG API is running. Frontend not found."}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """Accept a PDF, DOCX, or TXT file, extract & embed its content."""
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_FILE_SIZE_MB} MB limit.",
        )

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        chunks = ingest_document(content, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    return UploadResponse(
        filename=filename,
        chunks=chunks,
        message=f"Successfully processed '{filename}' into {chunks} chunks.",
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Answer a question grounded in the ingested document corpus."""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        result = answer_question(question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")

    return ChatResponse(answer=result["answer"], sources=result["sources"])


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
