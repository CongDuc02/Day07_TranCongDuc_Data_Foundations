# Benchmark Queries — hocvu-university (K3)

Corpus: `data/hocvu-university/` (6 tài liệu). Mỗi gold answer trích được trực tiếp từ
nội dung `.md` tương ứng, ghi rõ `doc_id` nguồn để đối chiếu khi chấm retrieval.

---

## Query 1 (dùng metadata_filter bắt buộc)

**Query:** "Sinh viên chương trình chuẩn được đăng ký tối đa bao nhiêu tín chỉ
trong một học kỳ chính?"

**metadata_filter:** `{"audience": "student"}`

**Gold answer:** Tối đa 24 tín chỉ, tối thiểu 12 tín chỉ (sinh viên bị cảnh cáo
học tập hoặc chưa đạt chuẩn ngoại ngữ thì tối đa 14 TC, tối thiểu 8 TC).

**Nguồn:** `course-registration` (mục "Khối lượng đăng ký") và
`training-regulation-registration-fees` (Điều 10, Điều 19).

---

## Query 2

**Query:** "Sinh viên được mượn tối đa bao nhiêu cuốn sách và trong bao lâu tại
Phòng mượn giáo trình 111?"

**Gold answer:** Tối đa 8 cuốn/bạn đọc; thời hạn mượn 90 ngày, được gia hạn 1 lần
thêm 30 ngày (tổng tối đa 120 ngày).

**Nguồn:** `library-textbook-loan` (mục "Chính sách mượn").

---

## Query 3

**Query:** "Nếu sinh viên rút học phần trong 7 tuần đầu học kỳ thì phải đóng bao
nhiêu phần trăm học phí của học phần đó?"

**Gold answer:** Chỉ phải đóng 50% học phí của học phần đó (riêng nếu rút trong
tuần đầu tiên của học kỳ 2, có thể không phải đóng học phí học phần đó). Quy định
này không áp dụng cho học kỳ hè.

**Nguồn:** `training-regulation-registration-fees` (Điều 9, trích).

---

## Query 4

**Query:** "Thời gian mở đăng ký xét tốt nghiệp đợt 2025.1 diễn ra khi nào và
sinh viên cần đăng ký ở đâu?"

**Gold answer:** Từ ngày 03/3/2026 đến hết ngày 15/3/2026; sinh viên đăng ký xét
tốt nghiệp từ tài khoản Cổng thông tin đào tạo (CTT) cá nhân, không giới hạn số
lần vào đăng ký cho đến khi hết hạn hoặc đăng ký thành công.

**Nguồn:** `graduation-registration`.

---

## Query 5

**Query:** "Mẫu đơn đề nghị điều chỉnh điểm dành cho đối tượng nào, và sinh viên
cần làm gì khi nộp đơn qua email tới Ban Đào tạo?"

**Gold answer:** Mẫu đơn đề nghị điều chỉnh điểm dành cho **giảng viên** (không
phải sinh viên). Khi nộp đơn khác (của sinh viên) qua email, sinh viên cần dùng
email do trường cấp, chụp ảnh đơn và thẻ sinh viên gửi kèm email, và đặt tiêu đề
email theo cấu trúc: [Hạng mục viết tắt] Mã số sinh viên – Họ và tên.

**Nguồn:** `academic-forms-directory` + `contact-ban-dao-tao-procedure`.

---

## Ghi chú kiểm chứng

- Query 1 là query bắt buộc dùng `metadata_filter={"audience": "student"}` theo
  yêu cầu K3 — nếu không filter, hệ thống có thể trả nhầm đoạn từ tài liệu
  `academic-forms-directory` (audience: faculty) hoặc
  `contact-ban-dao-tao-procedure` (audience: staff), vốn không chứa số tín chỉ.
- Tất cả 5 câu đều có thể trả lời bằng cách trích trực tiếp 1–2 câu từ đúng một
  hoặc hai tài liệu trong corpus, không cần suy đoán ngoài nguồn.
