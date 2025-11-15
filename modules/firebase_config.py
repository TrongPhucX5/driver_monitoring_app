import pyrebase
import logging 

auth = None
db = None

config = {
    "apiKey": "AIzaSyC3g4ovxA3cADCqEbx7jZ2052whq5Rctoo",
    "authDomain": "lithe-catbird-476301-p4.firebaseapp.com",
    "projectId": "lithe-catbird-476301-p4",
    "storageBucket": "lithe-catbird-476301-p4.firebasestorage.app",
    "databaseURL": "https://lithe-catbird-476301-p4-default-rtdb.asia-southeast1.firebasedatabase.app"
}

try:
    # 1. Khởi tạo ứng dụng Firebase
    firebase = pyrebase.initialize_app(config)
    
    # 2. Lấy dịch vụ Authentication (Đăng nhập)
    auth = firebase.auth()
    
    # 3. Lấy dịch vụ REALTIME DATABASE (không phải firestore)
    db = firebase.database()
    
    logging.warning("Firebase Config: Khởi tạo thành công! (auth và db đã sẵn sàng)")

except Exception as e:
    logging.error(f"Firebase Config: LỖI KHI KHỞI TẠO: {e}")
    logging.error("Vui lòng kiểm tra lại 'databaseURL' trong config và đảm bảo đã 'pip install pyrebase4'")