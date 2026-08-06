"""
Build a FAISS vector index from crawled markdown and 10-K HTML files.
Chunks documents, embeds with text-embedding-3-large, stores with metadata.

Run:
    python scripts/build_index.py
    python scripts/build_index.py --rebuild
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
CRAWLED_DIR = ROOT_DIR / "data" / "crawled"
TENK_DIR = ROOT_DIR / "data" / "10k"
INDEX_DIR = ROOT_DIR / "data" / "rag_index"

CHUNK_MIN_TOKENS = 400
CHUNK_MAX_TOKENS = 800
CHUNK_OVERLAP_TOKENS = 100
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 3072
EMBEDDING_TOKEN_LIMIT = 8000  # API max is 8192; leave headroom
BATCH_SIZE = 64


# ── Tokenizer ─────────────────────────────────────────────────
def get_encoder():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, enc) -> int:
    return len(enc.encode(text))


# ── Document loaders ──────────────────────────────────────────
def load_crawled_docs() -> list[dict]:
    """Load markdown files from data/crawled/ with their metadata."""
    docs = []
    if not CRAWLED_DIR.exists():
        return docs
    for md_path in sorted(CRAWLED_DIR.glob("*.md")):
        meta_path = md_path.with_suffix(".meta.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            meta = {
                "source": "crawled",
                "company": "Unknown",
                "ticker": "N/A",
                "doc_type": "web_page",
                "section": "general",
                "url": "",
            }
        text = md_path.read_text(encoding="utf-8").strip()
        if text:
            docs.append({"text": text, "metadata": meta})
    return docs


def html_to_text(html: str) -> str:
    """Strip HTML tags for plain-text extraction."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "head"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def load_10k_docs() -> list[dict]:
    """Load 10-K HTML filings from data/10k/."""
    docs = []
    if not TENK_DIR.exists():
        return docs
    for html_path in sorted(TENK_DIR.glob("*.html")):
        name = html_path.stem  # e.g. Intel_10K_2024_2024-01-26
        parts = name.split("_")
        company = parts[0] if parts else "Unknown"
        ticker = {"Intel": "INTC", "Micron": "MU"}.get(company, "N/A")
        year = parts[2] if len(parts) > 2 else "N/A"
        date = parts[3] if len(parts) > 3 else "N/A"

        raw_html = html_path.read_text(encoding="utf-8", errors="replace")
        text = html_to_text(raw_html)
        if not text.strip():
            continue

        meta = {
            "source": "sec_edgar",
            "company": company,
            "ticker": ticker,
            "doc_type": "10-K",
            "section": "annual_report",
            "url": f"https://www.sec.gov/ (CIK lookup)",
            "date": date,
            "fiscal_year": year,
        }
        docs.append({"text": text, "metadata": meta})
    return docs


# ── Chunking ──────────────────────────────────────────────────
def chunk_text(text: str, metadata: dict, enc) -> list[dict]:
    """Split text into overlapping chunks of CHUNK_MIN..CHUNK_MAX tokens."""
    paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    current_lines: list[str] = []
    current_tokens = 0

    def flush():
        nonlocal current_lines, current_tokens
        if not current_lines:
            return
        chunk_text = "\n\n".join(current_lines).strip()
        if count_tokens(chunk_text, enc) >= 50:  # skip tiny fragments
            chunks.append({
                "text": chunk_text,
                "metadata": {**metadata, "chunk_index": len(chunks)},
            })
        current_lines = []
        current_tokens = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        para_tokens = count_tokens(para, enc)

        # If single paragraph exceeds max, split by sentences
        if para_tokens > CHUNK_MAX_TOKENS:
            flush()
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                st = count_tokens(sent, enc)
                if current_tokens + st > CHUNK_MAX_TOKENS:
                    flush()
                current_lines.append(sent)
                current_tokens += st
            flush()
            continue

        if current_tokens + para_tokens > CHUNK_MAX_TOKENS:
            flush()
            # Keep overlap: reuse the last paragraph
            if current_lines:
                overlap_text = current_lines[-1]
                if count_tokens(overlap_text, enc) <= CHUNK_OVERLAP_TOKENS:
                    current_lines = [overlap_text]
                    current_tokens = count_tokens(overlap_text, enc)
                else:
                    current_lines = []
                    current_tokens = 0

        current_lines.append(para)
        current_tokens += para_tokens

    flush()
    return chunks


