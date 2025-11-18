"""
ui/login_window.py
Màn hình Đăng nhập & Đăng ký (Rounded UI + Google)
Đã sửa lỗi SyntaxError ở hàm save_session
"""
import sys
import json
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from modules.firebase_service import FirebaseService

# Import module Google
try:
    from modules.google_auth import GoogleAuthManager
except ImportError:
    GoogleAuthManager = None

class LoginWindow(QtWidgets.QWidget):
    loginSuccess = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Driver Monitor - Account")
        self.setFixedSize(1000, 650)
        
        # --- 1. CẤU HÌNH CỬA SỔ KHÔNG VIỀN & TRONG SUỐT ---
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        self.firebase = FirebaseService()
        self.google_manager = GoogleAuthManager() if GoogleAuthManager else None
        self.is_login_mode = True 

        # --- LAYOUT CHÍNH ---
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.container = QtWidgets.QFrame()
        self.container.setObjectName("Container")
        self.container.setStyleSheet("""
            QFrame#Container {
                background-color: #1e1e1e;
                border-radius: 20px;
                border: 1px solid #333;
            }
        """)
        main_layout.addWidget(self.container)
        
        content_layout = QtWidgets.QHBoxLayout(self.container)
        content_layout.setContentsMargins(0, 0, 0, 0); content_layout.setSpacing(0)

        # === CỘT TRÁI ===
        self.left_panel = QtWidgets.QFrame()
        self.left_panel.setStyleSheet("""
            background-color: #0bc3ab;
            border-top-left-radius: 20px;
            border-bottom-left-radius: 20px;
        """)
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setAlignment(QtCore.Qt.AlignCenter)

        lbl_welcome = QtWidgets.QLabel("Chào mừng bạn\nđến với\nDriver Monitoring")
        lbl_welcome.setAlignment(QtCore.Qt.AlignCenter)
        lbl_welcome.setStyleSheet("font-family: 'Segoe UI', Arial; font-size: 36px; color: white; font-weight: bold; line-height: 1.5;")
        left_layout.addWidget(lbl_welcome)
        content_layout.addWidget(self.left_panel, 45)

        # === CỘT PHẢI ===
        self.right_panel = QtWidgets.QFrame()
        self.right_panel.setStyleSheet("""
            background-color: #1e1e1e;
            border-top-right-radius: 20px;
            border-bottom-right-radius: 20px;
        """)
        right_layout = QtWidgets.QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(50, 20, 50, 40)
        right_layout.setSpacing(15)
        
        # Nút Đóng (X)
        title_bar = QtWidgets.QHBoxLayout(); title_bar.addStretch()
        self.btn_close = QtWidgets.QPushButton("✕"); self.btn_close.setFixedSize(30, 30); self.btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton { color: #aaa; border: none; font-size: 16px; background: transparent; font-weight: bold;}
            QPushButton:hover { color: white; background-color: #e74c3c; border-radius: 15px; }
        """)
        self.btn_close.clicked.connect(self.close)
        title_bar.addWidget(self.btn_close)
        right_layout.addLayout(title_bar); right_layout.addStretch()

        # Tab
        top_bar = QtWidgets.QHBoxLayout()
        self.btn_sw_signin = QtWidgets.QPushButton("Sign In"); self.btn_sw_signup = QtWidgets.QPushButton("Sign Up")
        self.btn_style_active = "color: white; background-color: #0bc3ab; border: 1px solid #0bc3ab; border-radius: 20px; padding: 8px 25px; font-weight: bold; font-size: 14px;"
        self.btn_style_inactive = "color: #888; background: transparent; border: 1px solid #555; border-radius: 20px; padding: 8px 25px; font-size: 14px;"
        self.btn_sw_signin.clicked.connect(self.switch_to_login)
        self.btn_sw_signup.clicked.connect(self.switch_to_register)
        top_bar.addStretch(); top_bar.addWidget(self.btn_sw_signin); top_bar.addWidget(self.btn_sw_signup); top_bar.addStretch()
        right_layout.addLayout(top_bar)
        
        # Tiêu đề
        self.lbl_title = QtWidgets.QLabel("ĐĂNG NHẬP"); self.lbl_title.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_title.setStyleSheet("color: white; font-size: 28px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;")
        right_layout.addWidget(self.lbl_title)

        # Inputs
        input_style = """
            QLineEdit { background-color: #2b2b2b; color: white; border: 1px solid #555; border-radius: 8px; padding: 12px; font-size: 16px; }
            QLineEdit:focus { border: 1px solid #0bc3ab; }
        """
        container_style = "background-color: #2b2b2b; border: 1px solid #555; border-radius: 8px;"
        
        self.txt_name = QtWidgets.QLineEdit(); self.txt_name.setPlaceholderText("Họ và Tên"); self.txt_name.setStyleSheet(input_style)
        self.txt_email = QtWidgets.QLineEdit(); self.txt_email.setPlaceholderText("Email"); self.txt_email.setStyleSheet(input_style)
        right_layout.addWidget(self.txt_name); right_layout.addWidget(self.txt_email)

        # Password
        self.pass_container = QtWidgets.QFrame(); self.pass_container.setStyleSheet(container_style)
        pass_layout = QtWidgets.QHBoxLayout(self.pass_container); pass_layout.setContentsMargins(2, 2, 10, 2)
        self.txt_pass = QtWidgets.QLineEdit(); self.txt_pass.setPlaceholderText("Mật khẩu"); self.txt_pass.setEchoMode(QtWidgets.QLineEdit.Password); self.txt_pass.setStyleSheet("border: none; background: transparent; color: white; padding: 10px; font-size: 16px;")
        self.btn_eye = QtWidgets.QToolButton(); self.btn_eye.setText("👁"); self.btn_eye.setCursor(QtCore.Qt.PointingHandCursor); self.btn_eye.setStyleSheet("color: #888; border: none; background: transparent; font-size: 18px;")
        self.btn_eye.clicked.connect(lambda: self.toggle_password(self.txt_pass, self.btn_eye))
        pass_layout.addWidget(self.txt_pass); pass_layout.addWidget(self.btn_eye)
        right_layout.addWidget(self.pass_container)

        # Confirm Pass
        self.confirm_container = QtWidgets.QFrame(); self.confirm_container.setStyleSheet(container_style)
        confirm_layout = QtWidgets.QHBoxLayout(self.confirm_container); confirm_layout.setContentsMargins(2, 2, 10, 2)
        self.txt_confirm = QtWidgets.QLineEdit(); self.txt_confirm.setPlaceholderText("Nhập lại mật khẩu"); self.txt_confirm.setEchoMode(QtWidgets.QLineEdit.Password); self.txt_confirm.setStyleSheet("border: none; background: transparent; color: white; padding: 10px; font-size: 16px;")
        self.btn_eye_confirm = QtWidgets.QToolButton(); self.btn_eye_confirm.setText("👁"); self.btn_eye_confirm.setCursor(QtCore.Qt.PointingHandCursor); self.btn_eye_confirm.setStyleSheet("color: #888; border: none; background: transparent; font-size: 18px;")
        self.btn_eye_confirm.clicked.connect(lambda: self.toggle_password(self.txt_confirm, self.btn_eye_confirm))
        confirm_layout.addWidget(self.txt_confirm); confirm_layout.addWidget(self.btn_eye_confirm)
        right_layout.addWidget(self.confirm_container)

        # Options
        row_options = QtWidgets.QHBoxLayout()
        self.chk_remember = QtWidgets.QCheckBox("Ghi nhớ đăng nhập"); self.chk_remember.setStyleSheet("color: white; font-size: 14px;"); self.chk_remember.setChecked(True)
        self.btn_forgot = QtWidgets.QPushButton("Quên mật khẩu?"); self.btn_forgot.setCursor(QtCore.Qt.PointingHandCursor); self.btn_forgot.setStyleSheet("border: none; background: transparent; color: #0bc3ab; font-style: italic; font-size: 14px;")
        self.btn_forgot.clicked.connect(self.action_forgot_password)
        row_options.addWidget(self.chk_remember); row_options.addStretch(); row_options.addWidget(self.btn_forgot)
        right_layout.addLayout(row_options)

        # Button Login
        self.btn_action = QtWidgets.QPushButton("ĐĂNG NHẬP"); self.btn_action.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_action.setStyleSheet("""
            QPushButton { background-color: #0bc3ab; color: white; font-weight: bold; padding: 15px; border-radius: 25px; font-size: 18px; margin-top: 5px; }
            QPushButton:hover { background-color: #09a38f; }
        """)
        self.btn_action.clicked.connect(self.handle_auth_action)
        right_layout.addWidget(self.btn_action)

        # Button Google
        self.btn_google = QtWidgets.QPushButton("  Đăng nhập bằng Google"); self.btn_google.setCursor(QtCore.Qt.PointingHandCursor)
        if os.path.exists("assets/images/google.png"):
            self.btn_google.setIcon(QtGui.QIcon("assets/images/google.png")); self.btn_google.setIconSize(QtCore.QSize(24, 24))
        self.btn_google.setStyleSheet("""
            QPushButton { background-color: white; color: #5f6368; font-weight: bold; font-family: 'Segoe UI'; padding: 12px; border-radius: 25px; font-size: 15px; margin-top: 10px; border: 1px solid #dadce0; }
            QPushButton:hover { background-color: #f8f9fa; border: 1px solid #d2e3fc; color: #1a73e8; }
            QPushButton:pressed { background-color: #e8f0fe; }
        """)
        self.btn_google.clicked.connect(self.handle_google_login)
        right_layout.addWidget(self.btn_google)

        right_layout.addStretch()
        content_layout.addWidget(self.right_panel, 55)
        
        self.switch_to_login()
        self.load_saved_data()

    # --- LOGIC ---
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton: self.drag_pos = event.globalPos() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton: self.move(event.globalPos() - self.drag_pos); event.accept()

    def load_saved_data(self):
        if os.path.exists("session.json"):
            try:
                with open("session.json", "r") as f:
                    data = json.load(f)
                    self.txt_email.setText(data.get("email", ""))
                    self.txt_pass.setText(data.get("password", ""))
            except: pass

    def switch_to_login(self):
        self.is_login_mode = True; self.lbl_title.setText("ĐĂNG NHẬP"); self.btn_action.setText("ĐĂNG NHẬP")
        self.btn_sw_signin.setStyleSheet(self.btn_style_active); self.btn_sw_signup.setStyleSheet(self.btn_style_inactive)
        self.txt_name.setVisible(False); self.confirm_container.setVisible(False); self.btn_forgot.setVisible(True); self.chk_remember.setVisible(True); self.btn_google.setVisible(True)

    def switch_to_register(self):
        self.is_login_mode = False; self.lbl_title.setText("TẠO TÀI KHOẢN"); self.btn_action.setText("ĐĂNG KÝ NGAY")
        self.btn_sw_signup.setStyleSheet(self.btn_style_active); self.btn_sw_signin.setStyleSheet(self.btn_style_inactive)
        self.txt_name.setVisible(True); self.confirm_container.setVisible(True); self.btn_forgot.setVisible(False); self.chk_remember.setVisible(False); self.btn_google.setVisible(False)

    def toggle_password(self, line_edit, button):
        if line_edit.echoMode() == QtWidgets.QLineEdit.Password: line_edit.setEchoMode(QtWidgets.QLineEdit.Normal); button.setStyleSheet("color: #0bc3ab; border: none; background: transparent; font-size: 18px;")
        else: line_edit.setEchoMode(QtWidgets.QLineEdit.Password); button.setStyleSheet("color: #888; border: none; background: transparent; font-size: 18px;")

    def handle_auth_action(self):
        email = self.txt_email.text().strip(); password = self.txt_pass.text().strip()
        if not email or not password: return QtWidgets.QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng điền đầy đủ thông tin.")
        self.btn_action.setEnabled(False); self.btn_action.setText("Đang xử lý..."); QtWidgets.QApplication.processEvents()

        if self.is_login_mode:
            success, result = self.firebase.login(email, password)
            if success:
                if self.chk_remember.isChecked(): self.save_session(email, password)
                self.loginSuccess.emit(result); self.close()
            else: QtWidgets.QMessageBox.warning(self, "Lỗi Đăng nhập", str(result))
        else:
            fullname = self.txt_name.text().strip(); confirm_pass = self.txt_confirm.text().strip()
            if not fullname: self.btn_action.setEnabled(True); return QtWidgets.QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập Họ tên.")
            if password != confirm_pass: self.btn_action.setEnabled(True); return QtWidgets.QMessageBox.warning(self, "Mật khẩu", "Mật khẩu không khớp!")
            success, result = self.firebase.register(email, password, fullname)
            if success: QtWidgets.QMessageBox.information(self, "Thành công", f"Đã tạo tài khoản cho {fullname}!\nVui lòng đăng nhập."); self.txt_pass.clear(); self.txt_confirm.clear(); self.switch_to_login()
            else: QtWidgets.QMessageBox.warning(self, "Lỗi Đăng ký", str(result))
        self.reset_button()

    def handle_google_login(self):
        if not self.google_manager: return QtWidgets.QMessageBox.critical(self, "Lỗi", "Chưa cài đặt module Google Auth!")
        self.btn_google.setEnabled(False); self.btn_google.setText("Đang mở trình duyệt...")
        success, result = self.google_manager.login()
        if success:
            self.btn_google.setText("Đang xác thực...")
            fb_success, fb_result = self.firebase.login_with_google(result)
            if fb_success: self.loginSuccess.emit(fb_result); self.close()
            else: QtWidgets.QMessageBox.warning(self, "Lỗi Firebase", str(fb_result))
        else:
            if "client_secret" in str(result): QtWidgets.QMessageBox.critical(self, "Thiếu File", "Chưa có file 'client_secret.json'!")
            else: QtWidgets.QMessageBox.warning(self, "Lỗi Google", str(result))
        self.btn_google.setEnabled(True); self.btn_google.setText("  Đăng nhập bằng Google")

    def reset_button(self): self.btn_action.setEnabled(True); self.btn_action.setText("ĐĂNG NHẬP" if self.is_login_mode else "ĐĂNG KÝ NGAY")
    def action_forgot_password(self):
        email = self.txt_email.text().strip()
        if not email: return QtWidgets.QMessageBox.warning(self, "Nhắc nhở", "Nhập Email vào ô trên trước.")
        if QtWidgets.QMessageBox.question(self, "Xác nhận", f"Gửi email reset tới: {email}?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            success, msg = self.firebase.reset_password(email)
            if success: QtWidgets.QMessageBox.information(self, "Đã gửi", msg)
            else: QtWidgets.QMessageBox.warning(self, "Lỗi", str(msg))

    # --- HÀM SỬA LỖI SYNTAX ---
    def save_session(self, email, password):
        try:
            with open("session.json", "w") as f:
                json.dump({"email": email, "password": password}, f)
        except: pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = LoginWindow(); window.show(); sys.exit(app.exec_())