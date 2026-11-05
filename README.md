# Backend sửa câu hỏi

Chạy trên máy/VPS có Python 3 (không cần cài thêm gì):

    EDIT_TOKEN=matkhau python3 server.py                 # http://127.0.0.1:8000
    HOST=0.0.0.0 PORT=8000 EDIT_TOKEN=matkhau python3 server.py   # cho máy khác vào

Mở trang -> nút "✎ Chỉnh sửa câu hỏi" (góc trên phải) -> sửa câu hỏi/đáp án
-> "Render lại" để xem thử, "Lưu" để lưu lên server (data/config.json).
"Về mặc định" xoá bản đã lưu. GitHub Pages / artifact không có backend nên chỉ đọc, nút sửa tự ẩn.
