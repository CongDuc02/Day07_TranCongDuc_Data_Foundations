# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** E2
**Thành viên:**

- Xuân Thế Độ - 2A202601847
- Nguyễn Công Trí - 2A202601715
- Trần Công Đức - 2A202601423
- Lê Kiên Cường - 2A202601427<br>
  **Ngày:** 03/08/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Phạm vi bộ tài liệu (Scope)

**Chủ đề (cố định theo lớp K3):** Dịch vụ / quy định đại học (đăng ký môn, học phí, học bổng, thư viện, ký túc xá…).

**Phạm vi cụ thể nhóm tập trung:**

> Học vụ tại Đại học Bách khoa Hà Nội: đăng ký học phần, tốt nghiệp, học phí/cảnh báo học tập, thư viện, và quy trình liên hệ/biểu mẫu hành chính của Ban Đào tạo.

### Danh sách tài liệu (Data Inventory)

| #   | Tên tài liệu                                                                   | Nguồn (Source URL)                                                                                                                | Ngày lấy / Phiên bản    | Số ký tự | Metadata đã gán                                                                                                                                |
| --- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Kế hoạch đăng ký lớp học kỳ 1 năm học 2025-2026 (20251)                        | https://ctt.hust.edu.vn/DisplayWeb/DisplayKehoach?kehoach=25223                                                                   | 2026-08-03 / 2025-07-30 | ~3400    | doc_id, title, source_url, retrieved_at, document_version, audience: student, department: ban-dao-tao, category: course-registration, language |
| 2   | Thông báo mở đăng ký tốt nghiệp đợt 2025.1                                     | https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=46601                                                                   | 2026-08-03 / 2025.1     | ~2400    | audience: student, department: ban-dao-tao, category: graduation                                                                               |
| 3   | Quy trình mượn trả sách tại Phòng mượn giáo trình 111                          | https://library.hust.edu.vn/vi/node/483                                                                                           | 2026-08-03 / not-stated | ~2600    | audience: student, department: library, category: borrowing-policy                                                                             |
| 4   | Quy chế đào tạo 2025 — Đăng ký học tập, học phí, cảnh báo học tập (trích)      | https://ctt.hust.edu.vn/Upload/Nguy%E1%BB%85n%20Qu%E1%BB%91c%20%C4%90%E1%BA%A1t/files/DTDH_QDQC/Hoctap/QCDT_2025_5445_QD-DHBK.pdf | 2026-08-03 / QCDT_2025  | ~4000    | audience: all, department: ban-dao-tao, category: training-regulation                                                                          |
| 5   | Hướng dẫn gửi câu hỏi/thắc mắc tới Ban Đào tạo (học tập, học phí)              | https://sv-ctt.hust.edu.vn/#/so-tay-sv/69/ban-dao-tao-huong-dan-thu-tuc-bieu-mau-thac-mac-ve-hoc-tap-hoc-phi                      | 2026-08-03 / not-stated | ~2900    | audience: staff, department: ban-dao-tao, category: administrative-procedure                                                                   |
| 6   | Biểu mẫu về học tập (đơn điều chỉnh điểm, đăng ký lớp, rút học phần, hoãn thi) | https://ctt.hust.edu.vn/DisplayWeb/DisplayBaiViet?baiviet=77                                                                      | 2026-08-03 / not-stated | ~2600    | audience: faculty, department: ban-dao-tao, category: forms                                                                                    |

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**

- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata    | Kiểu          | Ví dụ giá trị                                                                                                       | Tại sao hữu ích cho truy xuất (retrieval)?                                                                                                  |
| ------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `audience`         | string (enum) | `student`, `faculty`, `staff`, `all`                                                                                | Lọc theo đối tượng đọc — tránh trả nhầm nội dung dành cho giảng viên/cán bộ khi sinh viên hỏi, và ngược lại (dùng trong `metadata_filter`). |
| `department`       | string        | `ban-dao-tao`, `library`                                                                                            | Thu hẹp phạm vi truy xuất theo đơn vị phụ trách khi câu hỏi nêu rõ phòng ban (VD: "thư viện nói gì về...").                                 |
| `category`         | string        | `course-registration`, `graduation`, `borrowing-policy`, `training-regulation`, `administrative-procedure`, `forms` | Phân loại chủ đề con, hỗ trợ định tuyến câu hỏi hoặc lọc kết hợp với `audience` khi corpus mở rộng.                                         |
| `document_version` | string        | `2025-07-30`, `QCDT_2025`, `not-stated`                                                                             | Giúp agent/người dùng biết thông tin có còn hiệu lực không (đặc biệt quan trọng với các mốc thời gian đăng ký thay đổi theo từng kỳ).       |
| `source_url`       | string (URL)  | `https://ctt.hust.edu.vn/...`                                                                                       | Cho phép trích dẫn nguồn và người dùng tự kiểm chứng thông tin gốc.                                                                         |

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Số lượng chunk sinh ra trên toàn bộ corpus (`data/hocvu-university/`, 6 tài liệu):

