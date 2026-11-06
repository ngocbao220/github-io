# Quy trình dựng benchmark

```
audio thô (YouTube, phim, CSKH…)
  → cắt + phiên âm + tách người nói (máy)
  → gán sự kiện turn sơ bộ (máy)           *_turnevent.txt: EoT / MoT / FI / BC / INT
  → tools/build_manifest.py                 manifests/<tên>.jsonl, mỗi sự kiện = 1 mẫu
  → chọn mẫu theo bảng độ phủ               (xem khai-thac.md, mục 4)
  → người gán nhãn trên index.html          JSON mỗi mẫu, mỗi người
  → gộp nhãn + tính độ khó + chia tầng      (khai-thac.md)
  → bộ benchmark: audio + nhãn + tầng + strata
```

## Nguyên tắc chia việc người và máy

1. **Cái gì đo được bằng số thì máy đo**: khoảng lặng sau lượt (`gap_after_sec_auto`), có nói chồng không (`overlap_auto`), ai nói tiếp (`next_auto`), độ ồn, độ vang, dải tần. Các trường này có đuôi `_auto` trong manifest. Người chỉ cần sửa khi máy sai rõ.
2. **Người trả lời phần cần hiểu ý và nghe tinh**: lượt nói đã xong chưa, có phải tiếng đệm không, ngữ điệu cuối câu, mốc kết thúc lượt.
3. **Câu hỏi nào mô hình (vd. Qwen) trả lời đủ tốt thì bỏ khỏi phần người**: dùng `tools/audit_questions.py` sau mỗi vòng (khai-thac.md, mục 6).

## Vì sao mỗi sự kiện là một mẫu

Turn detection là bài toán *tại một thời điểm*: “ở đây có được nói không?”. Vì vậy mẫu được neo vào một sự kiện, kèm 12 giây ngữ cảnh trước và 3 giây sau (`--pre`, `--post`). Người dùng là người phát sinh sự kiện, nên vai tự đảo theo từng sự kiện. Nhờ đó một cuộc hội thoại cho ra nhiều mẫu với đủ loại sự kiện.

Lưu ý: data thật lệch mạnh về MoT (vd. `10154_2`: 22 MoT, 7 EoT, 1 INT). Khi chọn mẫu phải cân lại (khai-thac.md, mục 4), nếu không thì điểm của benchmark sẽ chủ yếu đo khả năng “chờ”.
