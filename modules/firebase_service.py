"""
modules/firebase_service.py
Backend xử lý dữ liệu với Firebase (Final Fix - Sửa lỗi URL)
"""
import pyrebase
import time
import json
from datetime import datetime
import requests

class FirebaseService:
    def __init__(self):
        config = {
            "apiKey": "AIzaSyC3g4ovxA3cADCqEbx7jZ2052whq5Rctoo",
            "authDomain": "lithe-catbird-476301-p4.firebaseapp.com",
            "projectId": "lithe-catbird-476301-p4",
            "storageBucket": "lithe-catbird-476301-p4.firebasestorage.app",
            
            # --- QUAN TRỌNG: THÊM DẤU / Ở CUỐI CÙNG ---
            "databaseURL": "https://lithe-catbird-476301-p4-default-rtdb.asia-southeast1.firebasedatabase.app/"
        }

        try:
            self.firebase = pyrebase.initialize_app(config)
            self.auth = self.firebase.auth()
            self.db = self.firebase.database()
            print(f"✅ Firebase: Kết nối tới {config['databaseURL']}")
        except Exception as e:
            print(f"❌ Lỗi kết nối Firebase: {e}")
            self.auth = None; self.db = None

    # --- AUTHENTICATION ---
    def login(self, email, password):
        if not self.auth: return False, "Mất kết nối mạng."
        try:
            user = self.auth.sign_in_with_email_and_password(email, password)
            local_id = user['localId']
            
            # Thử đọc DB để xem kết nối thông chưa
            try:
                db_info = self.db.child("users").child(local_id).get().val()
            except Exception as db_err:
                print(f"⚠️ Lỗi đọc DB khi login: {db_err}")
                db_info = None

            if db_info:
                user['db_data'] = db_info
            else:
                # Tạo dữ liệu mặc định
                default_data = self._create_default_data(email, "Người dùng")
                try:
                    self.db.child("users").child(local_id).set(default_data)
                    print(f"✅ Đã khởi tạo data cho User ID: {local_id}")
                except Exception as e:
                    print(f"❌ Không thể ghi data khởi tạo: {e}")
                    
                user['db_data'] = default_data
            return True, user
        except Exception as e:
            return False, self._parse_error(e)

    def register(self, email, password, fullname):
        if not self.auth: return False, "Mất kết nối mạng."
        try:
            user = self.auth.create_user_with_email_and_password(email, password)
            local_id = user['localId']
            user_data = self._create_default_data(email, fullname)
            
            # Ghi DB
            self.db.child("users").child(local_id).set(user_data)
            user['db_data'] = user_data
            return True, user
        except Exception as e:
            return False, self._parse_error(e)

    def reset_password(self, email):
        if not self.auth: return False, "Chưa kết nối."
        try:
            self.auth.send_password_reset_email(email)
            return True, "Đã gửi email đặt lại mật khẩu."
        except Exception as e:
            return False, self._parse_error(e)

    # --- DATABASE ---
    def log_alert(self, uid, level, message):
        if not self.db: return
        data = {
            "timestamp": int(time.time()),
            "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": level,
            "message": message
        }
        try:
            # Thêm print để debug kết quả trả về từ server
            result = self.db.child("users").child(uid).child("history").push(data)
            print(f"✅ Server phản hồi: Đã lưu log {result['name']}")
        except Exception as e:
            print(f"❌ Lỗi LƯU LOG mạng: {e}")

    def get_history(self, uid):
        if not self.db: return {}
        try:
            data = self.db.child("users").child(uid).child("history").order_by_child("timestamp").limit_to_last(50).get().val()
            return data if data else {}
        except Exception as e:
            print(f"Lỗi lấy lịch sử: {e}")
            return {}

    def clear_history(self, uid):
        if not self.db: return False
        try:
            self.db.child("users").child(uid).child("history").remove()
            return True
        except: return False

    def update_user_info(self, uid, fullname):
        if not self.db: return False
        try:
            self.db.child("users").child(uid).update({"fullname": fullname})
            return True
        except: return False

    def update_settings(self, uid, settings_dict):
        if not self.db: return False
        try:
            self.db.child("users").child(uid).child("settings").update(settings_dict)
            return True
        except: return False

    # --- UTILS ---
    def _parse_error(self, e):
        try:
            error_json = json.loads(e.args[1])
            msg = error_json['error']['message']
            if "EMAIL_NOT_FOUND" in msg: return "Email không tồn tại."
            if "INVALID_PASSWORD" in msg: return "Sai mật khẩu."
            if "EMAIL_EXISTS" in msg: return "Email đã tồn tại."
            return msg
        except: return "Lỗi không xác định."

    def _create_default_data(self, email, fullname):
        return {
            "email": email, "fullname": fullname, "created_at": int(time.time()),
            "settings": {"yawn_threshold": 3, "eye_time": 2.0, "head_angle": 20}
        }
        
    def login_with_google(self, id_token):
        """Đổi Google ID Token lấy Firebase User"""
        # API Key lấy từ config
        api_key = self.firebase.api_key
        request_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={api_key}"
        
        payload = {
            "postBody": f"id_token={id_token}&providerId=google.com",
            "requestUri": "http://localhost",
            "returnIdpCredential": True,
            "returnSecureToken": True
        }

        try:
            # Gửi yêu cầu lên Google
            response = requests.post(request_url, data=payload)
            data = response.json()

            if "error" in data:
                return False, data['error']['message']

            # Lấy thông tin user trả về
            local_id = data['localId']
            email = data['email']
            fullname = data.get('displayName', email) # Lấy tên Google, nếu ko có thì lấy email
            id_token_firebase = data['idToken']

            # Tạo cấu trúc user giống như đăng nhập thường
            user = {
                'localId': local_id,
                'email': email,
                'idToken': id_token_firebase
            }

            # Kiểm tra xem user này đã có trong Database chưa
            db_info = self.db.child("users").child(local_id).get().val()
            
            if db_info:
                user['db_data'] = db_info
            else:
                # Nếu chưa (lần đầu login Google), tạo dữ liệu mới
                default_data = self._create_default_data(email, fullname)
                self.db.child("users").child(local_id).set(default_data)
                user['db_data'] = default_data

            return True, user

        except Exception as e:
            return False, f"Lỗi kết nối API: {e}"