| Chiến lược                                    | Tham số                                                 | Tổng số chunk (6 tài liệu) | Ghi chú                                                                                                                   |
| --------------------------------------------- | ------------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `fixed_size`                                  | `chunk_size=800, overlap=150`                           | 20                         | Cắt cứng theo ký tự; đơn giản, dự đoán được, nhưng có thể chia đôi câu/mục.                                               |
| `by_sentences`                                | `max_sentences_per_chunk=3`                             | 39                         | Không bao giờ cắt giữa câu; nhiều chunk nhỏ hơn hẳn do gộp tối đa 3 câu/chunk.                                            |
| `recursive`                                   | `chunk_size=700`, separator `['\n\n','\n','. ',' ','']` | 24                         | Ưu tiên tách theo đoạn/dòng trước khi cắt câu.                                                                            |
| `by_heading` (custom `HeadingSectionChunker`) | `max_chars=700`                                         | 33                         | Tách theo heading Markdown trước, section dài quá ngưỡng mới hạ xuống recursive và **gắn lại tiêu đề** vào từng mảnh con. |

**Nhận xét baseline:** Số lượng chunk chênh lệch tới ~2x giữa các chiến lược
(20 với `fixed_size` so với 39 với `by_sentences`), phản ánh cách mỗi thuật toán
định nghĩa "1 đơn vị ngữ nghĩa" khác nhau.

### Chiến lược của từng thành viên

**Thành viên 1 — Cường — `fixed_size`**

- **Mô tả & lý do chọn:** Chọn `FixedSizeChunker(chunk_size=800, overlap=150)` (từ `src/chunking.py`) làm baseline vì đây là chiến lược đơn giản nhất, không phụ thuộc cấu trúc tài liệu — dùng để đối chiếu xem các chiến lược "thông minh" hơn có thực sự cải thiện retrieval hay không.
- **Code:**

```python
from src.chunking import FixedSizeChunker
chunker = FixedSizeChunker(chunk_size=800, overlap=150)
```

**Thành viên 2 — Độ — `by_sentences`**

- **Mô tả & lý do chọn:** Chọn `SentenceChunker(max_sentences_per_chunk=3)` vì các câu trong tài liệu học vụ thường chứa trọn 1 điều kiện/quy định, nên gộp theo câu tránh cắt đứt quy định giữa chừng.
- **Code:**

```python
from src.chunking import SentenceChunker
chunker = SentenceChunker(max_sentences_per_chunk=3)
```

**Thành viên 3 — Đức — `recursive`**

- **Mô tả & lý do chọn:** Chọn `RecursiveChunker(chunk_size=700)` vì kỳ vọng đây là chiến lược cân bằng — ưu tiên ranh giới tự nhiên (đoạn/dòng) trước khi cắt câu.
- **Code:**

```python
from src.chunking import RecursiveChunker
chunker = RecursiveChunker(chunk_size=700)
```

**Thành viên 4 — Trí — `by_heading` (custom)**

- **Mô tả & lý do chọn:** Viết `HeadingSectionChunker(max_chars=700)` (trong `ingest.py`) vì toàn bộ 6 tài liệu được viết theo cấu trúc Markdown có heading rõ ràng — tách theo heading khớp đúng ý định phân chia mục của người viết tài liệu. Section nào dài quá `max_chars` mới hạ xuống `RecursiveChunker`, và tiêu đề được gắn lại vào từng mảnh con để không mất ngữ cảnh.
- **Code:**

