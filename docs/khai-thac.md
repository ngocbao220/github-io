# Khai thác câu trả lời của người gán nhãn

Đầu vào: các file JSON mà trang xuất ra, mỗi mẫu mỗi người một file:

```json
{"sample_id": "10154_2_001", "annotator": "an01",
 "answers": {"tcontent.event": "MOT", "tvoice.final_pitch": "LEVEL", ...},
 "marks": {"turn_end_sec": 7.38}, "missing": []}
```

Gộp tất cả thành một file JSONL, rồi nối với manifest qua `sample_id` = `event_id` để có thêm `*_auto`, nguồn file và thời gian.

---

## 1. Gộp nhãn của nhiều người

Mỗi mẫu cần **ít nhất 2 người**, và **3 người** cho mẫu thuộc tầng khó hoặc mẫu bị lệch.

- **Nhãn cuối của câu phân loại**: lấy đa số. Câu trả lời `UNK` không tính là một phiếu.
  - `event` chỉ được chốt khi có ≥ 2 phiếu giống nhau và chiếm ≥ 2/3 số phiếu. Nếu không, mẫu vào hàng **chờ xem lại**, không đưa vào benchmark.
  - Nếu sau này có nhiều người gán nhãn với chất lượng khác nhau, thay đa số bằng Dawid–Skene để đánh trọng số theo độ tin của từng người.
- **`turn_end_sec`**: lấy trung vị của các người. Nếu chênh lệch giữa các người > 200 ms thì đưa đi xem lại. Độ chênh này cũng là sai số tối thiểu khi chấm độ trễ (mục 5).
- **Đối chiếu với máy**: khi nhãn người khác `event_auto`, ghi lại cặp (máy → người). Ma trận này cho biết cách gán tự động sai ở đâu, để sửa pipeline vòng sau.
- **Kiểm tra mâu thuẫn**: `event=EOT` mà `next_auto=SAME`, hoặc `event=MOT` mà `next_auto=OTHER`. Không loại tự động, chỉ đánh dấu để xem.

**Theo dõi từng người gán nhãn:** tính tỉ lệ khớp với nhãn đa số và kappa trên các mẫu chung. Người có kappa thấp kéo dài thì đào tạo lại. Cách này cũng cho biết có ai đang chọn đại hay không.

---

## 2. Tính độ khó của từng mẫu

Độ khó gồm bốn thành phần, mỗi phần chuẩn hoá về [0, 1]:

| Thành phần | Lấy từ | Ý nghĩa |
|---|---|---|
| **Mơ hồ** | 1 − tỉ lệ đồng thuận về `event`, cộng thêm phần của `confidence` MID/LOW | người cũng phân vân |
| **Ngược tín hiệu** | xem bảng dưới | tín hiệu bề mặt chỉ sai hướng |
| **Âm thanh** | `audibility=NOISY_OK`, `distance=FAR`, `channel≠CLEAN_MIC`, `noise_type≠QUIET` | điều kiện thu kém |
| **Hội thoại** | nhiều “ờ, ừm” (`disfluency_auto`), nói nhanh (`pace_auto`), `genre`≠READ, nói chồng (`overlap_auto`) | nhịp khó đoán |

**Ngược tín hiệu** là thành phần đáng giá nhất, vì đó là nơi mô hình kém sẽ bị lộ:

| Nhãn đúng | Tín hiệu đánh lừa |
|---|---|
| MOT | `complete_auto=COMPLETE`, `final_pitch=FALL`, `final_volume=FADING`, `gap_after_sec_auto` dài (> 0,5 s) |
| EOT | `complete_auto=INCOMPLETE`, `final_pitch=LEVEL/RISE`, `gap_after_sec_auto` ngắn (< 0,2 s) |
| BC | tiếng đệm dài hoặc có nội dung (“ừ đúng rồi”) |
| INT | bắt đầu khi bên kia chưa có dấu hiệu dừng |

Mỗi tín hiệu đánh lừa cộng một điểm, rồi chia cho số tín hiệu có thể có.

Điểm độ khó = trung bình có trọng số của bốn thành phần. Trọng số khởi điểm gợi ý là 0,3 / 0,4 / 0,15 / 0,15. Sau vòng đầu cần **hiệu chỉnh lại**: chạy hai mô hình gốc, kiểm tra điểm độ khó có tương quan với tỉ lệ mô hình sai không, rồi chỉnh trọng số theo đó. Nếu không làm bước này thì độ khó chỉ là cảm tính.

Chia **3 tầng** theo phân vị của điểm: **dễ** (dưới 40%), **vừa** (40–80%), **khó** (trên 80%). Lưu điểm gốc cạnh tên tầng để có thể chia lại sau.

Mẫu mà cả hai mô hình gốc đều sai nhưng người đồng thuận cao vẫn là mẫu hợp lệ, và rất có giá trị. Không dùng chuyện “mô hình sai” để định nghĩa độ khó, nếu không benchmark sẽ bị thiên về mô hình gốc.

---

## 3. Lọc ra bộ benchmark

Một mẫu được đưa vào benchmark khi:
- `event` đã được chốt (mục 1) và khác `UNK`.
- `audibility` ≠ `UNUSABLE`.
- Có `turn_end_sec` nếu `event` ∈ {EOT, INT}.

Mẫu không đạt không bị xoá mà lưu riêng. Chúng có thể dùng làm data train hoặc để xem cách gán nhãn sai ở đâu.

---

## 4. Cân bằng và bảng độ phủ

