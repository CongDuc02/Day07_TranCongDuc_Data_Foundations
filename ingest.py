"""
ingest.py — pipeline nạp dữ liệu ĐÃ CUNG CẤP cho Lab 7 (Giai đoạn 2/3).

Biến một thư mục file `.md`/`.txt` thành một `EmbeddingStore` tìm kiếm được:

    1. Parse YAML front matter  -> metadata cho từng tài liệu (xem docs/DATA_COLLECTION.md)
    2. Chia mỗi tài liệu thành chunks bằng chiến lược bạn chọn
    3. Gắn `doc_id` + toàn bộ metadata của tài liệu lên TỪNG chunk
    4. Nạp tất cả chunk vào EmbeddingStore

Phần "glue" này được cung cấp sẵn để bạn tập trung vào phần được chấm điểm:
thiết kế/lựa chọn chiến lược chunking, schema metadata, câu hỏi đánh giá và phân
tích truy xuất. Bạn vẫn truyền vào CHUNKER của mình (và có thể thêm metadata).

Front matter (dạng phẳng `key: value`), ví dụ:

    ---
    doc_id: library-renewal-policy
    audience: student
    ---
    <nội dung đã làm sạch>

Chạy `python3 ingest.py` để tự kiểm tra bộ parser front matter (không cần store —
chạy được cả trước khi bạn hoàn thành Giai đoạn 2).
"""
"""Ingest pipeline for the K3 (hocvu-hust) RAG lab.

Provides:
- Front-matter parsing for the corpus .md files.
- A small set of interchangeable chunking strategies.
- ChunkingStrategyComparator to eyeball chunk count / avg length per strategy.
- build_knowledge_base(): parse -> chunk -> attach metadata -> load into EmbeddingStore.
- search_with_filter(): thin wrapper so K3 audience filters (or K4 customer_role)
  are easy to demo in the benchmark.

This is intentionally dependency-light (no external embedding SDK wired in) so it
runs anywhere; swap `EmbeddingStore._embed` for a real provider when EMBEDDING_PROVIDER
is not "local".
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

EMBEDDING_PROVIDER = os.environ.get("EMBEDDING_PROVIDER", "local")
DATA_DIR = Path("data/hocvu-hust")

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

@dataclass
class Document:
    doc_id: str
    metadata: dict[str, str]
    content: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


def parse_markdown_file(path: Path) -> Document:
    """Parse YAML-ish front matter (key: value per line, no nested structures)
    and return the body as content. Raises if front matter is missing."""
    raw = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(raw)
    if not match:
        raise ValueError(f"{path} has no front matter (expected --- ... --- header)")

    front_matter_block, content = match.groups()
    metadata: dict[str, str] = {}
    for line in front_matter_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"')
        # Drop trailing inline comments like `audience: student # comment`
        value = re.split(r"\s+#", value)[0].strip()
        metadata[key] = value

    doc_id = metadata.get("doc_id", path.stem)
    return Document(doc_id=doc_id, metadata=metadata, content=content.strip())


def load_corpus(data_dir: Path = DATA_DIR) -> list[Document]:
    docs = []
    for path in sorted(data_dir.glob("*.md")):
        if path.name.lower() == "benchmark_queries.md":
            continue  # not a source document
        docs.append(parse_markdown_file(path))
    return docs


# ---------------------------------------------------------------------------
# Chunking strategies
# ---------------------------------------------------------------------------

class Chunker:
    name = "base"

    def chunk(self, text: str) -> list[str]:
        raise NotImplementedError


class FixedSizeChunker(Chunker):
    """Fixed character window with overlap."""

    name = "fixed_size"

    def __init__(self, size: int = 800, overlap: int = 150):
        self.size = size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if self.size <= self.overlap:
            raise ValueError("size must be greater than overlap")
        chunks = []
        start = 0
        n = len(text)
        step = self.size - self.overlap
        while start < n:
            end = min(start + self.size, n)
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end == n:
                break
            start += step
        return chunks


class SentenceChunker(Chunker):
    """Group sentences up to a target character budget."""

    name = "by_sentences"

    def __init__(self, target_chars: int = 500):
        self.target_chars = target_chars

    def chunk(self, text: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?…])\s+", text.replace("\n", " "))
        chunks, buf = [], []
        buf_len = 0
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if buf_len + len(sentence) > self.target_chars and buf:
                chunks.append(" ".join(buf))
                buf, buf_len = [], 0
            buf.append(sentence)
            buf_len += len(sentence) + 1
        if buf:
            chunks.append(" ".join(buf))
        return chunks


class RecursiveChunker(Chunker):
    """Split on progressively finer separators (headings > paragraphs >
    sentences > hard cut), recursing into any piece still over budget."""

    name = "recursive"
    SEPARATORS = ["\n## ", "\n### ", "\n\n", "\n", ". "]

    def __init__(self, max_chars: int = 700):
        self.max_chars = max_chars

    def chunk(self, text: str) -> list[str]:
        return self._split(text, list(self.SEPARATORS))

    def _split(self, text: str, separators: list[str]) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.max_chars or not separators:
            return [text]

        sep, rest = separators[0], separators[1:]
        parts = [p for p in text.split(sep) if p.strip()]
        if len(parts) <= 1:
            return self._split(text, rest)

        result = []
        for part in parts:
            if len(part) > self.max_chars:
                result.extend(self._split(part, rest))
            else:
                result.append(part.strip())
        return result


class HeadingChunker(Chunker):
    """Split strictly on Markdown headings (## / ###), keeping each section
    (heading + its body) as one chunk. Good for structured documents like the
    training regulation, where each "Điều" is a self-contained unit."""

    name = "by_heading"
    HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$", re.MULTILINE)

    def chunk(self, text: str) -> list[str]:
        matches = list(self.HEADING_RE.finditer(text))
        if not matches:
            return [text.strip()] if text.strip() else []

        chunks = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section = text[start:end].strip()
            if section:
                chunks.append(section)
        return chunks


STRATEGIES: dict[str, Callable[[], Chunker]] = {
    "fixed_size": lambda: FixedSizeChunker(),
    "by_sentences": lambda: SentenceChunker(),
    "recursive": lambda: RecursiveChunker(),
    "by_heading": lambda: HeadingChunker(),
}


# ---------------------------------------------------------------------------
# Chunking comparator (for the report's Baseline Analysis table)
# ---------------------------------------------------------------------------

class ChunkingStrategyComparator:
    def __init__(self, strategies: dict[str, Callable[[], Chunker]] | None = None):
        self.strategies = strategies or STRATEGIES

    def compare(self, documents: list[Document]) -> list[dict[str, Any]]:
        rows = []
        for doc in documents:
            for name, factory in self.strategies.items():
                chunker = factory()
                chunks = chunker.chunk(doc.content)
                lengths = [len(c) for c in chunks] or [0]
                rows.append({
                    "doc_id": doc.doc_id,
                    "strategy": name,
                    "num_chunks": len(chunks),
                    "avg_len": round(sum(lengths) / len(lengths), 1),
                    "min_len": min(lengths),
                    "max_len": max(lengths),
                })
        return rows

    def print_table(self, documents: list[Document]) -> None:
        rows = self.compare(documents)
        header = f"{'doc_id':35} {'strategy':12} {'chunks':>7} {'avg_len':>8} {'min':>6} {'max':>6}"
        print(header)
        print("-" * len(header))
        for r in rows:
            print(f"{r['doc_id']:35} {r['strategy']:12} {r['num_chunks']:>7} "
                  f"{r['avg_len']:>8} {r['min_len']:>6} {r['max_len']:>6}")


# ---------------------------------------------------------------------------
# Embedding store (local stub; swap out for a real provider if needed)
# ---------------------------------------------------------------------------

class EmbeddingStore:
    """Minimal in-memory vector store.

    EMBEDDING_PROVIDER=local uses a cheap hashed bag-of-words vector so the
    whole pipeline runs offline with zero API calls. This is NOT a real
    embedding model — it's only meant to let retrieval logic (incl. metadata
    filtering) be exercised end-to-end. Swap `_embed` for a real provider for
    meaningful similarity results.
    """

    def __init__(self, dims: int = 256):
        self.dims = dims
        self._chunks: list[Chunk] = []
        self._vectors: list[list[float]] = []

    def _embed(self, text: str) -> list[float]:
        if EMBEDDING_PROVIDER != "local":
            raise NotImplementedError(
                f"EMBEDDING_PROVIDER={EMBEDDING_PROVIDER!r} not wired up in this "
                "lab stub; set EMBEDDING_PROVIDER=local or implement your provider."
            )
        vec = [0.0] * self.dims
        for token in re.findall(r"\w+", text.lower()):
            idx = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % self.dims
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def add(self, chunk: Chunk) -> None:
        self._chunks.append(chunk)
        self._vectors.append(self._embed(chunk.text))

    def _cosine(self, a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def search(self, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        q_vec = self._embed(query)
        scored = [(c, self._cosine(q_vec, v)) for c, v in zip(self._chunks, self._vectors)]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]

    def search_with_filter(
        self, query: str, metadata_filter: dict[str, str], top_k: int = 3
    ) -> list[tuple[Chunk, float]]:
        q_vec = self._embed(query)
        candidates = [
            (c, v) for c, v in zip(self._chunks, self._vectors)
            if all(c.metadata.get(k) == v_ for k, v_ in metadata_filter.items())
        ]
        scored = [(c, self._cosine(q_vec, v)) for c, v in candidates]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]


# ---------------------------------------------------------------------------
# build_knowledge_base
# ---------------------------------------------------------------------------

def build_knowledge_base(
    data_dir: Path = DATA_DIR,
    strategy_name: str = "recursive",
) -> EmbeddingStore:
    """Parse front matter -> chunk -> attach doc_id + metadata -> load into store."""
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown strategy {strategy_name!r}; choose from {list(STRATEGIES)}")

    documents = load_corpus(data_dir)
    chunker = STRATEGIES[strategy_name]()
    store = EmbeddingStore()

    for doc in documents:
        pieces = chunker.chunk(doc.content)
        for i, piece in enumerate(pieces):
            chunk = Chunk(
                chunk_id=f"{doc.doc_id}::{strategy_name}::{i}",
                doc_id=doc.doc_id,
                text=piece,
                metadata=dict(doc.metadata),
            )
            store.add(chunk)

    print(f"Loaded {len(documents)} documents -> {len(store._chunks)} chunks "
          f"(strategy={strategy_name}, embedding_provider={EMBEDDING_PROVIDER})")
    return store


# ---------------------------------------------------------------------------
# Manual smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    docs = load_corpus()
    print(f"Parsed {len(docs)} documents from {DATA_DIR}")

    print("\n=== Baseline chunking comparison ===")
    ChunkingStrategyComparator().print_table(docs)

    print("\n=== build_knowledge_base (recursive) ===")
    store = build_knowledge_base(strategy_name="recursive")

    print("\n=== Sample query with metadata_filter={'audience': 'student'} ===")
    results = store.search_with_filter(
        "Sinh viên chương trình chuẩn được đăng ký tối đa bao nhiêu tín chỉ?",
        metadata_filter={"audience": "student"},
        top_k=3,
    )
    for chunk, score in results:
        print(f"[{score:.3f}] {chunk.doc_id} :: {chunk.text[:120]}...")