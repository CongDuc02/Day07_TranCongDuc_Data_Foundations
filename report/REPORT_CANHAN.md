# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** [Trần Công Đức]<br>
**Nhóm:** [Cường Độ Đức Trí]<br>
**Ngày:** [03-08-2026]

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**

> Cosine similarity đo góc giữa hai vector embedding chứ không đo độ dài của chúng; giá trị gần 1 nghĩa là hai vector gần như cùng hướng, tức hai đoạn văn bản mang ý nghĩa/ngữ cảnh gần giống nhau dù có thể dùng từ ngữ khác nhau.

**Ví dụ có độ tương tự CAO:**

- Câu A: "Sinh viên cần đăng ký học phần trước khi hết hạn quy định."
- Câu B: "Trước thời hạn quy định, sinh viên phải hoàn tất đăng ký học phần."
- Tại sao tương đồng: Hai câu diễn đạt cùng một hành động (đăng ký học phần đúng hạn) chỉ khác thứ tự từ và cách diễn đạt bề mặt, nên một embedding model tốt sẽ đặt chúng gần nhau trong không gian vector.

**Ví dụ có độ tương tự THẤP:**

- Câu A: "Thư viện trường mở cửa đến 21h các ngày trong tuần."
- Câu B: "Đội bóng đá của trường vừa giành chức vô địch giải sinh viên."
- Tại sao khác: Chủ đề, thực thể và hành động hoàn toàn khác nhau (giờ mở cửa thư viện vs. kết quả thi đấu thể thao) nên vector của hai câu trỏ theo hai hướng gần như không liên quan.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**

> Cosine chỉ quan tâm đến hướng (chuẩn hoá theo độ dài vector) nên hai câu cùng nghĩa nhưng độ dài văn bản khác nhau (khiến magnitude của vector khác nhau) vẫn được so sánh công bằng; Euclidean distance lại bị ảnh hưởng trực tiếp bởi magnitude này nên có thể đánh giá sai hai câu đồng nghĩa là "khác xa nhau" chỉ vì một câu dài hơn câu kia.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**

> _Trình bày phép tính:_
> Bước nhảy (step) giữa 2 chunk liên tiếp = chunk_size − overlap = 500 − 50 = 450.
> Số chunk = ⌈(L − chunk_size) / step⌉ + 1 = ⌈(10000 − 500) / 450⌉ + 1 = ⌈21.11⌉ + 1 = 22 + 1 = **23**.
> Đã kiểm chứng lại bằng code thật: `FixedSizeChunker(chunk_size=500, overlap=50).chunk("a"*10000)` → `len(...) == 23`.
>
> _Đáp án:_ **23 chunks**.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**

> Step giảm còn 500 − 100 = 400 → số chunk = ⌈9500/400⌉ + 1 = 24 + 1 = **25** (kiểm chứng bằng code: 25), tức tăng thêm 2 chunk so với overlap=50. Overlap nhiều hơn giúp giữ được câu/ý nằm vắt ngang ranh giới hai chunk — nếu không có overlap, một câu bị cắt đôi có thể khiến cả hai nửa đều thiếu ngữ cảnh và bị bỏ sót khi truy xuất; đánh đổi là tốn thêm dung lượng lưu trữ và chi phí nhúng do nội dung bị lặp lại.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:

> Dùng regex `(?<=[.!?])\s+` với lookbehind để tách câu tại khoảng trắng ngay sau dấu `.`, `!`, `?` — lookbehind giúp giữ lại dấu câu ở cuối mỗi câu thay vì bị `re.split` nuốt mất như split thông thường. Edge case xử lý: text rỗng/toàn whitespace trả về `[]` ngay từ đầu; sau khi split và `strip()`, loại bỏ mọi phần tử rỗng (phát sinh khi văn bản kết thúc bằng dấu câu, ví dụ chuỗi cuối cùng sau split chỉ là `""`).

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:

> Thuật toán đệ quy thử lần lượt các separator theo thứ tự ưu tiên (đoạn văn `\n\n` → dòng `\n` → câu `. ` → từ ` ` → cắt cứng ký tự), chỉ hạ xuống separator yếu hơn khi đoạn hiện tại vẫn dài hơn `chunk_size`, nhờ đó chunk giữ được ranh giới ngữ nghĩa lớn nhất có thể. Sau khi split bằng 1 separator, các mảnh liền kề được gộp tham lam (greedy merge) miễn tổng độ dài vẫn ≤ `chunk_size`, tránh vỡ thành quá nhiều chunk vụn. Base case: đoạn đã ≤ `chunk_size` (trả nguyên đoạn) hoặc hết separator (rơi vào `_hard_split`, cắt cứng theo số ký tự).

### Lớp EmbeddingStore

**`add_documents` + `search`** — hướng tiếp cận:

> Mỗi `Document` được chuẩn hoá qua `_make_record` thành 1 record gồm id lưu trữ duy nhất (`<doc.id>#<n>`), `doc_id` được nhét vào metadata, và vector nhúng tính ngay lúc add — rồi append vào `self._store` (list in-memory), đây luôn là nguồn dữ liệu chính kể cả khi có ChromaDB (Chroma chỉ nhận bản sao để phục vụ query). `search()` nhúng câu hỏi rồi tính tích vô hướng (dot product) giữa vector query và từng vector đã lưu; vì mọi embedder trong lab đều trả vector đã chuẩn hoá (norm=1) nên dot product chính là cosine similarity — sắp xếp giảm dần theo điểm và lấy `top_k`.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:

> Lọc **trước**, tìm **sau** (pre-filtering): duyệt `self._store`, giữ lại record khớp **tất cả** cặp key-value trong `metadata_filter` (điều kiện AND), rồi mới chạy similarity search trên tập ứng viên đã lọc — nếu lọc sau khi đã cắt `top_k` thì có thể trả về ít kết quả hợp lệ hơn `top_k` dù store còn nhiều record phù hợp. `delete_document` xoá theo `metadata['doc_id']` chứ không theo id lưu trữ, vì một tài liệu có thể bị chunk thành nhiều record; trả về `True` nếu có ít nhất 1 record khớp bị xoá, `False` nếu không tìm thấy `doc_id`.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:

> Theo đúng 3 bước RAG: retrieve top_k chunk từ `store.search(question, top_k)`, build prompt bằng cách đánh số từng chunk và kèm nguồn (`source` hoặc `doc_id`), rồi gọi `llm_fn(prompt)`. Ngữ cảnh được "inject" vào prompt dưới khối `NGỮ CẢNH:` nằm trước câu hỏi, kèm chỉ thị rõ "chỉ dùng thông tin trong ngữ cảnh, không suy đoán" và yêu cầu trích dẫn số thứ tự đoạn đã dùng (ví dụ `[1]`) để câu trả lời kiểm chứng được nguồn. Nếu retrieval không trả về chunk nào, agent trả thẳng câu "không tìm thấy thông tin" mà **không** gọi LLM, tránh kịch bản dễ sinh hallucination nhất (hỏi LLM khi hoàn toàn thiếu ngữ cảnh).

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v

============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.15s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

> Điểm thực tế tính bằng `MockEmbedder` + `compute_similarity` (mock là embedding duy nhất chạy được offline trong môi trường lab này — không cài `sentence-transformers`). Ngưỡng quy đổi cao/thấp dùng trong bảng: điểm > 0.3 → "cao", ngược lại → "thấp".

| Cặp | Câu A                                                  | Câu B                                                               | Dự đoán | Điểm thực tế | Đúng? |
| --- | ------------------------------------------------------ | ------------------------------------------------------------------- | ------- | ------------ | ----- |
| 1   | "Sinh viên đăng ký môn học qua hệ thống trực tuyến."   | "Sinh viên đăng ký tín chỉ qua cổng thông tin đào tạo."             | cao     | 0.0466       | Sai   |
| 2   | "Thư viện mở cửa từ 7h đến 21h các ngày trong tuần."   | "Tôi thích xem phim vào cuối tuần."                                 | thấp    | -0.0862      | Đúng  |
| 3   | "Học phí học kỳ này là 15 triệu đồng."                 | "Học phí học kỳ này là 15 triệu đồng." (giống hệt)                  | cao     | 1.0000       | Đúng  |
| 4   | "Sinh viên được đăng ký tối đa 25 tín chỉ mỗi học kỳ." | "Ký túc xá có 4 khu nhà dành cho sinh viên."                        | thấp    | -0.0278      | Đúng  |
| 5   | "Mượn sách tại thư viện cần có thẻ sinh viên."         | "Để mượn sách ở thư viện, sinh viên phải xuất trình thẻ sinh viên." | cao     | 0.2142       | Sai   |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**

