"""
email_alert.py – Module gửi email cảnh báo
Sử dụng smtplib. Yêu cầu thiết lập biến môi trường.
"""

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Lấy thông tin cấu hình từ Biến Môi Trường ---
# TUYỆT ĐỐI không hardcode mật khẩu vào đây
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD') # Nên dùng "Mật khẩu ứng dụng" của Google

def send_alert_email(to_email: str, subject: str, body: str):
    """
    Gửi email cảnh báo.
    Args:
        to_email (str): Email người nhận.
        subject (str): Chủ đề email.
        body (str): Nội dung email.
    """
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️  [EMAIL] Chưa cấu hình SENDER_EMAIL hoặc SENDER_PASSWORD trong biến môi trường.")
        return False

    try:
        # Tạo đối tượng email
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Kết nối SMTP và gửi
        print(f"Đang gửi email tới {to_email}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Bật bảo mật TLS
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        
        print(f"✅ [EMAIL] Đã gửi cảnh báo thành công tới {to_email}")
        return True

    except Exception as e:
        print(f"❌ [EMAIL] Lỗi khi gửi email: {str(e)}")
        return False

# ----- Test thử module này -----
if __name__ == "__main__":
    # Cần set biến môi trường trước khi chạy
    # export SENDER_EMAIL="your-email@gmail.com"
    # export SENDER_PASSWORD="your-app-password"
    
    if SENDER_EMAIL:
        print(f"Đang test gửi email từ: {SENDER_EMAIL}")
        send_alert_email(
            to_email="recipient-email@example.com", # Thay bằng email nhận test
            subject="[Cảnh Báo] Thử Nghiệm Module Email",
            body="Đây là email thử nghiệm từ ứng dụng giám sát tài xế."
        )
    else:
        print("Vui lòng thiết lập biến môi trường SENDER_EMAIL và SENDER_PASSWORD để test.")