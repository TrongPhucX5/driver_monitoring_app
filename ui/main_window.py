"""
ui/main_window.py
Giao diện chính (Final) - NO POPUPS
- Bỏ thông báo "Thành công" khi Lưu tên, Đổi pass, Đăng xuất.
- Trải nghiệm mượt mà, bấm là chạy.
"""
import sys
import cv2
import numpy as np
import time
import os
import threading
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QStackedWidget, QFrame, 
    QFormLayout, QCheckBox, QComboBox, QSlider, QSpinBox, QLineEdit,
    QSpacerItem, QSizePolicy, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)

try: import winsound
except: winsound = None

from modules.camera import VideoCaptureThread
from modules.firebase_service import FirebaseService
from modules.email_alert import EmailAlertSystem

class MainWindow(QMainWindow):
    logoutSignal = pyqtSignal()

    def __init__(self, user_info=None):
        super().__init__()
        self.user_info = user_info
        self.firebase = FirebaseService()
        self.email_system = EmailAlertSystem()
        
        self.setWindowTitle("Hệ thống Giám sát Lái xe Thông minh")
        self.setGeometry(50, 50, 1200, 800)
        
        self.video_thread = None
        self.current_theme = "dark"
        self.last_alert_time = 0 
        self.last_email_time = 0
        self.is_playing_sound = False

        # --- 1. CẤU HÌNH MẶC ĐỊNH ---
        self.config_yawn_threshold = 3
        self.config_eye_time = 2.0
        self.config_head_angle = 20
        self.config_audio_alert = "Tiếng Bíp (Mặc định)"
        self.config_email_sos = ""
        self.display_name = "Khách"
        
        # --- 2. LOAD DỮ LIỆU TỪ FIREBASE ---
        if self.user_info:
            if 'db_data' in self.user_info:
                self.display_name = self.user_info['db_data'].get('fullname', self.user_info.get('email'))
                settings = self.user_info['db_data'].get('settings', {})
                self.config_yawn_threshold = int(settings.get('yawn_threshold', 3))
                self.config_eye_time = float(settings.get('eye_time', 2.0))
                self.config_head_angle = int(settings.get('head_angle', 20))
                self.config_audio_alert = settings.get('audio_alert', "Tiếng Bíp (Mặc định)")
                self.config_email_sos = settings.get('email_sos', "")
            else:
                self.display_name = self.user_info.get('email', 'User')

        self.initUI()
        self.apply_styles()
        self.show_monitoring_page()

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- SIDEBAR ---
        sidebar = QWidget(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(240)
        sb_layout = QVBoxLayout(sidebar); sb_layout.setContentsMargins(20, 40, 20, 40); sb_layout.setSpacing(15)
        
        lbl_logo = QLabel("DRIVER\nGUARD"); lbl_logo.setObjectName("SidebarTitle"); lbl_logo.setAlignment(Qt.AlignCenter)
        
        self.btn_mon = self.create_nav_btn("📺  Giám sát", self.show_monitoring_page)
        self.btn_his = self.create_nav_btn("📜  Lịch sử", self.show_history_page)
        self.btn_rep = self.create_nav_btn("📊  Báo cáo", self.show_report_page)
        self.btn_acc = self.create_nav_btn("👤  Tài khoản", self.show_account_page)
        self.btn_set = self.create_nav_btn("⚙️  Cài đặt", self.show_settings_page)

        sb_layout.addWidget(lbl_logo); sb_layout.addSpacing(30)
        sb_layout.addWidget(self.btn_mon); sb_layout.addWidget(self.btn_his)
        sb_layout.addWidget(self.btn_rep); sb_layout.addWidget(self.btn_acc)
        sb_layout.addStretch(); sb_layout.addWidget(self.btn_set)
        main_layout.addWidget(sidebar)

        # --- MAIN CONTENT ---
        content_area = QWidget(); content_area.setObjectName("MainArea")
        c_layout = QVBoxLayout(content_area)
        
        # Header
        header_layout = QHBoxLayout()
        self.lbl_status = QLabel("TRẠNG THÁI: AN TOÀN 🟢")
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 16px; color: #0bc3ab;")
        
        self.lbl_header = QLabel(f"Xin chào, {self.display_name}")
        self.lbl_header.setObjectName("HeaderLabel")
        
        header_layout.addWidget(self.lbl_status); header_layout.addStretch(); header_layout.addWidget(self.lbl_header)
        c_layout.addLayout(header_layout)

        # Stacked Widget
        self.stacked_widget = QStackedWidget()
        self.page_mon = self.create_monitor_page()
        self.page_his = self.create_history_page()
        self.page_rep = self.create_report_page()
        self.page_acc = self.create_account_page()
        self.page_set = self.create_settings_page()
        
        self.stacked_widget.addWidget(self.page_mon)
        self.stacked_widget.addWidget(self.page_his)
        self.stacked_widget.addWidget(self.page_rep)
        self.stacked_widget.addWidget(self.page_acc)
        self.stacked_widget.addWidget(self.page_set)
        
        c_layout.addWidget(self.stacked_widget)

        # Status Bar
        self.status_bar = QLabel("Sẵn sàng")
        self.status_bar.setObjectName("StatusBar")
        self.status_bar.setFixedHeight(35)
        self.status_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        c_layout.addWidget(self.status_bar)

        main_layout.addWidget(content_area)

    def create_nav_btn(self, text, func):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor); btn.clicked.connect(func)
        btn.setObjectName("MenuButton")
        return btn

    # --- ÂM THANH ---
    def play_sound_async(self, frequency=None, duration=None, wav_file=None):
        if self.is_playing_sound: return
        def run_sound():
            self.is_playing_sound = True
            try:
                if wav_file: winsound.PlaySound(wav_file, winsound.SND_FILENAME)
                elif frequency: winsound.Beep(frequency, duration)
            except: pass
            self.is_playing_sound = False
        threading.Thread(target=run_sound, daemon=True).start()

    # --- CÁC TRANG ---
    def create_monitor_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        self.video_label = QLabel("Camera chưa bật")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: #000; border: 2px solid #333; border-radius: 10px;")
        
        opts_layout = QHBoxLayout()
        self.chk_mesh = QCheckBox("Hiện lưới (Debug)")
        self.chk_mesh.toggled.connect(self.toggle_mesh_display)
        self.chk_sunglasses = QCheckBox("😎 Đeo kính râm")
        self.chk_sunglasses.toggled.connect(self.toggle_sunglasses_mode)
        opts_layout.addWidget(self.chk_mesh); opts_layout.addSpacing(20); opts_layout.addWidget(self.chk_sunglasses); opts_layout.addStretch()

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶ BẮT ĐẦU"); self.btn_start.setObjectName("StartButton"); self.btn_start.clicked.connect(self.start_camera)
        self.btn_stop = QPushButton("⏹ DỪNG"); self.btn_stop.setObjectName("StopButton"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_camera)
        btn_layout.addStretch(); btn_layout.addWidget(self.btn_start); btn_layout.addSpacing(20); btn_layout.addWidget(self.btn_stop); btn_layout.addStretch()

        layout.addWidget(self.video_label); layout.addLayout(opts_layout); layout.addLayout(btn_layout)
        return page

    def create_history_page(self):
        page = QWidget(); layout = QVBoxLayout(page)
        header = QHBoxLayout()
        lbl = QLabel("LỊCH SỬ CẢNH BÁO"); lbl.setObjectName("FormTitle")
        btn_refresh = QPushButton("🔄 Làm mới"); btn_refresh.setFixedWidth(120); btn_refresh.clicked.connect(self.load_history)
        btn_clear = QPushButton("🗑️ Xóa tất cả"); btn_clear.setFixedWidth(120); btn_clear.setObjectName("StopButton"); btn_clear.clicked.connect(self.action_clear_history)
        header.addWidget(lbl); header.addStretch(); header.addWidget(btn_refresh); header.addWidget(btn_clear)
        
        self.table_his = QTableWidget(); self.table_his.setColumnCount(3)
        self.table_his.setHorizontalHeaderLabels(["Thời gian", "Cấp độ", "Nội dung"])
        self.table_his.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addLayout(header); layout.addWidget(self.table_his)
        return page

    def load_history(self):
        if not self.user_info: return
        uid = self.user_info['localId']
        history_data = self.firebase.get_history(uid)
        self.table_his.setRowCount(0)
        if history_data:
            sorted_items = sorted(history_data.values(), key=lambda x: x['timestamp'], reverse=True)
            for row_idx, item in enumerate(sorted_items):
                self.table_his.insertRow(row_idx)
                self.table_his.setItem(row_idx, 0, QTableWidgetItem(item.get('time_str', '')))
                lvl = item.get('level', 0)
                lvl_str = "SOS 🔴🔴" if lvl == 4 else ("Nguy hiểm 🔴" if lvl == 3 else ("Cảnh báo 🟠" if lvl == 2 else "Nhắc nhở 🟡"))
                self.table_his.setItem(row_idx, 1, QTableWidgetItem(lvl_str))
                self.table_his.setItem(row_idx, 2, QTableWidgetItem(item.get('message', '')))

    def action_clear_history(self):
        if not self.user_info: return
        if QMessageBox.question(self, 'Xác nhận', "Xóa toàn bộ lịch sử?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if self.firebase.clear_history(self.user_info['localId']):
                self.table_his.setRowCount(0)
                self.status_bar.setText("✅ Đã xóa sạch lịch sử")
                self.load_report_data()

    def create_report_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setAlignment(Qt.AlignCenter)
        container = QFrame(); container.setObjectName("FormContainer"); container.setFixedWidth(600)
        lbl = QLabel("BÁO CÁO HÔM NAY"); lbl.setObjectName("FormTitle"); lbl.setAlignment(Qt.AlignCenter)
        btn_ref = QPushButton("🔄 Cập nhật"); btn_ref.clicked.connect(self.load_report_data)
        
        self.stats_layout = QFormLayout(); self.stats_layout.setSpacing(20)
        self.lbl_score = QLabel("..."); self.lbl_score.setObjectName("ScoreLabel")
        self.lbl_count_lv3 = QLabel("..."); self.lbl_advice = QLabel("..."); self.lbl_advice.setWordWrap(True)
        
        self.stats_layout.addRow("Điểm an toàn:", self.lbl_score)
        self.stats_layout.addRow("Số lần ngủ gật (Cấp 3):", self.lbl_count_lv3)
        self.stats_layout.addRow("Đánh giá:", self.lbl_advice)
        vbox = QVBoxLayout(container); vbox.addWidget(lbl); vbox.addWidget(btn_ref); vbox.addLayout(self.stats_layout)
        layout.addWidget(container); return page

    def load_report_data(self):
        if not self.user_info: return
        uid = self.user_info['localId']
        history = self.firebase.get_history(uid)
        if not history:
            self.lbl_score.setText("100/100"); self.lbl_count_lv3.setText("0 lần"); self.lbl_advice.setText("Chưa có dữ liệu.")
            return
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_items = [item for item in history.values() if item.get('time_str', '').startswith(today_str)]
        count_lv3 = sum(1 for x in today_items if x.get('level') >= 3)
        count_lv2 = sum(1 for x in today_items if x.get('level') == 2)
        score = max(0, 100 - (count_lv3 * 15) - (count_lv2 * 5))
        self.lbl_score.setText(f"{score}/100")
        color = "#0bc3ab" if score >= 80 else ("orange" if score >= 50 else "red")
        self.lbl_score.setStyleSheet(f"font-size: 40px; color: {color}; font-weight: bold;")
        self.lbl_count_lv3.setText(f"{count_lv3} lần")
        if score == 100: self.lbl_advice.setText("Tuyệt vời! Lái xe an toàn.")
        elif score > 60: self.lbl_advice.setText("Khá tốt. Chú ý nghỉ ngơi.")
        else: self.lbl_advice.setText("CẢNH BÁO: Bạn quá buồn ngủ! Dừng lái xe ngay.")

    def create_account_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setAlignment(Qt.AlignTop)
        
        header_frame = QFrame(); header_frame.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header_frame)
        first_letter = self.display_name[0].upper() if self.display_name else "U"
        self.avatar = QLabel(first_letter); self.avatar.setFixedSize(80, 80); self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setStyleSheet("background-color: #0bc3ab; color: white; font-size: 40px; font-weight: bold; border-radius: 40px; border: 2px solid white;")
        info_layout = QVBoxLayout()
        lbl_name = QLabel(self.display_name); lbl_name.setStyleSheet("font-size: 24px; font-weight: bold;")
        lbl_role = QLabel("Tài xế"); lbl_role.setStyleSheet("color: #aaa; font-size: 14px; font-style: italic;")
        info_layout.addWidget(lbl_name); info_layout.addWidget(lbl_role)
        header_layout.addStretch(); header_layout.addWidget(self.avatar); header_layout.addSpacing(15); header_layout.addLayout(info_layout); header_layout.addStretch()

        stats_frame = QFrame(); stats_layout = QHBoxLayout(stats_frame); stats_layout.setSpacing(20)
        score = "100"; alerts = "0"
        if self.user_info:
            hist = self.firebase.get_history(self.user_info['localId'])
            if hist:
                today = datetime.now().strftime("%Y-%m-%d")
                today_items = [i for i in hist.values() if i.get('time_str', '').startswith(today)]
                cnt = sum(1 for x in today_items if x.get('level') >= 3)
                alerts = str(cnt); score = str(max(0, 100 - cnt*10))
        stats_layout.addStretch()
        stats_layout.addWidget(self.create_stat_card("🛡️ Điểm an toàn", f"{score}/100", "#27ae60"))
        stats_layout.addWidget(self.create_stat_card("⚠️ Cảnh báo hôm nay", f"{alerts} lần", "#e74c3c"))
        stats_layout.addStretch()

        form_container = QFrame(); form_container.setObjectName("FormContainer"); form_container.setFixedWidth(500)
        form_layout = QVBoxLayout(form_container); form_layout.setSpacing(15)
        self.txt_acc_email = QLineEdit(); self.txt_acc_email.setText(self.user_info.get('email', ''))
        self.txt_acc_email.setReadOnly(True); self.txt_acc_email.setObjectName("ReadOnlyInput")
        self.txt_acc_name = QLineEdit(); self.txt_acc_name.setText(self.display_name); self.txt_acc_name.setPlaceholderText("Nhập tên hiển thị")
        form_layout.addWidget(QLabel("Email:")); form_layout.addWidget(self.txt_acc_email)
        form_layout.addWidget(QLabel("Họ và Tên:")); form_layout.addWidget(self.txt_acc_name)
        btn_save = QPushButton("💾 Cập nhật tên"); btn_save.setObjectName("StartButton"); btn_save.clicked.connect(self.save_account_info)
        btn_pass = QPushButton("🔑 Đổi mật khẩu"); btn_pass.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        btn_pass.setCursor(Qt.PointingHandCursor); btn_pass.clicked.connect(self.request_change_password)
        form_layout.addSpacing(10); form_layout.addWidget(btn_save); form_layout.addWidget(btn_pass)

        # FOOTER
        footer_layout = QHBoxLayout()
        btn_theme = QCheckBox("Giao diện Sáng"); btn_theme.toggled.connect(self.toggle_theme)
        btn_logout = QPushButton("Đăng xuất", objectName="StopButton"); btn_logout.clicked.connect(self.perform_logout)
        footer_layout.addWidget(btn_theme); footer_layout.addStretch(); footer_layout.addWidget(btn_logout)

        layout.addSpacing(20); layout.addWidget(header_frame); layout.addWidget(stats_frame); layout.addSpacing(20); layout.addWidget(form_container, alignment=Qt.AlignCenter); layout.addSpacing(20); layout.addLayout(footer_layout); layout.addStretch()
        return page

    def create_stat_card(self, title, value, color):
        card = QFrame(); card.setFixedSize(180, 90); card.setStyleSheet(f"background-color: {color}; border-radius: 10px;")
        vbox = QVBoxLayout(card)
        l_val = QLabel(value); l_val.setStyleSheet("font-size: 24px; font-weight: bold; color: white;")
        l_tit = QLabel(title); l_tit.setStyleSheet("font-size: 13px; color: #f0f0f0;")
        l_val.setAlignment(Qt.AlignCenter); l_tit.setAlignment(Qt.AlignCenter)
        vbox.addWidget(l_val); vbox.addWidget(l_tit)
        return card

    # --- CÁC HÀM LOGIC ĐÃ SỬA (KHÔNG POPUP) ---
    def save_account_info(self):
        new_name = self.txt_acc_name.text().strip()
        if not new_name: return
        if self.firebase.update_user_info(self.user_info['localId'], new_name):
            self.display_name = new_name; self.lbl_header.setText(f"Xin chào, {new_name}"); self.avatar.setText(new_name[0].upper())
            # KHÔNG HIỆN POPUP, CHỈ CẬP NHẬT STATUS BAR
            self.status_bar.setText("✅ Đã cập nhật tên hiển thị")
            QTimer.singleShot(3000, lambda: self.status_bar.setText("Sẵn sàng"))

    def request_change_password(self):
        email = self.user_info.get('email', '')
        # Vẫn nên hỏi 1 lần để tránh bấm nhầm
        if QMessageBox.question(self, 'Xác nhận', f"Gửi email đổi mật khẩu tới {email}?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.firebase.reset_password(email)
            # KHÔNG HIỆN POPUP THÀNH CÔNG
            self.status_bar.setText(f"✅ Đã gửi email đổi mật khẩu tới {email}")
            QTimer.singleShot(3000, lambda: self.status_bar.setText("Sẵn sàng"))

    def perform_logout(self):
        """Xóa session và thoát ngay lập tức"""
        if os.path.exists("session.json"): os.remove("session.json")
        # KHÔNG HIỆN POPUP
        self.close(); self.logoutSignal.emit()

    # =========================================================
    # 5. TRANG CÀI ĐẶT
    # =========================================================
    def create_settings_page(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setAlignment(Qt.AlignCenter)
        container = QFrame(); container.setObjectName("FormContainer"); container.setFixedWidth(500)
        form = QFormLayout(); form.setSpacing(20)

        self.audio_alert_combo = QComboBox(); self.audio_alert_combo.addItems(["Tiếng Bíp (Mặc định)", "Giọng nói cảnh báo", "Tắt âm thanh"])
        self.audio_alert_combo.setCurrentText(self.config_audio_alert)
        form.addRow(QLabel("Âm thanh cảnh báo:"), self.audio_alert_combo)
        self.txt_email_sos = QLineEdit(); self.txt_email_sos.setPlaceholderText("Nhập email nhận cảnh báo SOS"); self.txt_email_sos.setText(self.config_email_sos)
        form.addRow(QLabel("Email SOS:"), self.txt_email_sos)

        self.spin_yawn = QSpinBox(); self.spin_yawn.setRange(1, 10); self.spin_yawn.setValue(self.config_yawn_threshold); self.spin_yawn.setSuffix(" lần"); self.spin_yawn.setMinimumHeight(35)
        self.spin_eye = QSpinBox(); self.spin_eye.setRange(1, 5); self.spin_eye.setValue(int(self.config_eye_time)); self.spin_eye.setSuffix(" giây"); self.spin_eye.setMinimumHeight(35)
        self.spin_head = QSpinBox(); self.spin_head.setRange(10, 60); self.spin_head.setValue(self.config_head_angle); self.spin_head.setSuffix(" độ"); self.spin_head.setMinimumHeight(35)

        form.addRow(QLabel("Ngưỡng ngáp:"), self.spin_yawn); form.addRow(QLabel("Thời gian nhắm mắt:"), self.spin_eye); form.addRow(QLabel("Góc nghiêng đầu:"), self.spin_head)
        btn_save = QPushButton("Lưu & Đồng bộ", objectName="StartButton"); btn_save.setCursor(Qt.PointingHandCursor); btn_save.clicked.connect(self.save_settings)

        vbox = QVBoxLayout(container); vbox.addWidget(QLabel("CÀI ĐẶT", objectName="FormTitle", alignment=Qt.AlignCenter)); vbox.addLayout(form); vbox.addSpacing(30); vbox.addWidget(btn_save)
        layout.addWidget(container); return page

    def save_settings(self):
        """Lưu cài đặt KHÔNG POPUP"""
        self.config_yawn_threshold = self.spin_yawn.value()
        self.config_eye_time = self.spin_eye.value()
        self.config_head_angle = self.spin_head.value()
        self.config_audio_alert = self.audio_alert_combo.currentText()
        self.config_email_sos = self.txt_email_sos.text().strip()
        
        if self.video_thread:
            self.video_thread.update_config({'yawn_threshold': self.config_yawn_threshold, 'eye_time': self.config_eye_time, 'head_angle': self.config_head_angle})
        
        if self.user_info:
            uid = self.user_info['localId']
            new_set = {
                'yawn_threshold': self.config_yawn_threshold, 'eye_time': self.config_eye_time, 
                'head_angle': self.config_head_angle, 'audio_alert': self.config_audio_alert, 'email_sos': self.config_email_sos
            }
            self.firebase.update_settings(uid, new_set)
        
        # THAY POPUP BẰNG STATUS BAR
        self.status_bar.setText("✅ Đã lưu cài đặt và đồng bộ lên Cloud!")
        QTimer.singleShot(3000, lambda: self.status_bar.setText("Sẵn sàng"))

    def show_monitoring_page(self): self.stacked_widget.setCurrentIndex(0); self.update_nav_style(self.btn_mon)
    def show_history_page(self): 
        self.stacked_widget.setCurrentIndex(1); self.load_history(); self.update_nav_style(self.btn_his)
    def show_report_page(self): 
        self.stacked_widget.setCurrentIndex(2); self.load_report_data(); self.update_nav_style(self.btn_rep)
    def show_account_page(self): 
        self.stacked_widget.removeWidget(self.page_acc); self.page_acc = self.create_account_page(); self.stacked_widget.insertWidget(3, self.page_acc); self.stacked_widget.setCurrentIndex(3); self.update_nav_style(self.btn_acc)
    def show_settings_page(self): self.stacked_widget.setCurrentIndex(4); self.update_nav_style(self.btn_set)

    def update_nav_style(self, active_btn):
        for btn in [self.btn_mon, self.btn_his, self.btn_rep, self.btn_acc, self.btn_set]:
            btn.setObjectName("MenuButton"); self.style().unpolish(btn); self.style().polish(btn)
        active_btn.setObjectName("SelectedMenuButton"); self.style().unpolish(active_btn); self.style().polish(active_btn)

    def start_camera(self):
        if self.video_thread is not None: self.video_thread.stop()
        config = {'yawn_threshold': self.config_yawn_threshold, 'eye_time': self.config_eye_time, 'head_angle': self.config_head_angle}
        self.video_thread = VideoCaptureThread(source=0, config=config)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.detection_data_signal.connect(self.process_ai_data)
        self.video_thread.status_changed.connect(self.update_status)
        if hasattr(self, 'chk_mesh'): self.video_thread.set_draw_mesh(self.chk_mesh.isChecked())
        if hasattr(self, 'chk_sunglasses'): self.video_thread.set_sunglasses_mode(self.chk_sunglasses.isChecked())
        self.video_thread.start()
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)

    def stop_camera(self):
        if self.video_thread: self.video_thread.stop(); self.video_thread = None
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.video_label.setText("Camera đã dừng")
        self.lbl_status.setText("TRẠNG THÁI: ĐÃ DỪNG"); self.lbl_status.setStyleSheet("color: grey; font-weight: bold; font-size: 16px;")
        self.update_status("Đã dừng")

    def toggle_mesh_display(self, checked):
        if self.video_thread: self.video_thread.set_draw_mesh(checked)
    def toggle_sunglasses_mode(self, checked):
        if self.video_thread: self.video_thread.set_sunglasses_mode(checked)

    @pyqtSlot(np.ndarray)
    def update_image(self, cv_img):
        qt_img = self.convert_cv_qt(cv_img)
        self.video_label.setPixmap(qt_img)

    @pyqtSlot(dict)
    def process_ai_data(self, data):
        level = data.get('alert_level', 0)
        msg = data.get('alert_msg', "")
        sound_mode = self.config_audio_alert

        if level == 0:
            self.lbl_status.setText("TRẠNG THÁI: AN TOÀN 🟢")
            self.lbl_status.setStyleSheet("color: #0bc3ab; font-weight: bold; font-size: 16px;")
            self.video_label.setStyleSheet("border: 2px solid #0bc3ab; border-radius: 12px;")
        elif level == 1:
            self.lbl_status.setText(f"CẤP 1: {msg} 🟡")
            self.lbl_status.setStyleSheet("color: yellow; font-weight: bold; font-size: 16px;")
            self.video_label.setStyleSheet("border: 4px solid yellow; border-radius: 12px;")
        elif level == 2:
            self.lbl_status.setText(f"CẤP 2: {msg} 🟠")
            self.lbl_status.setStyleSheet("color: orange; font-weight: bold; font-size: 18px;")
            self.video_label.setStyleSheet("border: 6px solid orange; border-radius: 12px;")
            if winsound:
                if sound_mode == "Tiếng Bíp (Mặc định)": self.play_sound_async(frequency=1500, duration=200)
                elif sound_mode == "Giọng nói cảnh báo": self.play_sound_async(wav_file="assets/sounds/alert.wav")
        elif level == 3:
            self.lbl_status.setText(f"CẤP 3: {msg} 🔴")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold; font-size: 20px;")
            self.video_label.setStyleSheet("border: 10px solid red; border-radius: 12px;")
            if winsound:
                if sound_mode == "Tiếng Bíp (Mặc định)": self.play_sound_async(frequency=2500, duration=500)
                elif sound_mode == "Giọng nói cảnh báo": self.play_sound_async(wav_file="assets/sounds/alert.wav")
        elif level == 4:
            self.lbl_status.setText(f"CẤP 4: {msg} 🚨")
            self.lbl_status.setStyleSheet("color: black; background-color: red; font-weight: bold; font-size: 22px;")
            self.video_label.setStyleSheet("border: 15px solid black; border-radius: 12px;")
            if winsound: self.play_sound_async(frequency=3000, duration=800)
            if time.time() - self.last_email_time > 60:
                if self.config_email_sos:
                    self.email_system.send_alert_async(self.config_email_sos, "🆘 SOS: NGỦ GẬT", f"Tài xế {self.display_name} đang ngủ gật nguy hiểm!")
                    self.last_email_time = time.time()

        if level >= 2 and (time.time() - self.last_alert_time > 5):
            if self.user_info:
                self.firebase.log_alert(self.user_info['localId'], level, msg)
                self.last_alert_time = time.time()

        self.update_status(f"{msg}" if msg else "Đang theo dõi...")

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(convert_to_Qt_format).scaled(self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio)

    def update_status(self, text): self.status_bar.setText(text)

    def toggle_theme(self, checked):
        self.current_theme = "light" if checked else "dark"
        self.apply_styles()

    def apply_styles(self):
        if self.current_theme == "dark":
            self.setStyleSheet("""
                QMainWindow { background-color: #2c3e50; }
                QWidget { color: #ecf0f1; font-family: 'Segoe UI', Arial; font-size: 15px; }
                QWidget#Sidebar { background-color: #34495e; }
                QLabel#SidebarTitle { font-size: 22px; font-weight: bold; color: #0bc3ab; }
                QPushButton#MenuButton { background: transparent; border: none; text-align: left; padding: 15px; font-size: 16px; }
                QPushButton#MenuButton:hover { background-color: #405a74; border-radius: 8px;}
                QPushButton#SelectedMenuButton { background-color: #0bc3ab; color: white; border-radius: 8px; padding: 15px; text-align: left; font-weight: bold; font-size: 16px;}
                QWidget#MainArea { background-color: #2c3e50; }
                QWidget#FormContainer { background-color: #34495e; border-radius: 15px; padding: 30px; }
                QLabel#FormTitle { font-size: 20px; font-weight: bold; color: #0bc3ab; margin-bottom: 20px; }
                QPushButton#StartButton { background-color: #0bc3ab; border-radius: 8px; padding: 12px 30px; font-weight: bold; color: white; font-size: 16px; }
                QPushButton#StartButton:hover { background-color: #16a085; }
                QPushButton#StopButton { background-color: #e74c3c; border-radius: 8px; padding: 12px 30px; font-weight: bold; color: white; font-size: 16px; }
                QPushButton#StopButton:hover { background-color: #c0392b; }
                QPushButton#StopButton:disabled { background-color: #7f8c8d; }
                QSpinBox, QComboBox, QLineEdit { background-color: #2c3e50; border: 1px solid #7f8c8d; padding: 5px; border-radius: 5px; color: white; font-size: 15px; }
                QTableWidget { background-color: #2c3e50; color: white; gridline-color: #555; font-size: 14px; border: 1px solid #555; }
                QTableWidget::item { padding: 5px; }
                QHeaderView::section { background-color: #34495e; color: white; padding: 5px; border: 1px solid #555; font-weight: bold; }
                QTableCornerButton::section { background-color: #34495e; }
                QLineEdit#ReadOnlyInput { background-color: #444; color: #aaa; }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow { background-color: #f5f7fa; }
                QWidget { color: #34495e; font-family: 'Segoe UI', Arial; font-size: 15px; }
                QWidget#Sidebar { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
                QLabel#SidebarTitle { font-size: 22px; font-weight: bold; color: #0bc3ab; }
                QPushButton#MenuButton { background: transparent; border: none; text-align: left; padding: 15px; color: #555; font-size: 16px; }
                QPushButton#MenuButton:hover { background-color: #e0e0e0; border-radius: 8px;}
                QPushButton#SelectedMenuButton { background-color: #0bc3ab; color: white; border-radius: 8px; padding: 15px; text-align: left; font-weight: bold; font-size: 16px;}
                QWidget#MainArea { background-color: #f5f7fa; }
                QWidget#FormContainer { background-color: #ffffff; border-radius: 15px; padding: 30px; border: 1px solid #d0d0d0; }
                QLabel#FormTitle { font-size: 20px; font-weight: bold; color: #0bc3ab; margin-bottom: 20px; }
                QPushButton#StartButton { background-color: #0bc3ab; border-radius: 8px; padding: 12px 30px; font-weight: bold; color: white; font-size: 16px; }
                QPushButton#StartButton:hover { background-color: #16a085; }
                QPushButton#StopButton { background-color: #e74c3c; border-radius: 8px; padding: 12px 30px; font-weight: bold; color: white; font-size: 16px; }
                QPushButton#StopButton:hover { background-color: #c0392b; }
                QPushButton#StopButton:disabled { background-color: #bdc3c7; }
                QSpinBox, QComboBox, QLineEdit { background-color: #ffffff; border: 1px solid #bdc3c7; padding: 5px; border-radius: 5px; color: #2c3e50; font-size: 15px; }
                QCheckBox { color: #34495e; }
                QTableWidget { border: 1px solid #d0d0d0; background-color: #ffffff; color: #34495e; gridline-color: #e0e0e0; }
                QTableWidget::item { padding: 5px; }
                QHeaderView::section { background-color: #f0f0f0; color: #34495e; padding: 5px; border-bottom: 1px solid #d0d0d0; }
                QLineEdit#ReadOnlyInput { background-color: #e0e0e0; color: #777; }
                QLabel#StatusBar { background-color: #ffffff; color: #555; border-top: 1px solid #e0e0e0; }
            """)

    def closeEvent(self, event): self.stop_camera(); event.accept()