Lập bảng đếm theo các trục: **`event` × tầng độ khó × `genre` × `accent` × điều kiện âm thanh** (gộp `channel` + `noise_type` + `distance` thành một số nhóm, ví dụ sạch / ồn / xa / điện thoại).

- **Đặt chỉ tiêu tối thiểu cho mỗi ô quan trọng**, ví dụ ≥ 50 mẫu cho mỗi (`event` × tầng), ≥ 30 mẫu cho mỗi (`event` × domain). Đủ số đó thì khoảng tin cậy của từng lát cắt mới đủ hẹp để so sánh.
- **Cân `event`**: data thật lệch về MOT. Giữ tỉ lệ EOT : MOT : BC : INT gần đều trong bộ chính. Vẫn báo thêm điểm trên bộ theo phân phối tự nhiên để biết chất lượng ngoài thực tế.
- **Ô thiếu**: ưu tiên lấy thêm data thật từ nguồn phù hợp (CSKH cho BC; phim, tranh luận cho INT). Nếu vẫn thiếu điều kiện âm thanh thì tạo bằng augmentation (trộn tiếng ồn, giả vang, giả điện thoại) và **gắn cờ `synthetic`**. Báo điểm data thật và data tổng hợp riêng.
- **Chia theo cuộc hội thoại**, không theo mẫu: mọi mẫu của một `conversation_id` (và tốt nhất là của cùng một người nói) phải ở chung một tập (dev hoặc test), để không rò thông tin.

---

## 5. Chấm hai mô hình

### Ánh xạ nhãn

| Benchmark | Easy Turn (dự kiến) | SoulX-Duplug |
|---|---|---|
| `EOT` | complete | được nói (sau `turn_end_sec`) |
| `MOT` | incomplete | phải im |
| `BC` | backchannel | không giành lời |
| `stop_request=YES` | wait | dừng / im |
| `INT` | không có lớp riêng | phát hiện người dùng chen ngang và dừng nói |

Bảng trên là giả định. Cần đối chiếu lại với tên lớp và đầu ra thật của từng mô hình trước khi chấm. `INT` chủ yếu dùng để chấm Duplug. Với Easy Turn chỉ báo riêng, không đưa vào macro-F1.

### Easy Turn (utterance-level)
- Đưa vào mô hình đoạn audio của người dùng, cắt đến cuối lượt (không lộ phần sau sự kiện).
- **Chỉ số chính**: macro-F1 trên 4 lớp. Báo kèm F1 từng lớp và ma trận nhầm lẫn.
- **Lỗi đáng quan tâm nhất**: MOT bị đoán là complete (gây ngắt lời) và EOT bị đoán là incomplete (gây chờ lâu). Báo riêng hai tỉ lệ này.

### SoulX-Duplug (frame-level)
Cho mô hình chạy trên toàn bộ clip (12 giây ngữ cảnh + 3 giây sau), lấy thời điểm `t_model` khi mô hình quyết định nói (hoặc dừng).
- **EOT, độ trễ**: `t_model − turn_end_sec`. Báo trung vị, P90 và tỉ lệ phản hồi trong vòng 0,5 s / 1 s. Nếu đến hết clip vẫn không nói thì tính là trượt.
- **EOT, nói sớm**: `t_model < turn_end_sec − δ` (δ là sai số mốc, lấy từ độ chênh giữa người ở mục 1, khoảng 100–200 ms) tính là ngắt lời.
- **MOT, ngắt lời sai**: tỉ lệ mẫu mô hình nói trong lúc người dùng ngừng giữa chừng. Đây là chỉ số quan trọng nhất về trải nghiệm.
- **BC**: tỉ lệ mô hình coi tiếng đệm là lượt nói và giành lời.
- **INT / stop_request**: tỉ lệ dừng đúng và thời gian từ lúc người dùng chen vào đến lúc mô hình dừng.

Để so sánh với Easy Turn, có thể quy kết quả Duplug về nhãn utterance-level (có nói trong cửa sổ [`turn_end_sec`, +1 s] hay không) và tính cùng macro-F1.

### Báo cáo
Mỗi chỉ số báo theo: **tổng**, **từng tầng độ khó**, **từng domain** (`genre` và nguồn file), **vùng miền và tuổi** (`accent`, `age`), **từng điều kiện âm thanh**, và **data thật / tổng hợp**. Kèm khoảng tin cậy 95% bằng bootstrap theo cuộc hội thoại. Ô nào ít hơn chỉ tiêu ở mục 4 thì ghi rõ là chưa đủ mẫu. Cách đọc kết quả: mô hình tốt thì tụt điểm ít từ tầng dễ sang tầng khó, chứ không chỉ có điểm tổng cao.

---

## 6. Vòng lặp cải tiến câu hỏi

Sau mỗi vòng gán nhãn khoảng vài trăm mẫu:

```
python3 tools/audit_questions.py --humans humans.jsonl --model qwen.jsonl
```

- **DROP**: mô hình trả lời tốt, nên bỏ khỏi phần người và để máy gán (ứng viên: `final_volume`, `final_speed`).
- **REWRITE**: chính người cũng không đồng thuận, nghĩa là câu hỏi mơ hồ. Viết lại hướng dẫn hoặc gộp đáp án.
- **KEEP**: người đồng thuận nhưng máy sai, nên câu này là chỗ người thật sự cần thiết.

Ngoài ra, xem mỗi câu thuộc nhóm độ khó có thật sự tương quan với lỗi của mô hình không (mục 2). Câu không tương quan và cũng không dùng làm lát cắt báo cáo thì bỏ.
