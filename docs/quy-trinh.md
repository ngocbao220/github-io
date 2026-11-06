# Quy trình dựng benchmark

```
config/collect/*.yaml (thư mục nguồn trên server + quota theo bucket)   config/models/*.yaml (đường dẫn mô hình)
  │
  ▼  tools/collect.py, lặp đến khi mọi bucket đủ quota hoặc hết nguồn
  │   [A] ffmpeg → wav mono 16 kHz, tối đa N phút/file
  │   [B] segment.py: Silero VAD → Nemotron-Diarization → zipformer ASR → <id>_transcript.txt
  │   [C] Qwen3-Omni nghe 3 đoạn trích + đọc transcript → genre, accent, channel, noise, distance
  │       (số người nói đếm từ diarization)
  │   [D] xếp vào bucket khớp `match` và còn thiếu quota; không cần thì bỏ (vẫn lưu nhãn để không phân loại lại)
  │   [E] segment.py: quy tắc 3.1 / 3.2 → <id>_turnevent.txt
  │   [F] build_manifest.py → manifests/<id>.jsonl + clips/<event_id>.wav (kèm `times` để đo latency)
  ▼
tools/ask_models.py   Qwen Instruct + Thinking trả lời bộ câu hỏi trên từng segment → out/<model>.jsonl
  ▼
tools/stats.py        bảng độ phủ, ô thiếu quota  ──► thêm nguồn / tăng quota / tools/augment.py (synthetic)
  ▼
server.py + index.html   người gán nhãn pilot (trang đọc manifest qua /api/samples)
  ▼
tools/audit_questions.py  bỏ / viết lại / giữ từng câu hỏi
notebooks/inspect_answers.ipynb  xem trực quan câu hỏi, câu trả lời của mô hình và người
```

## Chạy trên server

1. Config nằm trong `config/` và được quản lý bằng Hydra:
   ```
   config/config.yaml            # paths (thư mục dùng chung) + gom các nhóm bên dưới
   config/models/default.yaml    # đường dẫn mô hình (mẫu)
   config/collect/default.yaml   # thư mục nguồn, bucket, target_minutes, phân loại mức file
   config/segment/default.yaml   # ngưỡng gán sự kiện (bc_max, int_gap)
   config/manifest/default.yaml  # cửa sổ clip quanh sự kiện (pre, post)
   config/quotas/default.yaml    # chỉ tiêu segment mỗi ô cho stats.py
   ```
   Chép `config/models/default.yaml` thành `config/models/local.yaml` và `config/collect/default.yaml` thành `config/collect/local.yaml`, rồi sửa cho máy server. Các file `local.yaml` không commit lên git. Mọi lệnh bên dưới thêm `models=local collect=local` để dùng chúng. Mỗi tham số chỉ nằm ở một file, nên chỉ cần sửa đúng một chỗ. Muốn đổi một giá trị thì ghi đè luôn trên dòng lệnh, ví dụ `collect.buckets.0.target_minutes=60` hoặc `models.qwen_instruct.base_url=http://host:8001/v1`.
2. Cài `pip install -r tools/requirements.txt`, và cài thêm ffmpeg.
3. Chạy Qwen bằng vLLM, mỗi bản một cổng, khớp với `base_url` và `served_name` trong config `models`:
   ```
   vllm serve /models/Qwen3-Omni-30B-A3B-Instruct --served-model-name qwen3-omni-instruct --port 8001
   vllm serve /models/Qwen3-Omni-30B-A3B-Thinking --served-model-name qwen3-omni-thinking --port 8002
   ```
4. Thu thập và cắt segment: `python3 tools/collect.py models=local collect=local dry_run=true` để xem có bao nhiêu file nguồn và quota còn thiếu, rồi bỏ `dry_run=true` để chạy thật. Chạy lại sẽ tiếp tục từ chỗ dừng.
5. Hỏi mô hình:
   ```
   python3 tools/ask_models.py --manifest 'manifests/*.jsonl' --model qwen_instruct --out out/qwen_instruct.jsonl models=local
   python3 tools/ask_models.py --manifest 'manifests/*.jsonl' --model qwen_thinking --out out/qwen_thinking.jsonl models=local
   ```
   Thêm `--dry-run` để xem prompt và schema, `--limit 5` để chạy thử.
6. Thống kê: `python3 tools/stats.py --answers out/qwen_instruct.jsonl out/qwen_thinking.jsonl --csv out/stats collect=local`.
7. Nếu thiếu điều kiện âm thanh thì tạo thêm, ví dụ `python3 tools/augment.py --manifest manifests/<id>.jsonl --op noise --noise-dir <musan> --out manifests/<id>_noise.jsonl`. Các phép khác là `phone`, `reverb`, `quiet`.
8. Pilot với người: `HOST=0.0.0.0 EDIT_TOKEN=... python3 server.py`, mở trang và gán nhãn. Gộp các file JSON xuất ra thành `humans.jsonl` (mỗi dòng một file), rồi chạy `audit_questions.py` và mở notebook.

Data CSKH phải che thông tin cá nhân (tên, số điện thoại, địa chỉ…) trong transcript và audio trước bước 8.

Gán sự kiện tự động chỉ là gợi ý: ngưỡng ở `config/segment/default.yaml` (`bc_max`, `int_gap`) chỉnh được, hoặc ghi đè trên dòng lệnh như `segment.bc_max=1.5`. Chen ngang không chồng lời chỉ được bắt khi câu trước kết thúc bằng từ bỏ ngỏ (“mà”, “thì”, “là”…), nên phần còn lại phải dựa vào người gán nhãn ở câu `event`.

## Nguyên tắc chia việc người và máy

1. **Cái gì đo được bằng số thì máy đo**: khoảng lặng sau lượt (`gap_after_sec_auto`), có nói chồng không (`overlap_auto`), ai nói tiếp (`next_auto`), độ ồn, độ vang, dải tần. Các trường này có đuôi `_auto` trong manifest. Người chỉ cần sửa khi máy sai rõ.
2. **Người trả lời phần cần hiểu ý và nghe tinh**: lượt nói đã xong chưa, có phải tiếng đệm không, ngữ điệu cuối câu, mốc kết thúc lượt.
3. **Câu hỏi nào mô hình (vd. Qwen) trả lời đủ tốt thì bỏ khỏi phần người**: dùng `tools/audit_questions.py` sau mỗi vòng (khai-thac.md, mục 6).

## Vì sao mỗi sự kiện là một mẫu

Turn detection là bài toán *tại một thời điểm*: “ở đây có được nói không?”. Vì vậy mẫu được neo vào một sự kiện, kèm 12 giây ngữ cảnh trước và 3 giây sau (`--pre`, `--post`). Người dùng là người phát sinh sự kiện, nên vai tự đảo theo từng sự kiện. Nhờ đó một cuộc hội thoại cho ra nhiều mẫu với đủ loại sự kiện.

Lưu ý: data thật lệch mạnh về MoT (vd. `10154_2`: 29 MoT, 15 EoT, 3 BC, 2 INT). Khi chọn mẫu phải cân lại (khai-thac.md, mục 4), nếu không thì điểm của benchmark sẽ chủ yếu đo khả năng “chờ”.