# ── Embedding ─────────────────────────────────────────────────
def truncate_to_token_limit(text: str, enc, limit: int = EMBEDDING_TOKEN_LIMIT) -> str:
    """Truncate text to fit within the embedding model's token limit."""
    tokens = enc.encode(text)
    if len(tokens) <= limit:
        return text
    return enc.decode(tokens[:limit])


def embed_texts(texts: list[str], enc) -> np.ndarray:
    """Embed a list of texts using OpenAI text-embedding-3-large."""
    from openai import OpenAI
    client = OpenAI()
    all_embeddings = []

    # Truncate any texts exceeding API limit
    safe_texts = [truncate_to_token_limit(t, enc) for t in texts]

    for i in range(0, len(safe_texts), BATCH_SIZE):
        batch = safe_texts[i : i + BATCH_SIZE]
        print(f"  Embedding batch {i // BATCH_SIZE + 1} "
              f"({len(batch)} texts, {i + len(batch)}/{len(safe_texts)})")
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for item in resp.data:
            all_embeddings.append(item.embedding)

    return np.array(all_embeddings, dtype="float32")


# ── FAISS index ───────────────────────────────────────────────
def build_faiss_index(embeddings: np.ndarray):
    """Build an L2-normalized FAISS index with inner-product search."""
    import faiss

    dim = embeddings.shape[1]
    # Normalize for cosine similarity via inner product
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS RAG index")
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild index even if it exists")
    args = parser.parse_args()

    index_path = INDEX_DIR / "faiss.index"
    meta_path = INDEX_DIR / "chunks_meta.json"

    if index_path.exists() and not args.rebuild:
        print(f"Index already exists at {index_path}")
        print("Use --rebuild to recreate it.")
        return

    enc = get_encoder()

    # Load all documents
    print("Loading crawled documents...")
    crawled = load_crawled_docs()
    print(f"  {len(crawled)} crawled documents")

    print("Loading 10-K filings...")
    tenk = load_10k_docs()
    print(f"  {len(tenk)} 10-K documents")

    all_docs = crawled + tenk
    if not all_docs:
        print("No documents found. Run crawl_sources.py and/or download_10k.py first.")
        return

    # Chunk
    print("Chunking documents...")
    all_chunks: list[dict] = []
    for doc in all_docs:
        chunks = chunk_text(doc["text"], doc["metadata"], enc)
        all_chunks.extend(chunks)
    print(f"  {len(all_chunks)} chunks created")

    if not all_chunks:
        print("No chunks produced — check document content.")
        return

    # Embed
    print(f"Generating embeddings with {EMBEDDING_MODEL}...")
    texts = [c["text"] for c in all_chunks]
    embeddings = embed_texts(texts, enc)
    print(f"  Embedding matrix: {embeddings.shape}")

    # Build index
    print("Building FAISS index...")
    import faiss
    index = build_faiss_index(embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))

    # Save metadata (text + metadata per chunk)
    meta_records = []
    for chunk in all_chunks:
        meta_records.append({
            "text": chunk["text"][:3000],  # cap stored text for file size
            "metadata": chunk["metadata"],
        })
    meta_path.write_text(
        json.dumps(meta_records, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )

    print(f"\nIndex saved: {index_path} ({index.ntotal} vectors, dim={EMBEDDING_DIM})")
    print(f"Metadata saved: {meta_path}")
    print("Done.")


if __name__ == "__main__":
    main()
