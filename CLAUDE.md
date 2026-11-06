# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Mục tiêu

Repo này phục vụ việc chọn data và gán nhãn để làm **benchmark turn detection cho tiếng Việt**, đánh giá hai kiểu mô hình:
- **Easy Turn**: utterance-level, phán đoán trên cả một câu/đoạn (nói xong / chưa xong / tiếng đệm / chen ngang).
- **SoulX-Duplug**: frame-level, phán đoán theo từng khung thời gian, nên cần mốc thời gian chính xác (vd. `turn_end_sec`).

Yêu cầu với data benchmark: phủ đủ domain (podcast, trò chuyện, phỏng vấn YouTube; phim; chăm sóc khách hàng…) và đủ kịch bản thực tế (nhiễu, nói nhỏ, mic gần/xa, qua điện thoại…), được **phân tầng theo độ khó** để phản ánh đúng chất lượng mô hình ngoài thực tế. Khi đổi câu hỏi hay pipeline, giữ cho nhãn đủ để lọc/phân tầng theo domain, điều kiện âm thanh và độ khó.

## Chạy

Không có build, lint hay test. Chỉ cần Python 3 (stdlib):

    python3 server.py                                    # http://127.0.0.1:8000
    HOST=0.0.0.0 PORT=8000 EDIT_TOKEN=matkhau python3 server.py

Mở thẳng `index.html` hoặc qua GitHub Pages (https://ngocbao220.github.io/github-io/) cũng chạy được nhưng chỉ đọc: không có `/api/config`, nút sửa câu hỏi tự ẩn, trang dùng câu hỏi mặc định trong `index.html`.

Tools (chạy độc lập):

    python3 tools/build_manifest.py 10154_2 --dir <thư mục> [--pre 12] [--post 3] [--clips out_dir]   # --clips cần ffmpeg
    python3 tools/audit_questions.py --humans humans.jsonl --model qwen.jsonl

## Kiến trúc

- **`index.html`**: toàn bộ app gán nhãn (HTML/CSS/JS thuần, một file). Các phần chính:
  - `SAMPLES`: danh sách mẫu, mỗi mẫu có `tags` (`turntaking` hoặc `slm`); audio ở `audio/`.
  - `PANELS`: map `tag -> [panel]`, mỗi panel là một tab gồm `qs` (câu hỏi). Tag của mẫu quyết định tab nào hiện. Câu hỏi có `codes` thì giá trị lưu là mã (vd. `EOT`, `close_mic`) thay cho chỉ số đáp án.
  - Panel `type:"score"` (thang `SCALE_*`, sinh câu chấm điểm từ `descs`) vẫn được hỗ trợ trong `buildPanels`, nhưng slm hiện không dùng.
  - Nút xuất JSON tải về một bản ghi `{sample_id, annotator, answers: {"<panel>.<qid>": value}, marks: {turn_end_sec}, missing}`. Đây cũng là định dạng đầu vào của `tools/audit_questions.py`.
- **`server.py`**: phục vụ `/`, `/index.html`, `/audio/*` và `GET/PUT/DELETE /api/config`. `valid()` kiểm tra cấu trúc config trước khi lưu.
- **`data/config.json`**: bộ câu hỏi đã lưu từ trình soạn trong trang. Nó **ghi đè toàn bộ** `PANELS` mặc định khi chạy có server. Vì vậy sửa câu hỏi thì phải sửa **cả** `index.html` và `data/config.json` (rồi kiểm tra bằng `server.valid`). `data/` được commit lên git (không còn trong `.gitignore`).
- **`tools/build_manifest.py`**: từ `<name>_transcript.txt` + `<name>_turnevent.txt` (EoT/MoT/FI/BC/INT) tạo `manifests/<name>.jsonl`, mỗi sự kiện turn là một mẫu, có cửa sổ clip và các trường `*_auto` để người gán nhãn chỉ kiểm tra. Trang hiện chưa đọc manifest.
- **`tools/audit_questions.py`**: so nhãn người với nhãn mô hình (vd. Qwen) theo từng câu hỏi, kết luận DROP (để mô hình tự gán) / REWRITE / KEEP / WATCH.

## Quy ước

- Toàn bộ nội dung hiển thị và câu hỏi viết bằng tiếng Việt có dấu.
- Đổi câu hỏi thì giữ ổn định `id`/`codes` nếu được, vì chúng là khoá trong dữ liệu đã xuất và trong audit.
