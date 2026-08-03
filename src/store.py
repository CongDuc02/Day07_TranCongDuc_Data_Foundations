from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

        try:
            import chromadb  # noqa: F401

            # Client in-memory (EphemeralClient): không ghi ra đĩa, hợp với lab/test.
            # hnsw:space="cosine" -> Chroma trả về distance = 1 - cosine, nhờ đó
            # score quy đổi ở dưới trùng thang đo với nhánh fallback (dot product).
            client = chromadb.EphemeralClient()
            self._collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._use_chroma = True
        except Exception:
            # Chroma chưa cài hoặc lỗi khởi tạo -> im lặng lùi về store in-memory
            # để lab luôn chạy được mà không cần dependency ngoài.
            self._use_chroma = False
            self._collection = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        """
        Chuẩn hóa 1 Document thành 1 record lưu trữ (đã kèm vector nhúng).

        Hai điểm quan trọng:
          - Luôn nhét `doc_id` vào metadata: một tài liệu có thể bị chunk thành
            nhiều record, `doc_id` là sợi dây để delete_document() gom lại và xóa.
          - Sinh id lưu trữ duy nhất `<doc.id>#<n>` để add cùng một doc.id nhiều lần
            không bị ghi đè (Chroma sẽ upsert nếu trùng id).
        """
        metadata = dict(doc.metadata or {})
        metadata.setdefault("doc_id", doc.id)

        record_id = f"{doc.id}#{self._next_index}"
        self._next_index += 1

        return {
            "id": record_id,
            "doc_id": metadata["doc_id"],
            "content": doc.content,
            "metadata": metadata,
            # Nhúng ngay lúc add: chi phí trả một lần, mọi truy vấn sau chỉ còn so vector.
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        """
        Brute-force similarity search trên danh sách record cho trước.

        Tách riêng để search() và search_with_filter() dùng chung: bên gọi chỉ việc
        quyết định tập ứng viên (toàn bộ hay đã lọc metadata).
        """
        if top_k <= 0 or not records:
            return []

        query_embedding = self._embedding_fn(query)

        # Các embedder trong lab đều trả vector đã chuẩn hóa (norm = 1),
        # nên tích vô hướng chính là cosine similarity -> bỏ được phép chia norm.
        scored = [(_dot(query_embedding, record["embedding"]), record) for record in records]

        # Sắp xếp giảm dần theo điểm; key chỉ lấy phần score vì dict không so sánh được.
        scored.sort(key=lambda pair: pair[0], reverse=True)

        return [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": record["metadata"],
                "score": score,
            }
            for score, record in scored[:top_k]
        ]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if not docs:
            return

        records = [self._make_record(doc) for doc in docs]

        # self._store luôn được ghi, kể cả khi có Chroma: nó là "nguồn sự thật" cho
        # các thao tác theo metadata (đếm, lọc, xóa) vốn dễ làm tại chỗ hơn nhiều.
        self._store.extend(records)

        if self._use_chroma and self._collection is not None:
            # Chroma nhận từng list song song theo index: ids[i] <-> documents[i] <-> ...
            self._collection.add(
                ids=[r["id"] for r in records],
                documents=[r["content"] for r in records],
                embeddings=[r["embedding"] for r in records],
                metadatas=[r["metadata"] for r in records],
            )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if not self._store or top_k <= 0:
            return []

        if self._use_chroma and self._collection is not None:
            # Tự nhúng query rồi truyền query_embeddings để dùng ĐÚNG embedding_fn
            # đã dùng lúc add (nếu để Chroma tự nhúng sẽ lệch không gian vector).
            response = self._collection.query(
                query_embeddings=[self._embedding_fn(query)],
                n_results=min(top_k, len(self._store)),
            )
            return self._format_chroma_response(response)

        return self._search_records(query, self._store, top_k)

    def _format_chroma_response(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Đưa kết quả Chroma về cùng schema với nhánh in-memory để bên gọi không phải phân biệt."""
        # Chroma trả list-của-list (một list con cho mỗi query); ta chỉ gửi 1 query.
        ids = (response.get("ids") or [[]])[0]
        documents = (response.get("documents") or [[]])[0]
        metadatas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]

        results: list[dict[str, Any]] = []
        for index, doc_id in enumerate(ids):
            distance = distances[index] if index < len(distances) else 0.0
            results.append({
                "id": doc_id,
                "content": documents[index] if index < len(documents) else "",
                "metadata": metadatas[index] if index < len(metadatas) else {},
                # Với không gian cosine: distance = 1 - similarity -> đảo ngược lại
                # để điểm càng cao càng giống, thống nhất với _search_records.
                "score": 1.0 - distance,
            })
        return results

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        # Pre-filtering (lọc trước, tìm sau) chứ không phải post-filtering: nếu lọc sau
        # khi đã lấy top_k thì có thể trả về ít hơn top_k kết quả hợp lệ dù store còn.
        if metadata_filter:
            candidates = [
                record for record in self._store
                # Chỉ giữ record khớp TẤT CẢ cặp key-value trong bộ lọc (điều kiện AND).
                if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
            ]
        else:
            candidates = self._store

        # Luôn dùng nhánh in-memory: tập ứng viên đã lọc sẵn nên không cần ANN của Chroma.
        return self._search_records(query, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        # Một tài liệu có thể nằm ở nhiều record (do chunking) -> phải xóa theo doc_id,
        # không xóa theo id lưu trữ.
        removed = [record for record in self._store if record["metadata"].get("doc_id") == doc_id]
        if not removed:
            return False

        # Gán lại danh sách đã lọc thay vì xóa trong lúc lặp (tránh nhảy index).
        self._store = [record for record in self._store if record["metadata"].get("doc_id") != doc_id]

        if self._use_chroma and self._collection is not None:
            self._collection.delete(ids=[record["id"] for record in removed])

        return True