> Bất ngờ nhất là cặp 1 và cặp 5: cả hai đều là câu diễn giải lại (paraphrase) — cùng ý nghĩa, chỉ đổi từ ngữ — nhưng điểm cosine lại thấp gần như hai câu ngẫu nhiên không liên quan (cặp 2, 4). Lý do là `MockEmbedder` băm (hash MD5) trực tiếp chuỗi ký tự thô để sinh vector giả lập, hoàn toàn không "hiểu" ngữ nghĩa, nên chỉ cần đổi vài từ là vector nhảy sang một hướng gần như ngẫu nhiên. Điều này cho thấy cosine similarity chỉ phản ánh đúng ý nghĩa khi vector đến từ một model embedding ngữ nghĩa thật (`LocalEmbedder`/`OpenAIEmbedder`); mock chỉ đáng tin để kiểm thử tính đúng đắn của pipeline (add/search/sắp xếp), không phải để đánh giá chất lượng truy xuất theo ngữ nghĩa.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

Chiến lược cá nhân được nhóm phân công: **`recursive`** (`RecursiveChunker(chunk_size=700)`, xem `REPORT_NHOM.md` §2 "Chiến lược của từng thành viên — Đức"). Số liệu bên dưới lấy từ kết quả đo thật của nhóm (`analyze_failures.py`, `EMBEDDING_PROVIDER=ollama`, `bge-m3:567m`, top_k=3, chấm ở **mức chunk** theo rubric 2/1/0 của `docs/SCORING.md`) — không dùng lại `MockEmbedder` cho bảng này vì mock không mang ngữ nghĩa thật (đã chứng minh ở Mục 4) nên không phản ánh đúng chất lượng truy xuất. Cột "Điểm Score" quy đổi theo rubric của nhóm (2đ = evidence đúng ở rank 1; 1đ = có liên quan nhưng không ở rank 1 hoặc bị lỗi đo) vì nhóm không lưu lại điểm cosine thô cho từng chiến lược/câu hỏi.

