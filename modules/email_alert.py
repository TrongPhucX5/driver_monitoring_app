"""
email_alert.py – Module gửi email cảnh báo (Hardcoded credentials cho Demo)
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CẤU HÌNH NGƯỜI GỬI (SENDER) ---
# Bạn điền trực tiếp thông tin của bạn vào đây
SENDER_EMAIL = "trinhvanchinh1109@gmail.com"  # <--- Điền email của bạn
SENDER_PASSWORD = "tzzznshulsasvyig"  #<--- Điền App Password (không phải pass đăng nhập)
# mật khẩu liên quan tui đó cấm lấy lung tung nha    

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def send_alert_email(to_email: str, subject: str, body: str):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        print("⚠️ [EMAIL] Chưa điền SENDER_EMAIL hoặc SENDER_PASSWORD trong file email_alert.py")
        return False
    
    if not to_email:
        print("⚠️ [EMAIL] Chưa có địa chỉ người nhận!")
        return False

    try:
        # Tạo nội dung email
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Kết nối và gửi
        print(f"⏳ Đang gửi email tới {to_email}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        
        print(f"✅ [EMAIL] Đã gửi thành công tới {to_email}")
        return True

    except Exception as e:
        print(f"❌ [EMAIL] Lỗi: {str(e)}")
        return False