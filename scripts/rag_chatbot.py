"""
RAG chatbot for semiconductor investment analysis.
Retrieves context from FAISS index and generates citation-backed answers.

Run interactively:
    python scripts/rag_chatbot.py

Run with a single question:
    python scripts/rag_chatbot.py --query "What is Intel's revenue trend?"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
INDEX_DIR = ROOT_DIR / "data" / "rag_index"

EMBEDDING_MODEL = "text-embedding-3-large"
CHAT_MODEL = "gpt-4o"
TOP_K = 8

SYSTEM_PROMPT = """\
You are SemiconInvest AI, an expert semiconductor investment analyst \
specializing in Intel (INTC) and Micron (MU).

When answering questions:
- Use ONLY the provided context chunks to answer. If the context is \
insufficient, say so explicitly.
- Cite sources inline using [Source: <source_name>, <section>] format.
- Include the URL when available.
- Compare companies when relevant.
- Be precise with financial figures — quote exact numbers from the data.
- Flag when data may be outdated and suggest verification.
"""


class RAGChatbot:
    def __init__(self):
        import faiss
        from openai import OpenAI

        index_path = INDEX_DIR / "faiss.index"
        meta_path = INDEX_DIR / "chunks_meta.json"

        if not index_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                "FAISS index not found. Run: python scripts/build_index.py"
            )

        self.index = faiss.read_index(str(index_path))
        self.chunks = json.loads(meta_path.read_text(encoding="utf-8"))
        self.client = OpenAI()
        self.history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        print(f"Loaded index with {self.index.ntotal} vectors, "
              f"{len(self.chunks)} chunk records")

    def embed_query(self, query: str) -> np.ndarray:
        resp = self.client.embeddings.create(
            model=EMBEDDING_MODEL, input=[query]
        )
        vec = np.array([resp.data[0].embedding], dtype="float32")
        import faiss
        faiss.normalize_L2(vec)
        return vec

    def retrieve(
        self,
        query: str,
        top_k: int = TOP_K,
        ticker: str | None = None,
        source: str | None = None,
        year: str | None = None,
    ) -> list[dict]:
        """Retrieve top-k chunks, filtered by ticker, source, or fiscal year."""
        fetch_k = top_k * 5 if (ticker or source or year) else top_k
        vec = self.embed_query(query)
        scores, indices = self.index.search(vec, min(fetch_k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            chunk = self.chunks[idx]
            meta = chunk.get("metadata", {})

            if ticker and meta.get("ticker", "").upper() != ticker.upper():
                continue
            if source and meta.get("source", "") != source:
                continue
            if year and str(meta.get("fiscal_year", "")) != str(year):
                continue

            results.append({
                "text": chunk["text"],
                "score": float(score),
                **meta,
            })
            if len(results) >= top_k:
                break

        return results

    def format_context(self, chunks: list[dict]) -> str:
        parts = []
        for i, c in enumerate(chunks, 1):
            score = c.get("score", 0)
            conf = "high" if score >= 0.7 else "medium" if score >= 0.4 else "low"
            fy = c.get("fiscal_year", "")
            header = (
                f"[{i}] Source: {c.get('source', 'N/A')} | "
                f"Company: {c.get('company', 'N/A')} ({c.get('ticker', '')}) | "
                f"Year: {fy or 'N/A'} | "
                f"Section: {c.get('section', 'N/A')} | "
                f"Confidence: {score:.2f} ({conf})"
            )
            url = c.get("url", "")
            if url:
                header += f"\n   URL: {url}"
            parts.append(f"{header}\n{c['text']}")
        return "\n\n---\n\n".join(parts)

    def ask(
        self,
        question: str,
        ticker: str | None = None,
        source: str | None = None,
    ) -> str:
        chunks = self.retrieve(question, ticker=ticker, source=source)

        if not chunks:
            return ("No relevant documents found. Try broadening your question "
                    "or check that the index has been built.")

        context = self.format_context(chunks)
        user_msg = (
            f"Context:\n{context}\n\n---\n\nQuestion: {question}\n\n"
            "Provide a detailed answer with inline source citations."
        )

        self.history.append({"role": "user", "content": user_msg})

        resp = self.client.chat.completions.create(
            model=CHAT_MODEL,
            messages=self.history,
            temperature=0.3,
            max_tokens=2000,
        )
        answer = resp.choices[0].message.content or ""
        self.history.append({"role": "assistant", "content": answer})
        return answer


def parse_filters(raw: str) -> tuple[str | None, str | None]:
    """Parse /ticker:INTC or /source:macrotrends prefixes from input."""
    ticker = source = None
    tokens = raw.split()
    clean = []
    for t in tokens:
        if t.lower().startswith("/ticker:"):
            ticker = t.split(":", 1)[1].upper()
        elif t.lower().startswith("/source:"):
            source = t.split(":", 1)[1]
        else:
            clean.append(t)
    return " ".join(clean), ticker, source


def interactive(bot: RAGChatbot) -> None:
    print("\n╔══════════════════════════════════════════════════╗")
    print("║       SemiconInvest AI — RAG Chatbot            ║")
    print("║  Type your question, or 'quit' to exit.         ║")
    print("║  Filters: /ticker:INTC  /source:macrotrends     ║")
    print("╚══════════════════════════════════════════════════╝\n")

    while True:
        try:
            raw = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not raw or raw.lower() in ("quit", "exit", "q"):
            break

        question, ticker, source = parse_filters(raw)
        if not question:
            continue

        print("\nSearching knowledge base...\n")
        answer = bot.ask(question, ticker=ticker, source=source)
        print(f"AI: {answer}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="SemiconInvest RAG Chatbot")
    parser.add_argument("--query", type=str, default=None,
                        help="Single question (non-interactive mode)")
    parser.add_argument("--ticker", type=str, default=None,
                        help="Filter by ticker (INTC, MU)")
    parser.add_argument("--source", type=str, default=None,
                        help="Filter by source name")
    args = parser.parse_args()

    bot = RAGChatbot()

    if args.query:
        answer = bot.ask(args.query, ticker=args.ticker, source=args.source)
        print(answer)
    else:
        interactive(bot)


if __name__ == "__main__":
    main()