| #   | Câu hỏi (Query)                                             | Top-1 Chunk truy xuất được (tóm tắt)                                                                                                                       | Điểm Score   | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt)                                                                                                                                                   |
| --- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Sinh viên chuẩn được đăng ký tối đa bao nhiêu tín chỉ?      | `course-registration.md` — mục "Khối lượng đăng ký": "Chương trình chuẩn: tối đa 24 tín chỉ, tối thiểu 12 tín chỉ (14 TC/8 TC nếu bị cảnh cáo học tập...)" | 2/2 (rank 1) | Có                             | "Tối đa 24 TC (tối thiểu 12 TC, 14 TC/8 TC nếu cảnh cáo học tập/chưa đạt ngoại ngữ) [1]" — chỉ đúng khi có `metadata_filter={"audience":"student"}`, thiếu filter thì mất hạng 1. |
| 2   | Mượn tối đa bao nhiêu sách tại Phòng 111 và bao lâu?        | `library-textbook-loan.md` — "Tối đa 8 cuốn/bạn đọc; hạn mượn 90 ngày, gia hạn 1 lần thêm 30 ngày (tối đa 120 ngày)."                                      | 2/2 (rank 1) | Có                             | "Tối đa 8 cuốn, hạn mượn 90 ngày, gia hạn 1 lần thêm 30 ngày [1]" — câu dễ nhất, cả 4 chiến lược của nhóm đều đúng rank 1.                                                        |
| 3   | Rút học phần trong 7 tuần đầu đóng bao nhiêu % học phí?     | `training-regulation-registration-fees.md` (Điều 9) — "...rút học phần trong 7 tuần đầu học kỳ đóng 50% học phí học phần đó..."                            | 2/2 (rank 1) | Có                             | "50% học phí học phần đó (rút tuần đầu học kỳ 2 có thể miễn; không áp dụng học kỳ hè) [1]".                                                                                       |
| 4   | Đăng ký xét tốt nghiệp 2025.1 mở khi nào, đăng ký ở đâu?    | `graduation-registration.md` — "Từ 03/3/2026 đến hết 15/3/2026; đăng ký từ tài khoản CTT cá nhân, không giới hạn số lần vào đăng ký."                      | 2/2 (rank 1) | Có                             | "Từ 03/3/2026 đến 15/3/2026, đăng ký qua tài khoản CTT cá nhân [1]" — riêng câu này `by_heading` của Trí bị tụt hạng, `recursive` của tôi vẫn giữ rank 1.                         |
| 5   | Mẫu đơn điều chỉnh điểm dành cho ai, nộp qua email thế nào? | `academic-forms-directory.md` — "...là biểu mẫu duy nhất trong danh mục này **dành riêng cho giảng viên**..." (nội dung đúng, ở rank 1 thật sự)            | 1/2 (lỗi đo) | Có (đúng nội dung ở rank 1)    | "Mẫu đơn điều chỉnh điểm dành riêng cho giảng viên; sinh viên nộp loại đơn khác qua email trường cấp kèm ảnh đơn + thẻ SV, tiêu đề [Hạng mục] Mã SV – Họ tên [1]".                |

> Ghi chú Câu 5: script chấm tự động của nhóm so khớp chuỗi cứng `"dành cho giảng viên"`, trong khi chunk rank-1 thật sự viết là `"dành riêng cho giảng viên"` (thêm từ "riêng" chen giữa) nên bị tính nhầm là hạng 2. Đây là **lỗi thiết kế benchmark** (so khớp chuỗi con quá cứng nhắc), không phải lỗi của `RecursiveChunker`/`EmbeddingStore` — xem chi tiết ở `REPORT_NHOM.md` §3 "Failure Case 2".

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5** / 5 (tính theo nội dung thật sự đúng — kể cả Câu 5 vốn đúng ở rank 1, chỉ bị script benchmark của nhóm đo nhầm thành rank 2). Theo đúng rubric chấm điểm của nhóm (2đ/1đ/0đ): **9 / 10 điểm rubric**.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**

> Từ so sánh 4 chiến lược trong `REPORT_NHOM.md`, điều tôi ấn tượng nhất là chiến lược `fixed_size` đơn giản nhất của Cường lại đạt điểm rubric ở mức chunk cao tuyệt đối (10/10) — cao hơn cả `recursive` của tôi (9/10) — vì ranh giới cắt cứng 800 ký tự tình cờ giữ trọn câu trả lời trong cùng 1 chunk trên corpus nhỏ này; bài học là "chunk theo ranh giới ngữ nghĩa tự nhiên" không tự động thắng "cắt cứng đơn giản" khi tài liệu ngắn. Điều thứ hai là phát hiện meta của cả nhóm: 1 trong 2 "failure case" (chính là câu 5 tôi gặp phải) hoá ra là lỗi của **cách nhóm tự chấm điểm** (so khớp chuỗi cứng bỏ sót câu trả lời paraphrase đúng), không phải lỗi retrieval — nhắc tôi rằng số liệu benchmark tự động luôn cần được đọc lại bằng mắt trước khi kết luận.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí                                        | Điểm tự đánh giá |
| ----------------------------------------------- | ---------------- |
| Khởi động (Warm-up)                             | 5/5              |
| Hướng tiếp cận của tôi (My Approach)            | 10/10            |
| Hoàn thiện code (Core Implementation — tests)   | 30/30            |
| Dự đoán độ tương tự (Similarity Predictions)    | 5/5              |
| Kết quả truy xuất của tôi (Competition Results) | 9/10             |
| **Tổng phần cá nhân**                           | **59/60**        |
