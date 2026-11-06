# Bộ câu hỏi gán nhãn turn-taking và lý do

Mỗi câu hỏi phải phục vụ ít nhất một trong bốn vai trò. Câu nào không có vai trò nào thì bỏ.

| Vai trò | Dùng để | Ký hiệu |
|---|---|---|
| **Nhãn đúng** (ground truth) | chấm mô hình đúng/sai | GT |
| **Strata** (lát cắt) | báo điểm theo domain, điều kiện âm thanh | ST |
| **Độ khó** | xếp mẫu vào tầng dễ / vừa / khó | DK |
| **Kiểm soát chất lượng** | loại mẫu hỏng, đo độ tin của nhãn | QC |

Mã đáp án (`codes`) và `id` là khoá trong dữ liệu xuất ra. Khi sửa câu chữ, giữ nguyên mã nếu ý nghĩa không đổi. Câu hỏi nằm ở `PANELS.turntaking` trong `index.html` **và** trong `data/config.json`.

---

## 1. Nội dung lượt nói (`tcontent`): phần quan trọng nhất

### `event`: Ở cuối đoạn, lượt nói của người dùng là gì?  · GT
`EOT` nói xong · `MOT` chưa nói xong · `BC` tiếng đệm · `INT` chen ngang · `UNK` không rõ

**Lý do:** đây là nhãn chính của benchmark, khớp trực tiếp với đầu ra của cả hai mô hình (khai-thac.md, mục 5). Máy đã gán sơ bộ (`event_auto`) và người xác nhận, vì nhãn tự động từ khoảng lặng hay sai đúng ở những ca quan trọng nhất: ngừng lâu nhưng chưa xong, hoặc xong mà không ngừng. `UNK` được giữ để người không bị ép đoán. Mẫu `UNK` không dùng để chấm, nhưng cho biết ca nào mơ hồ.

### `stop_request`: Người dùng có đang bảo bên kia dừng hoặc đợi không?  · GT
`YES` · `NO` · `UNK`

**Lý do:** Easy Turn có trạng thái riêng cho “bảo đợi”. Ca này cũng nguy hiểm cho hệ full-duplex: đáp lại lúc người dùng nói “khoan đã” là lỗi rất dễ thấy. Tách ra câu riêng vì nó trực giao với `event`: “đợi tí” có thể vừa là câu trọn vẹn vừa là chen ngang.

### Đã bỏ: `complete`, `next`
Hai câu này từng có để đo độ khó (câu trọn nghĩa nhưng chưa nhường lời) và để đối chiếu nhãn. Đã bỏ vì trùng với `event`. Thay vào đó:
- **Trọn nghĩa hay không**: để LLM suy ra từ `user_text`, lưu thành `complete_auto`.
- **Ai nói tiếp**: dùng `next_auto` trong manifest.

### `confidence`: Bạn chắc chắn đến đâu?  · DK, QC
`HIGH` · `MID` · `LOW`

**Lý do:** cùng với độ đồng thuận giữa các người gán nhãn, đây là tín hiệu độ khó rẻ nhất. Nó còn giúp tách hai trường hợp: “người không đồng ý vì mẫu khó” và “người không đồng ý vì có người làm ẩu”.

### Mốc `turn_end_sec` (đánh dấu trên sóng âm)  · GT
**Lý do:** SoulX-Duplug chạy theo khung thời gian, nên benchmark cần biết *chính xác* lúc lượt kết thúc để đo độ trễ và phát hiện mô hình nói sớm. Máy đề xuất sẵn (`marks_auto.turn_end_sec`), người kéo lại nếu lệch quá khoảng 100 ms. Chỉ bắt buộc với EOT và INT.

---

## 2. Sắc thái giọng (`tvoice`): tín hiệu âm học ở cuối lượt

| id | Mã | Vai trò |
|---|---|---|
| `final_pitch` | FALL / LEVEL / RISE | DK |
| `final_volume` | FADING / STEADY / LOUDER | DK |
| `final_speed` | SLOWING / STEADY / FASTER | DK |
| `emotion` | HAPPY / SAD / NEUTRAL / ANGRY | ST |