```python
from ingest import HeadingSectionChunker
chunker = HeadingSectionChunker(max_chars=700)
```

> Phân công: Cường (`fixed_size`), Độ (`by_sentences`), Đức (`recursive`), Trí (`by_heading`).

### So Sánh Giữa Các Thành Viên

Kết quả **chấm ở mức chunk** (không chỉ doc_id) từ `analyze_failures.py` với
`EMBEDDING_PROVIDER=ollama` (`bge-m3:567m`), top-k=3, dùng rubric 2/1/0 chính
thức của `docs/SCORING.md` (2đ: evidence ở rank 1; 1đ: evidence có trong top-3
nhưng không ở rank 1; 0đ: evidence không xuất hiện trong top-3):

| Thành viên | Chiến lược     | Doc-hit (5 câu) | **Điểm rubric chunk-level** | Điểm mạnh                                                                                                               | Điểm yếu                                                                                                                                                                                                                             |
| ---------- | -------------- | --------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Cường      | `fixed_size`   | 5/5             | **10/10**                   | Evidence luôn ở đúng rank 1 cho cả 5 câu — không có câu nào bị "chunk giới thiệu chung chung" đánh bật khỏi vị trí đầu. | Phụ thuộc filter nặng nhất: không filter, evidence biến mất hoàn toàn khỏi top-3 ở Q1 (xem A/B bên dưới).                                                                                                                            |
| Độ         | `by_sentences` | 5/5             | **9/10**                    | Chunk nhỏ nhất, dễ đọc từng câu riêng lẻ.                                                                               | Mất điểm ở Q1: chunk rank-1 (nhóm 3 câu đầu tiên của mục "Khối lượng đăng ký") lại là câu tiếp theo về ELITECH chứ không phải câu "24 tín chỉ" — nhóm câu cố định 3-câu/chunk không may cắt lệch khỏi câu chứa đáp án ngay trước nó. |
| Đức        | `recursive`    | 5/5             | **9/10**                    | Evidence rank-1 ở 4/5 câu, kể cả các câu khó (Q1, Q3, Q4).                                                              | Mất điểm ở Q5 — **nhưng đây thực chất là lỗi đo, không phải lỗi retrieval** (xem Failure Case 2 bên dưới): rank-1 đã đúng nội dung, chỉ khác cách diễn đạt.                                                                          |
| Trí        | `by_heading`   | 5/5             | **8/10**                    | Mỗi chunk là 1 mục `##` trọn vẹn, dễ giải thích.                                                                        | Mất điểm ở Q4 và Q5 — cả 2 đều do chunk "giới thiệu chung" (đoạn mở đầu tài liệu, không có heading riêng) được xếp hạng 1 nhờ điểm chủ đề cao, trong khi chunk chứa số liệu cụ thể (mục con) bị đẩy xuống rank 2.                    |

**Phát hiện quan trọng:** ở mức **doc_id**, cả 4 chiến lược hòa tuyệt đối 5/5.
Chỉ khi chấm ở mức **chunk** (evidence thật có xuất hiện đúng vị trí hay
không), sự khác biệt giữa các chiến lược mới lộ ra rõ ràng (10 vs 9 vs 9 vs 8) — đúng như `docs/SCORING.md` cảnh báo: _"Score cao là tín hiệu xếp hạng,
không phải bằng chứng rằng nội dung đúng."_

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**

> `fixed_size` (Cường) đạt điểm rubric chunk-level cao nhất tuyệt đối (10/10), nhưng nhóm **không kết luận đây là chiến lược "tốt nhất"** một cách vội vàng — ở mức doc_id, tất cả 4 chiến lược đều hoàn hảo 5/5, và khoảng cách 10 so với 8-9 điểm chỉ đến từ việc evidence rơi xuống rank 2 (1đ) chứ không phải sai hoàn toàn (0đ). Với corpus 6 tài liệu hiện tại, nhóm vẫn nghiêng về `by_heading`/`recursive` khi triển khai thật, vì lý do **định tính**: mỗi chunk là 1 đơn vị ngữ nghĩa dễ giải thích, trong khi điểm 10/10 của `fixed_size` một phần đến từ may mắn — ranh giới cắt cứng theo ký tự tình cờ trùng khớp với vị trí câu trả lời trên bộ dữ liệu nhỏ này, chưa chắc giữ được lợi thế khi tài liệu dài/nhiều hơn.

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

