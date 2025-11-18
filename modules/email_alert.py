"""
modules/email_alert.py
Gửi email cảnh báo qua SMTP (Gmail)
"""
import smtplib
import ssl
from email.message import EmailMessage
import threading

class EmailAlertSystem:
    def __init__(self):
        # --- ĐIỀN THÔNG TIN TRỰC TIẾP VÀO ĐÂY ĐỂ CHẠY LUÔN ---
        # Lưu ý: Mật khẩu là "Mật khẩu ứng dụng" (16 ký tự), KHÔNG PHẢI mật khẩu đăng nhập Gmail
        self.sender_email = "email_cua_ban@gmail.com" 
        self.email_password = "mat_khau_ung_dung_16_ky_tu"    
        
        self.port = 465  # SSL
        self.smtp_server = "smtp.gmail.com"

    def send_alert_async(self, receiver_email, subject, content):
        """Gửi email trong một luồng riêng để không làm đơ camera"""
        thread = threading.Thread(target=self._send, args=(receiver_email, subject, content))
        thread.start()

    def _send(self, receiver_email, subject, content):
        if not receiver_email or "@" not in receiver_email:
            print("Email người nhận không hợp lệ.")
            return

        msg = EmailMessage()
        msg.set_content(content)
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = receiver_email

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.port, context=context) as server:
                server.login(self.sender_email, self.email_password)
                server.send_message(msg)
            print(f"✅ Đã gửi cảnh báo tới {receiver_email}")
        except Exception as e:
            print(f"❌ Lỗi gửi email: {e}")