**Lý do:** người nói thường báo hiệu sắp nhường lời bằng giọng hạ, nhỏ dần, chậm lại. Mô hình học được các tín hiệu đó. Mẫu **ngược tín hiệu** chính là mẫu khó: EOT mà giọng lơ lửng, hoặc MOT mà giọng hạ và ngừng lâu. Nếu không có ba câu này thì không phân biệt được “mô hình sai vì mẫu khó” với “mô hình sai vô lý”. Lưu ý tiếng Việt có thanh điệu: thanh của âm tiết cuối ảnh hưởng đến cao độ, nên `final_pitch` cần người nghe theo *ngữ điệu cả cụm*, không theo thanh của một từ.

`emotion` không quyết định độ khó, nhưng giọng giận, gấp thường nói dồn và hay chen ngang. Giữ để báo điểm theo lát cắt.

**Ứng viên giao cho máy:** `final_volume` và `final_speed` đo được bằng năng lượng và tốc độ âm tiết. Nếu audit cho thấy máy khớp người thì bỏ khỏi phần người.

---

## 3. Domain và người nói (`tstyle`)

| id | Mã | Vai trò |
|---|---|---|
| `genre` | STORY / INTERVIEW / SHARE / CHAT / DEBATE / LECTURE / SERVICE / SCENE / READ / OTHER | ST, DK |
| `accent` | NORTH / CENTRAL / SOUTH / FOREIGN / UNK | ST |
| `age` | CHILD / TEEN / YOUNG / MIDDLE / OLD / UNK | ST |

**Lý do:**
- `genre` là trục **domain** của benchmark. Phỏng vấn có lượt dài, ngừng nghĩ nhiều; CSKH (SERVICE) có nhiều “dạ, vâng”; phim (SCENE) có lời diễn, nhịp nhanh. `READ` (đọc theo kịch bản) có ranh giới lượt rõ hơn lời tự nhiên nên dễ hơn; cần biết để không thổi phồng điểm. Nguồn gốc file (YouTube / phim / CSKH) đã có trong metadata. `genre` mô tả *cách nói chuyện*, hai trục này không trùng nhau.
- `accent`: ngữ điệu cuối câu khác nhau giữa các vùng miền. Mô hình train chủ yếu trên một giọng có thể hỏng ở giọng khác, nên cần lát cắt này để phát hiện.
- `age`: trẻ em và người lớn tuổi có nhịp nói, khoảng ngừng khác người trẻ.
- Accent và tuổi thuộc về *người nói*, nên có thể gán một lần cho mỗi người trong cuộc hội thoại rồi dùng lại cho mọi mẫu.

**Đã bỏ, chuyển sang máy:** `pace` (đo bằng số âm tiết/giây), `disfluency` (đếm “ờ, ừm” trong transcript) và `speech_style` (gộp vào `genre=READ`). Vẫn dùng các giá trị này trong tính độ khó, dưới dạng trường `_auto`.

## 4. Điều kiện âm thanh (`tenv`)

| id | Mã | Vai trò |
|---|---|---|
| `audibility` | CLEAR / NOISY_OK / UNUSABLE | QC, DK |
| `distance` | NEAR / MID / FAR | ST, DK |
| `noise_type` | QUIET / CROWD / MUSIC / MACHINE | ST, DK |
| `channel` | CLEAN_MIC / PHONE / SPEAKER_ROOM | ST, DK |

**Lý do:** đây là các kịch bản thực tế cần phủ (ồn, nói nhỏ, xa, qua điện thoại). Mỗi trục là một lát cắt báo điểm riêng. `audibility = UNUSABLE` loại mẫu khỏi benchmark: không ai biết đáp án đúng thì không thể chấm. `NOISY_OK` giữ lại và tính là khó. `CROWD` đáng chú ý riêng: tiếng người nền dễ bị mô hình hiểu nhầm là người dùng vẫn đang nói.

**Ứng viên giao cho máy:** độ ồn (SNR), độ vang (C50) và dải tần (để nhận ra điện thoại) đo được tự động. Người vẫn nên xác nhận `noise_type` vì máy hay nhầm nhạc với tiếng người.

---

## 5. Những gì cố ý không hỏi

- **Câu đã bỏ** (`interrupt_rate`, `respond`, `speakers_end`): trùng với `event`, `next_auto` hoặc với trường `_auto`, nên chỉ làm người gán nhãn mệt thêm.
- **Khoảng lặng, nói chồng**: máy đo chính xác hơn tai người.
- **Giới tính**: không ảnh hưởng nhiều đến turn-taking. Nếu cần lát cắt này thì dùng model nhận dạng người nói.
