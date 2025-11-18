# 🚗 Driver Guard - Hệ thống Giám sát Tài xế Thông minh

**Driver Guard** là ứng dụng Desktop sử dụng Trí tuệ nhân tạo (AI) để giám sát trạng thái tài xế theo thời gian thực. Hệ thống giúp phát hiện sớm các dấu hiệu buồn ngủ, mất tập trung và phát cảnh báo đa cấp độ để đảm bảo an toàn giao thông.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green.svg)
![MediaPipe](https://img.shields.io/badge/AI-MediaPipe-orange.svg)
![Firebase](https://img.shields.io/badge/Cloud-Firebase-yellow.svg)

---

## ✨ Tính năng Nổi bật

### 1. Giám sát AI Thông minh (Smart Monitoring)

- **Phân tích đa chiều:** Theo dõi Mắt (EAR), Miệng (MAR) và Tư thế đầu (Head Pose).
- **Lọc nhiễu thông minh:** Phân biệt được hành động **Nói chuyện/Hát** với **Ngáp**.
- **Phát hiện Xao nhãng:** Cảnh báo khi tài xế quay đầu nhìn gương hoặc cúi xuống nhìn điện thoại quá lâu.
- **Chế độ Kính râm (Sunglasses Mode):** Tự động chuyển sang theo dõi gật gù khi không nhìn thấy mắt.
- **Debug Mode:** Hiển thị lưới 468 điểm khuôn mặt thời gian thực.

### 2. Hệ thống Cảnh báo 4 Cấp độ

- 🟢 **Cấp 0 (An toàn):** Màn hình xanh, không âm thanh.
- 🟡 **Cấp 1 (Nhắc nhở):** Phát hiện Ngáp hoặc Chớp mắt chậm (Viền vàng).
- 🟠 **Cấp 2 (Cảnh báo):** Mắt lờ đờ hoặc Xao nhãng (Viền cam + Bíp ngắn).
- 🔴 **Cấp 3 (Nguy hiểm):** Ngủ gật > 2 giây (Viền đỏ + Còi báo động + **Lưu lịch sử**).
- 🚨 **Cấp 4 (SOS):** Ngủ gật > 4 giây -> **Gửi Email khẩn cấp** kèm cảnh báo cho người thân.

### 3. Quản lý & Đồng bộ Đám mây (Cloud Sync)

- **Đăng nhập đa nền tảng:** Hỗ trợ Email/Mật khẩu và **Google Login**.
- **Đồng bộ cài đặt:** Lưu độ nhạy, âm thanh, email SOS lên Cloud (Firebase). Đổi máy tính không mất cấu hình.
- **Lịch sử & Báo cáo:** Lưu trữ nhật ký vi phạm và chấm điểm an toàn lái xe theo ngày.

---

## 📦 Cấu trúc Dự án

```text
DRIVER_MONITORING_APP/
├── assets/                  # Tài nguyên
│   ├── images/              # Icon Google, Logo App...
│   └── sounds/              # File alert.wav (Âm thanh cảnh báo)
├── modules/                 # Mã nguồn xử lý Logic (Backend)
│   ├── camera.py            # Xử lý luồng video, logic 4 cấp độ
│   ├── email_alert.py       # Gửi email SOS qua SMTP
│   ├── face_processor.py    # AI MediaPipe (Tính toán EAR, MAR, Pose)
│   ├── firebase_service.py  # Kết nối Firebase Auth & Database
│   └── google_auth.py       # Xử lý đăng nhập Google OAuth2
├── ui/                      # Mã nguồn Giao diện (Frontend - PyQt5)
│   ├── login_window.py      # Màn hình Đăng nhập/Đăng ký (Bo tròn, đẹp)
│   └── main_window.py       # Màn hình chính (Dashboard, Chart, History)
├── .gitignore               # Chặn file nhạy cảm khi up lên Git
├── main.py                  # Điểm khởi chạy ứng dụng
├── requirements.txt         # Danh sách thư viện cần cài
└── README.md                # Tài liệu hướng dẫn
⚙️ Hướng dẫn Cài đặt & Chạy
Bước 1: Cài đặt Môi trường
Yêu cầu: Python 3.10 trở lên.

Bash

# 1. Clone dự án
git clone <link-repo-cua-ban>
cd driver_monitoring_app

# 2. Cài đặt thư viện
pip install -r requirements.txt
Lưu ý: Nếu gặp lỗi DLL load failed với MediaPipe, vui lòng cài đặt Visual C++ Redistributable mới nhất từ trang chủ Microsoft.

Bước 2: Cấu hình Bảo mật (Quan trọng!)
Do tính bảo mật, các file chứa khóa API không được tải lên GitHub. Bạn cần tự cấu hình:

File client_secret.json (Cho Google Login):

Tải từ Google Cloud Console (OAuth 2.0 Client IDs - Desktop App).

Đặt file này ngang hàng với main.py.

Cấu hình Firebase:

Mở modules/firebase_service.py.

Cập nhật biến config với thông tin Project Firebase của bạn (API Key, Database URL...).

Lưu ý: Database URL phải chính xác (có dấu / ở cuối nếu cần).

Cấu hình Email:

Mở modules/email_alert.py.

Điền Email gửi và Mật khẩu ứng dụng (App Password).

File Âm thanh:

Đảm bảo có file assets/sounds/alert.wav.

Bước 3: Chạy ứng dụng
Bash

python main.py
📖 Hướng dẫn Sử dụng
Đăng nhập:

Sử dụng Email/Pass hoặc bấm nút Google.

Tích chọn "Ghi nhớ đăng nhập" để lần sau vào thẳng Dashboard.

Cài đặt Cá nhân:

Vào tab Cài đặt -> Nhập "Email người thân (SOS)".

Chỉnh độ nhạy và thời gian nhắm mắt cho phù hợp.

Bấm "Lưu & Đồng bộ".

Bắt đầu Giám sát:

Vào tab Giám sát -> Bấm ▶ BẮT ĐẦU.

Test: Nhắm mắt 3 giây để thấy cảnh báo Đỏ. Nhắm 6 giây để test gửi Email SOS.

Debug: Tích vào "Hiện lưới" để xem AI hoạt động.

Xem Báo cáo:

Vào tab Lịch sử để xem chi tiết các lần vi phạm (Có thể xóa).

Vào tab Báo cáo để xem điểm số an toàn hôm nay.

🛠️ Công nghệ sử dụng
Ngôn ngữ: Python

Giao diện: PyQt5 (Custom Stylesheet, Frameless Window)

Computer Vision: OpenCV, MediaPipe Face Mesh (468 landmarks)

Backend: Google Firebase (Realtime Database, Authentication)

Tiện ích: Threading (Đa luồng), Winsound, SMTP Email, OAuth2.

© 2025 Developed by [Group 11]
```