| #   | Câu hỏi (Query)                                                                                                                              | Câu trả lời chuẩn (Gold Answer)                                                                                                                                            | Chunk nào chứa thông tin?                                                                                                     |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 1   | Sinh viên chương trình chuẩn được đăng ký tối đa bao nhiêu tín chỉ trong một học kỳ chính? _(cần `metadata_filter={"audience": "student"}`)_ | Tối đa 24 TC, tối thiểu 12 TC (14 TC / 8 TC nếu bị cảnh cáo học tập hoặc chưa đạt chuẩn ngoại ngữ).                                                                        | `course-registration.md` (mục "Khối lượng đăng ký"); đối chiếu `training-regulation-registration-fees.md` (Điều 10, Điều 19). |
| 2   | Sinh viên được mượn tối đa bao nhiêu cuốn sách và trong bao lâu tại Phòng mượn giáo trình 111?                                               | Tối đa 8 cuốn/bạn đọc; hạn mượn 90 ngày, gia hạn 1 lần thêm 30 ngày (tổng tối đa 120 ngày).                                                                                | `library-textbook-loan.md` (mục "Chính sách mượn").                                                                           |
| 3   | Nếu sinh viên rút học phần trong 7 tuần đầu học kỳ thì phải đóng bao nhiêu phần trăm học phí của học phần đó?                                | 50% học phí học phần đó (rút trong tuần đầu học kỳ 2 có thể không phải đóng); không áp dụng học kỳ hè.                                                                     | `training-regulation-registration-fees.md` (Điều 9, trích).                                                                   |
| 4   | Thời gian mở đăng ký xét tốt nghiệp đợt 2025.1 diễn ra khi nào và sinh viên đăng ký ở đâu?                                                   | Từ 03/3/2026 đến hết 15/3/2026; đăng ký từ tài khoản CTT cá nhân, không giới hạn số lần vào đăng ký.                                                                       | `graduation-registration.md`.                                                                                                 |
| 5   | Mẫu đơn đề nghị điều chỉnh điểm dành cho đối tượng nào, và sinh viên cần làm gì khi nộp đơn qua email tới Ban Đào tạo?                       | Mẫu đơn điều chỉnh điểm dành cho **giảng viên**; sinh viên nộp đơn khác qua email trường cấp, kèm ảnh đơn + thẻ SV, tiêu đề email theo cấu trúc [Hạng mục] Mã SV – Họ tên. | `academic-forms-directory.md` + `contact-ban-dao-tao-procedure.md`.                                                           |

### Tổng hợp chất lượng truy xuất của nhóm

Dữ liệu thật từ `analyze_failures.py` (Ollama `bge-m3:567m`, top_k=3), **chấm ở
mức chunk** (evidence cụ thể phải xuất hiện đúng trong nội dung, không chỉ
đúng doc_id):

| #   | Câu hỏi                                | Evidence yêu cầu        | Rank evidence xuất hiện (4 strategy)                          | Ghi chú                                                                                                                                                     |
| --- | -------------------------------------- | ----------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Tín chỉ tối đa chương trình chuẩn      | `"24 tín chỉ"`          | fixed_size: 1, by_sentences: 2, recursive: 1, by_heading: 1   | Duy nhất `by_sentences` mất điểm — xem Failure Case 1.                                                                                                      |
| 2   | Mượn sách Phòng 111                    | `"8 cuốn"`              | Cả 4: rank 1                                                  | Câu dễ nhất — mọi chiến lược đều đưa evidence lên rank 1.                                                                                                   |
| 3   | Rút học phần 7 tuần đầu — % học phí    | `"50% học phí"`         | Cả 4: rank 1                                                  | `course-registration` vẫn lọt top-3 (không có số %) nhưng luôn thua điểm so với chunk có số liệu thật.                                                      |
| 4   | Thời gian đăng ký tốt nghiệp 2025.1    | `"03/3/2026"`           | fixed_size: 1, by_sentences: 1, recursive: 1, by_heading: 2   | Chỉ `by_heading` mất điểm — đoạn mở đầu tài liệu (không có ngày cụ thể) được xếp rank 1 nhờ điểm chủ đề cao hơn đoạn "## Thời gian đăng ký" chứa ngày thật. |
| 5   | Đối tượng dùng mẫu đơn điều chỉnh điểm | `"dành cho giảng viên"` | fixed_size: 1, by_sentences: 1, recursive: 2*, by_heading: 2* | `recursive`/`by_heading` "mất điểm" nhưng đây là lỗi đo, không phải lỗi retrieval — xem Failure Case 2.                                                     |

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**

