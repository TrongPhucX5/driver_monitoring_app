"""
main.py - Điểm khởi động ứng dụng
Kết nối Login và Main, xử lý luồng Đăng xuất
"""
import sys
import json
import os
from PyQt5.QtWidgets import QApplication

# Import 2 màn hình
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

def start_app():
    app = QApplication(sys.argv)
    
    # Biến lưu cửa sổ hiện tại
    current_window = None

    def show_login():
        nonlocal current_window
        if current_window:
            current_window.close()
        
        login_win = LoginWindow()
        login_win.loginSuccess.connect(show_main)
        current_window = login_win
        login_win.show()

    def show_main(user_data):
        nonlocal current_window
        if current_window:
            current_window.close()
            
        main_win = MainWindow(user_info=user_data)
        # Kết nối tín hiệu Đăng xuất -> Quay lại Login
        main_win.logoutSignal.connect(show_login)
        
        current_window = main_win
        main_win.show()

    # --- LOGIC TỰ ĐỘNG ĐĂNG NHẬP ---
    session_file = "session.json"
    user_data_auto = None
    
    if os.path.exists(session_file):
        try:
            from modules.firebase_service import FirebaseService
            with open(session_file, "r") as f: creds = json.load(f)
            fb = FirebaseService()
            ok, res = fb.login(creds['email'], creds['password'])
            if ok: user_data_auto = res
        except: pass

    if user_data_auto:
        show_main(user_data_auto)
    else:
        show_login()

    sys.exit(app.exec_())

if __name__ == "__main__":
    start_app()