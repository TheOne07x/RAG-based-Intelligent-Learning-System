"""
rag_engine.py – Text extraction, chunking, ChromaDB ingestion,
               retrieval, and Gemini answer generation.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pymupdf as fitz  # PyMuPDF (pymupdf>=1.24 preferred import)
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "academic_docs"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K = 4

EMBEDDING_MODEL = "models/gemini-embedding-001"
CHAT_MODEL = "gemini-3.8-flash"

SYSTEM_PROMPT = (
    "You are an academic learning assistant. "
    "Answer the user's question using ONLY the provided document context. "
    "If the answer cannot be found in the context, explicitly say: "
    "'The provided document does not contain sufficient information to answer this question.' "
    "Do not fabricate facts.\n\n"
    "Format your response in clean Markdown:\n"
    "- Use ## or ### headings to organise distinct sections.\n"
    "- Use bullet points (- item) or numbered lists for enumerations.\n"
    "- Use **bold** for key terms or important phrases.\n"
    "- Leave a blank line between paragraphs and between a heading and its content.\n"
    "- Keep answers concise and well-structured so they are easy to scan."
)

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------
_embeddings: GoogleGenerativeAIEmbeddings | None = None
_vectorstore: Chroma | None = None
_llm: ChatGoogleGenerativeAI | None = None


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            api_version="v1beta",
        )
    return _embeddings


def _get_vectorstore() -> Chroma:
    global _vectorstore
    if _vectorstore is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=_get_embeddings(),
            persist_directory=str(CHROMA_DIR),
        )
    return _vectorstore


def _get_llm() -> ChatGoogleGenerativeAI:
    global _llm
    if _llm is None:
        _llm = ChatGoogleGenerativeAI(
            model=CHAT_MODEL,
            temperature=0.2,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )
    return _llm


# ---------------------------------------------------------------------------
# Text extraction helpers
# ---------------------------------------------------------------------------

def _extract_pdf(file_bytes: bytes, filename: str) -> list[Document]:
    """Extract text page-by-page from a PDF using PyMuPDF."""
    docs: list[Document] = []
    with fitz.open(stream=file_bytes, filetype="pdf") as pdf:
        for page_num, page in enumerate(pdf, start=1):
            text = page.get_text().strip()
            if text:
                docs.append(
                    Document(
                        page_content=text,
                        metadata={"source": filename, "page": page_num},
                    )
                )
    return docs


def _extract_docx(file_bytes: bytes, filename: str) -> list[Document]:
    """Extract text paragraph-by-paragraph from a Word document."""
    import io
    docx = DocxDocument(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in docx.paragraphs if p.text.strip()]
    full_text = "\n".join(paragraphs)
    return [
        Document(
            page_content=full_text,
            metadata={"source": filename, "page": 1},
        )
    ]


def _extract_txt(file_bytes: bytes, filename: str) -> list[Document]:
    """Extract text from a plain-text file."""
    text = file_bytes.decode("utf-8", errors="replace").strip()
    return [
        Document(
            page_content=text,
            metadata={"source": filename, "page": 1},
        )
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_document(file_bytes: bytes, filename: str) -> int:
    """
    Extract, chunk, embed, and store a document.
    Returns the number of chunks stored.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        raw_docs = _extract_pdf(file_bytes, filename)
    elif ext == ".docx":
        raw_docs = _extract_docx(file_bytes, filename)
    elif ext == ".txt":
        raw_docs = _extract_txt(file_bytes, filename)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(raw_docs)

    if not chunks:
        return 0

    vectorstore = _get_vectorstore()
    vectorstore.add_documents(chunks)

    return len(chunks)


def answer_question(question: str) -> dict[str, Any]:
    """
    Retrieve relevant chunks and generate a grounded answer.

    Returns:
        {
            "answer": str,
            "sources": list[str]   # e.g. ["lecture1.pdf — Page 3"]
        }
    """
    vectorstore = _get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})
    relevant_docs = retriever.invoke(question)

    if not relevant_docs:
        return {
            "answer": (
                "The provided document does not contain sufficient information "
                "to answer this question."
            ),
            "sources": [],
        }

    context_block = "\n\n---\n\n".join(
        f"[Source: {doc.metadata.get('source', 'unknown')}, "
        f"Page: {doc.metadata.get('page', '?')}]\n{doc.page_content}"
        for doc in relevant_docs
    )

    llm = _get_llm()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n{context_block}\n\nQuestion: {question}",
        },
    ]
    response = llm.invoke(messages)
    # Gemini 3.x returns content as a list of typed blocks; flatten to plain text
    raw = response.content
    if isinstance(raw, list):
        answer_text = "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw
        ).strip()
    else:
        answer_text = raw

    # Build deduplicated source list
    seen: set[str] = set()
    sources: list[str] = []
    for doc in relevant_docs:
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        label = f"{src} — Page {page}"
        if label not in seen:
            seen.add(label)
            sources.append(label)

    return {"answer": answer_text, "sources": sources}