> Chạy A/B (có/không `metadata_filter={"audience":"student"}`) cho Query 1 trên cả 4 chiến lược cho kết quả **khác nhau rõ rệt theo từng chiến lược**, không đơn giản là "có ích" hay "vô ích":
>
> - **`fixed_size` và `by_sentences`: filter QUYẾT ĐỊNH sự tồn tại của đáp án đúng.** Không filter, evidence `"24 tín chỉ"` **biến mất hoàn toàn** khỏi top-3 — toàn bộ top-3 bị `training-regulation-registration-fees` (audience: all, cũng chứa số liệu 24 TC nhưng viết tắt khác) chiếm chỗ. Nếu không filter, agent sẽ trả lời từ nguồn sai dù nội dung na ná đúng.
> - **`recursive`: filter cải thiện precision nhưng không phải sống còn.** Không filter, evidence vẫn có trong top-3 nhưng bị đẩy từ rank 1 xuống rank 3.
> - **`by_heading`: filter không thay đổi gì** — evidence đã ở rank 1 dù có filter hay không, vì chunk theo heading "## Khối lượng đăng ký" đủ đặc trưng để tự nhiên thắng điểm mà không cần lọc.
>
> Kết luận: **giá trị của metadata filter phụ thuộc vào chiến lược chunking**, đây là phát hiện nhóm không lường trước khi thiết kế corpus.

### Failure Case 1 — `by_sentences`, Query 1

- **Query:** "Sinh viên chương trình chuẩn được đăng ký tối đa bao nhiêu tín chỉ trong một học kỳ chính?"
- **Bằng chứng từ top-k:** rank 1 (score=429.897) là chunk bắt đầu bằng _"- Chương trình ELITECH: tối đa 28 TC..."_ — không chứa `"24 tín chỉ"`. Chunk chứa đúng câu trả lời (`"Chương trình chuẩn: tối đa 24 tín chỉ..."`) chỉ đứng rank 2 (score=398.062).
- **Nguyên nhân:** `SentenceChunker(max_sentences_per_chunk=3)` nhóm cố định 3 câu/chunk không quan tâm ranh giới ngữ nghĩa. Câu chứa "24 tín chỉ" (câu đầu của mục "Khối lượng đăng ký") bị nhóm chung với 2 câu _trước đó_ (thuộc đoạn mở đầu tài liệu) thành chunk rank-2, trong khi câu "ELITECH: 28 TC" cùng 2 câu _sau_ nó tạo thành chunk rank-1 — và chunk rank-1 tình cờ có điểm cosine cao hơn vì mật độ từ khóa "chương trình/TC/tối đa" dày hơn dù không chứa số 24.
- **Thay đổi đề xuất:** thêm overlap giữa các chunk câu liền kề (hiện `SentenceChunker` không có overlap), hoặc giảm `max_sentences_per_chunk` xuống 1-2 để mỗi con số quan trọng có chunk riêng, giảm rủi ro bị "chunk lân cận" có mật độ từ khóa cao hơn nhưng thiếu số liệu thắng điểm.

### Failure Case 2 — `recursive` & `by_heading`, Query 5 (lỗi đo, không phải lỗi retrieval)

