# Tài liệu benchmark turn detection tiếng Việt

Mục tiêu: dựng bộ benchmark đánh giá hai kiểu mô hình phát hiện lượt nói:

- **Easy Turn** (utterance-level): nhận một đoạn lời của người dùng, trả về trạng thái của lượt nói (nói xong / chưa xong / tiếng đệm / bảo đợi).
- **SoulX-Duplug** (frame-level, full-duplex): chạy theo từng khung thời gian, quyết định *lúc nào* được nói, nên được chấm cả về **đúng** lẫn **nhanh**.

Bộ data phải phủ đủ domain (podcast, trò chuyện, phỏng vấn, phim, chăm sóc khách hàng…), đủ điều kiện âm thanh thực tế (ồn, nói nhỏ, mic xa, qua điện thoại…) và được **chia tầng theo độ khó**, để điểm số phản ánh đúng chất lượng mô hình ngoài thực tế chứ không chỉ trên data sạch.

| File | Nội dung |
|---|---|
| [quy-trinh.md](quy-trinh.md) | Luồng từ audio thô đến bộ benchmark |
| [cau-hoi.md](cau-hoi.md) | Bộ câu hỏi gán nhãn và lý do của từng câu |
| [khai-thac.md](khai-thac.md) | Gộp nhãn, tính độ khó, chia tầng, chấm hai mô hình |
