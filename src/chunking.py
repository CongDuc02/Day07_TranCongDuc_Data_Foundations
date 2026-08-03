from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    # Tách câu tại vị trí SAU dấu ., ! hoặc ? và theo sau là khoảng trắng
    # (space hoặc xuống dòng). Dùng lookbehind (?<=...) để GIỮ LẠI dấu câu
    # ở cuối câu thay vì nuốt mất nó như re.split thông thường.
    _SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Bước 1: cắt văn bản thành danh sách câu, bỏ khoảng trắng thừa
        # và loại các phần tử rỗng (sinh ra khi text kết thúc bằng dấu câu).
        sentences = [s.strip() for s in self._SENTENCE_BOUNDARY.split(text)]
        sentences = [s for s in sentences if s]
        if not sentences:
            return []

        # Bước 2: gom từng nhóm max_sentences_per_chunk câu thành 1 chunk.
        # Bước nhảy của range chính là kích thước nhóm nên các nhóm không chồng lấn.
        chunks: list[str] = []
        for start in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[start : start + self.max_sentences_per_chunk]
            chunks.append(" ".join(group))
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        # Điểm vào: bắt đầu đệ quy với TOÀN BỘ danh sách separator theo thứ tự ưu tiên.
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        """
        Đệ quy: thử separator ưu tiên cao nhất trước (đoạn văn -> dòng -> câu -> từ),
        chỉ xuống mức thấp hơn khi đoạn hiện tại vẫn còn dài hơn chunk_size.
        Nhờ vậy chunk giữ được ranh giới ngữ nghĩa lớn nhất có thể.
        """
        if not current_text:
            return []

        # Điều kiện dừng 1: đoạn đã đủ ngắn -> nhận luôn, không cắt nữa.
        if len(current_text) <= self.chunk_size:
            return [current_text]

        # Điều kiện dừng 2: hết separator (hoặc gặp separator rỗng "") ->
        # không còn ranh giới tự nhiên nào, buộc phải cắt cứng theo ký tự.
        if not remaining_separators or remaining_separators[0] == "":
            return self._hard_split(current_text)

        separator = remaining_separators[0]
        rest = remaining_separators[1:]

        # Separator này không xuất hiện trong đoạn -> bỏ qua, thử mức ưu tiên kế tiếp.
        if separator not in current_text:
            return self._split(current_text, rest)

        pieces = current_text.split(separator)

        # Gộp tham lam (greedy): dồn các mảnh liên tiếp vào cùng một chunk
        # chừng nào tổng độ dài còn <= chunk_size, để tránh tạo ra quá nhiều chunk vụn.
        chunks: list[str] = []
        buffer = ""
        for piece in pieces:
            if not piece:
                continue

            # Mảnh này tự thân đã quá dài -> xả buffer rồi cắt nhỏ nó bằng separator yếu hơn.
            if len(piece) > self.chunk_size:
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                chunks.extend(self._split(piece, rest))
                continue

            candidate = piece if not buffer else buffer + separator + piece
            if len(candidate) <= self.chunk_size:
                buffer = candidate
            else:
                # Thêm mảnh này sẽ vượt ngưỡng -> chốt buffer hiện tại, mở buffer mới.
                chunks.append(buffer)
                buffer = piece

        if buffer:
            chunks.append(buffer)
        return chunks

    def _hard_split(self, current_text: str) -> list[str]:
        """Cắt cứng theo số ký tự khi không còn separator nào dùng được."""
        return [
            current_text[i : i + self.chunk_size]
            for i in range(0, len(current_text), self.chunk_size)
        ]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    # Tích vô hướng: đo mức "cùng hướng" của hai vector (chưa chuẩn hóa độ dài).
    dot = _dot(vec_a, vec_b)

    # Độ dài (norm) của từng vector = căn bậc hai của tổng bình phương các thành phần.
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))

    # Vector 0 không có hướng -> cosine không xác định, đồng thời tránh chia cho 0.
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    # Chia cho tích hai norm để đưa kết quả về đoạn [-1, 1]:
    # 1 = cùng hướng, 0 = vuông góc (không liên quan), -1 = ngược hướng.
    return dot / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        """
        Chạy 3 chiến lược chunking trên cùng một văn bản và trả về thống kê
        để so sánh: số chunk và độ dài trung bình mỗi chunk.

        Kết quả có dạng:
            {"fixed_size": {"count": int, "avg_length": float, "chunks": [...]}, ...}
        """
        # Overlap 10% chunk_size: đủ để giữ ngữ cảnh ở ranh giới mà không nhân đôi dữ liệu.
        overlap = max(0, chunk_size // 10)

        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size, overlap=overlap),
            "by_sentences": SentenceChunker(max_sentences_per_chunk=3),
            "recursive": RecursiveChunker(chunk_size=chunk_size),
        }

        results: dict = {}
        for name, chunker in strategies.items():
            chunks = chunker.chunk(text)
            # Guard chia cho 0 khi văn bản rỗng -> chunks rỗng.
            avg_length = (sum(len(c) for c in chunks) / len(chunks)) if chunks else 0.0
            results[name] = {
                "count": len(chunks),
                "avg_length": round(avg_length, 2),
                "chunks": chunks,
            }
        return results
