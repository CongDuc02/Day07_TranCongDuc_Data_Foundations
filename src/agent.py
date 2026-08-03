from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    # Câu trả lời khi retrieval không tìm được gì: KHÔNG gọi LLM trong trường hợp này,
    # vì hỏi LLM mà không có ngữ cảnh chính là kịch bản dễ sinh ra bịa đặt (hallucination).
    NO_CONTEXT_ANSWER = (
        "Không tìm thấy tài liệu liên quan trong cơ sở tri thức để trả lời câu hỏi này."
    )

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        # Dependency injection: store và llm_fn được truyền từ ngoài vào thay vì tự khởi tạo,
        # nhờ đó test có thể thay bằng mock (llm giả) mà không cần API key thật.
        self.store = store
        self.llm_fn = llm_fn

    def answer(self, question: str, top_k: int = 3) -> str:
        # Bước 1 — RETRIEVE: lấy top_k chunk gần nghĩa nhất với câu hỏi.
        results = self.store.search(question, top_k=top_k)
        if not results:
            return self.NO_CONTEXT_ANSWER

        # Bước 2 — AUGMENT: ghép các chunk thành khối ngữ cảnh cho prompt.
        prompt = self._build_prompt(question, results)

        # Bước 3 — GENERATE: để LLM viết câu trả lời dựa trên ngữ cảnh đã ghép.
        return self.llm_fn(prompt)

    def _build_prompt(self, question: str, results: list[dict]) -> str:
        """
        Ghép ngữ cảnh + câu hỏi thành một prompt duy nhất.

        Mỗi chunk được đánh số và kèm `source` để câu trả lời có thể trích dẫn được
        nguồn — điểm mấu chốt giúp người dùng kiểm chứng thay vì tin mù LLM.
        """
        context_blocks = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata") or {}
            # Ưu tiên 'source', không có thì lùi về doc_id, cuối cùng mới ghi "unknown".
            source = metadata.get("source") or metadata.get("doc_id") or "unknown"
            context_blocks.append(f"[{index}] (nguồn: {source})\n{result['content']}")

        context = "\n\n".join(context_blocks)

        # Chỉ thị "chỉ dùng ngữ cảnh" + "được phép nói không biết" là hai rào chắn
        # chống bịa đặt quan trọng nhất của một prompt RAG.
        return (
            "Bạn là trợ lý trả lời câu hỏi dựa trên tài liệu được cung cấp.\n"
            "Chỉ sử dụng thông tin trong phần NGỮ CẢNH dưới đây. Nếu ngữ cảnh không đủ "
            "thông tin, hãy trả lời rằng bạn không tìm thấy thông tin, tuyệt đối không suy đoán.\n"
            "Khi trả lời, hãy trích dẫn số thứ tự đoạn ngữ cảnh đã dùng, ví dụ [1].\n\n"
            f"NGỮ CẢNH:\n{context}\n\n"
            f"CÂU HỎI: {question}\n\n"
            "TRẢ LỜI:"
        )