- **Query:** "Mẫu đơn đề nghị điều chỉnh điểm dành cho đối tượng nào?"
- **Bằng chứng từ top-k:** rank 1 của cả 2 chiến lược là chunk _"...là biểu mẫu duy nhất trong danh mục này **dành riêng cho giảng viên**..."_ — nội dung **đúng hoàn toàn** (trả lời được câu hỏi), nhưng script chấm điểm dùng khớp chuỗi cứng `"dành cho giảng viên"` nên **không nhận diện được** vì có thêm từ "riêng" chen giữa. Chỉ rank 2 (`"...(dành cho giảng viên): giảng viên sử dụng..."`) khớp chuỗi chính xác.
- **Nguyên nhân:** đây không phải lỗi chunking/retrieval — retrieval đã đưa đúng đáp án lên rank 1. Lỗi nằm ở **thiết kế evidence string cho benchmark**: so khớp chuỗi con (substring) chính xác quá cứng nhắc, không chấp nhận diễn đạt lại (paraphrase) dù ngữ nghĩa giống hệt.
- **Thay đổi đề xuất:** cho mỗi query nhiều biến thể evidence hợp lệ (ví dụ `["dành cho giảng viên", "dành riêng cho giảng viên"]`) thay vì 1 chuỗi cố định; hoặc dùng LLM thật để chấm "câu trả lời có đúng không" thay vì so khớp chuỗi, chỉ giữ substring-match làm bước lọc nhanh sơ bộ. Đây là bài học meta quan trọng của cả nhóm: **ngay cả cách nhóm tự đánh giá cũng có thể sai**, không chỉ retrieval mới có failure case.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**

> - Ở mức doc_id, cả 4 chiến lược hòa tuyệt đối 5/5. Chỉ khi chấm ở mức **chunk** (evidence cụ thể có xuất hiện đúng vị trí không), khác biệt thật giữa các chiến lược mới lộ ra (10/9/9/8 trên 10). Bài học cốt lõi của cả lab: **đo bằng doc_id là chưa đủ, phải đo bằng chunk**.
> - A/B filter cho thấy giá trị của `metadata_filter` **phụ thuộc vào chiến lược chunking**: với `fixed_size`/`by_sentences`, bỏ filter khiến đáp án đúng biến mất hoàn toàn khỏi top-3; với `by_heading`, filter không thay đổi gì cả. Đây là phát hiện nhóm không lường trước — ban đầu tưởng filter "luôn có ích" như nhau cho mọi chiến lược.
> - Phát hiện meta quan trọng nhất: **1 trong 2 "failure case" của nhóm hóa ra là lỗi của chính cách nhóm tự chấm điểm** (so khớp chuỗi cứng "dành cho giảng viên" bỏ sót câu trả lời đúng "dành riêng cho giảng viên"), không phải lỗi retrieval. Điều này cho thấy tự động hóa việc chấm điểm cũng cần được kiểm chứng lại, không thể tin tuyệt đối vào con số.

**Bài học rút ra khi so sánh trong nhóm:**

> Cùng tài liệu, cùng embedding, nhưng cách chunk khác nhau tạo ra khác biệt rõ rệt ở **vị trí** (rank) mà đáp án đúng xuất hiện, dù tài liệu đúng vẫn luôn nằm trong top-3. `fixed_size` của Cường — chiến lược đơn giản nhất — lại đạt điểm chunk-level cao nhất, một phần vì ranh giới cắt cứng 800 ký tự tình cờ giữ trọn câu trả lời trong cùng 1 chunk ở hầu hết trường hợp trên corpus nhỏ này. `by_sentences` mất điểm đúng vào chunk kế bên chunk có đáp án — một lời nhắc rằng "chunk nhỏ hơn" không tự động "chính xác hơn".

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**

> Sẽ mở rộng corpus (nhiều hơn 6 tài liệu, đặc biệt thêm các tài liệu "gần giống" nhau về từ vựng nhưng khác đối tượng/nội dung) để chiến lược chunking và metadata filter có cơ hội thể hiện khác biệt rõ ràng hơn — bộ 5 query + 6 tài liệu hiện tại đã đủ để pass checkpoint nhưng chưa đủ "khó" để phân biệt chất lượng giữa các chiến lược khi dùng embedding thật.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí                                 | Điểm tự đánh giá |
| ---------------------------------------- | ---------------- |
| Lựa chọn tài liệu (Document Set Quality) | 10 / 10          |
| Thiết kế chiến lược (Strategy Design)    | 14 / 15          |
| Chất lượng truy xuất (Retrieval Quality) | 10 / 10          |
| Thuyết trình (Demo)                      | 5 / 5            |
| **Tổng phần nhóm**                       | **39 / 40**      |
