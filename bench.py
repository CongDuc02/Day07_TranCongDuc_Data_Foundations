"""bench.py — chạy 5 benchmark query của nhóm qua MỘT chunker cá nhân.

Mỗi thành viên chỉ sửa DÒNG CHỌN CHUNKER bên dưới (đánh dấu rõ ràng),
mọi thứ khác giữ nguyên để so sánh công bằng giữa các thành viên.

Dùng đúng mã nguồn cá nhân trong gói `src/` (Document, EmbeddingStore,
KnowledgeBaseAgent) — đây là gói được chấm điểm trong REPORT_CANHAN.md.
`ingest.py` chỉ được dùng để parse front-matter của corpus (`load_corpus`);
KHÔNG dùng `EmbeddingStore`/`Chunk` riêng của `ingest.py` vì nó trả về
`list[tuple[Chunk, float]]`, không tương thích với `KnowledgeBaseAgent`
trong `src/agent.py` (kỳ vọng `list[dict]` với key content/metadata/score).

Usage:
    python bench.py
    EMBEDDING_PROVIDER=local python bench.py   # cần cài requirements-local.txt
    EMBEDDING_PROVIDER=openai python bench.py  # cần OPENAI_API_KEY
    HOCVU_DATA_DIR=data/hocvu_university python bench.py

Lưu ý: môi trường lab này KHÔNG cài Ollama, nên `EMBEDDING_PROVIDER=ollama`
chưa được hỗ trợ ở đây (số liệu Ollama thật nằm trong REPORT_NHOM.md, đo trên
máy có Ollama). Không truyền `EMBEDDING_PROVIDER` -> mặc định dùng `mock`.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from ingest import HeadingChunker, load_corpus
from src.agent import KnowledgeBaseAgent
from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path(os.getenv("HOCVU_DATA_DIR", "data/hocvu_university"))

# ============================================================================
# DÒNG DUY NHẤT khác với bạn cùng nhóm — mỗi người chọn 1 dòng, comment 3 dòng còn lại.
# ============================================================================
# chunker = FixedSizeChunker(chunk_size=800, overlap=150)  # Cường
# chunker = SentenceChunker(max_sentences_per_chunk=3)     # Độ
chunker = RecursiveChunker(chunk_size=700)                 # Đức
# chunker = HeadingChunker()                                # Trí (heading, từ ingest.py)
# ============================================================================


# 5 câu hỏi đánh giá của nhóm (phải khớp REPORT_NHOM.md)
QUERIES = [
    {
        "text": "Sinh viên chương trình chuẩn được đăng ký tối đa bao nhiêu tín chỉ trong một học kỳ chính?",
        "metadata_filter": {"audience": "student"},
        "gold_doc_id": "course-registration",
    },
    {
        "text": "Sinh viên được mượn tối đa bao nhiêu cuốn sách và trong bao lâu tại Phòng mượn giáo trình 111?",
        "metadata_filter": None,
        "gold_doc_id": "library-textbook-loan",
    },
    {
        "text": "Nếu sinh viên rút học phần trong 7 tuần đầu học kỳ thì phải đóng bao nhiêu phần trăm học phí?",
        "metadata_filter": None,
        "gold_doc_id": "training-regulation-registration-fees",
    },
    {
        "text": "Thời gian mở đăng ký xét tốt nghiệp đợt 2025.1 diễn ra khi nào?",
        "metadata_filter": None,
        "gold_doc_id": "graduation-registration",
    },
    {
        "text": "Mẫu đơn đề nghị điều chỉnh điểm dành cho đối tượng nào?",
        "metadata_filter": None,
        "gold_doc_id": "academic-forms-directory",
    },
]


def select_embedder():
    """Giống _select_embedder() trong main.py: chọn theo EMBEDDING_PROVIDER
    (mock | local | openai), fallback về mock nếu backend lỗi hoặc thiếu."""
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            print("Local embedder không sẵn sàng; tạm dùng mock.")
            return _mock_embed
    if provider == "openai":
        try:
            return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            print("OpenAI embedder không sẵn sàng; tạm dùng mock.")
            return _mock_embed
    return _mock_embed


def demo_llm(prompt: str) -> str:
    preview = prompt[:300].replace("\n", " ")
    return f"[DEMO LLM] {preview}..."


def build_store(embedding_fn) -> EmbeddingStore:
    """Parse corpus (ingest.load_corpus) -> chunk (chunker đã chọn ở trên) ->
    gắn doc_id + metadata -> nạp vào src.store.EmbeddingStore thật."""
    store = EmbeddingStore(collection_name="bench", embedding_fn=embedding_fn)
    for doc in load_corpus(DATA_DIR):
        pieces = chunker.chunk(doc.content)
        docs = [
            Document(id=f"{doc.doc_id}::{i}", content=piece, metadata={**doc.metadata, "doc_id": doc.doc_id})
            for i, piece in enumerate(pieces)
        ]
        store.add_documents(docs)
    return store


def main() -> None:
    if not DATA_DIR.exists():
        raise SystemExit(f"Không tìm thấy thư mục corpus: {DATA_DIR}")

    embedding_fn = select_embedder()
    backend = getattr(embedding_fn, "_backend_name", embedding_fn.__class__.__name__)

    print(f"Chunker: {chunker.__class__.__name__} — {vars(chunker)}")
    print(f"Backend nhúng: {backend}")
    print(f"Corpus: {DATA_DIR}")

    store = build_store(embedding_fn)
    print(f"Đã nạp {store.get_collection_size()} chunk vào EmbeddingStore")

    agent = KnowledgeBaseAgent(store=store, llm_fn=demo_llm)

    hits = 0
    for i, q in enumerate(QUERIES, start=1):
        print(f"\n{'=' * 78}\nQ{i}: {q['text']}")
        if q["metadata_filter"]:
            print(f"    filter={q['metadata_filter']}")
            results = store.search_with_filter(
                q["text"], metadata_filter=q["metadata_filter"], top_k=3
            )
        else:
            results = store.search(q["text"], top_k=3)

        found_doc_ids = [r["metadata"].get("doc_id") for r in results]
        for rank, r in enumerate(results, start=1):
            marker = " <-- gold" if r["metadata"].get("doc_id") == q["gold_doc_id"] else ""
            preview = r["content"][:100].replace("\n", " ")
            print(f"    [{rank}] score={r['score']:.3f} doc_id={r['metadata'].get('doc_id')}{marker}")
            print(f"        {preview}...")

        hit = q["gold_doc_id"] in found_doc_ids
        hits += hit
        print(f"    -> gold doc_id in top-3: {'HIT' if hit else 'MISS'}")

        answer = agent.answer(q["text"], top_k=3)
        print(f"    Agent answer: {answer[:200]}...")

    print(
        f"\n{'=' * 78}\nSummary: {hits}/5 queries had the gold doc_id in top-3 "
        f"(chunker={chunker.__class__.__name__}, backend={backend})"
    )


if __name__ == "__main__":
    main()