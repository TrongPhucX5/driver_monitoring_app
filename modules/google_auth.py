"""
modules/google_auth.py
Xử lý mở trình duyệt để đăng nhập Google
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

class GoogleAuthManager:
    def __init__(self):
        # Quyền chúng ta cần: Email và Thông tin cơ bản (Tên, Ảnh)
        self.SCOPES = [
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
        ]
        self.client_secrets_file = 'client_secret.json'

    def login(self):
        """
        Mở trình duyệt, chờ người dùng đăng nhập, và trả về ID Token
        """
        if not os.path.exists(self.client_secrets_file):
            return False, "LỖI: Thiếu file 'client_secret.json' trong thư mục dự án!"

        try:
            # 1. Tạo luồng đăng nhập
            flow = InstalledAppFlow.from_client_secrets_file(
                self.client_secrets_file, self.SCOPES)
            
            # 2. Mở trình duyệt local server (tự động tìm port trống)
            print("Đang mở trình duyệt...")
            creds = flow.run_local_server(port=0)
            
            # 3. Lấy ID Token (Cái này mới quan trọng để gửi cho Firebase)
            if creds and creds.id_token:
                return True, creds.id_token
            else:
                return False, "Không lấy được Token."
        except Exception as e:
            return False, f"Lỗi Google Auth: {str(e)}"