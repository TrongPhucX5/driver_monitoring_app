"""
Camera Module - Tích hợp MediaPipe Face Processor
Sử dụng PySide6 cho GUI và MediaPipe để xử lý
"""

import sys
import cv2
import time  # --- MỚI ---: Cần để theo dõi thời gian (nhắm mắt, ngáp)
import threading # <--- Thêm dòng này để chạy âm thanh không bị lag
# --- CẬP NHẬT IMPORT ---
from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer 
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget,
    QFormLayout, QSpacerItem, QSizePolicy,
    QSlider, QComboBox, QSpinBox, QCheckBox, QLineEdit
)

from modules.sound import SoundModule # <--- Import module phát nhạc có sẵn
from modules.email_alert import send_alert_email
# --- MỚI ---: Import FaceProcessor từ file face_processor.py
try:
    from modules.face_processor import FaceProcessor
except ImportError:
    print("Lỗi: Không tìm thấy file 'face_processor.py'.")
    print("Hãy đảm bảo bạn có file 'modules/__init__.py' (có thể rỗng)")
    print("và file 'modules/face_processor.py'.")
    sys.exit(1)


# --- Class VideoThread (ĐÃ CẬP NHẬT) ---
class VideoThread(QThread):
    change_pixmap_signal = Signal(QImage)
    # --- MỚI ---: Signal để gửi dữ liệu (EAR, MAR, góc) về MainWindow
    detection_data_signal = Signal(dict)

    def __init__(self, source=0):
        super().__init__()
        self._run_flag = True
        self.source = source
        # --- MỚI ---: Khởi tạo processor
        try:
            self.processor = FaceProcessor()
        except Exception as e:
            print(f"Lỗi khi khởi tạo FaceProcessor: {e}")
            self.processor = None

    def run(self):
        if not self.processor:
            print("Lỗi: FaceProcessor không được khởi tạo. Thoát thread.")
            return

        cap = cv2.VideoCapture(self.source)
        while self._run_flag and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                # --- MỚI ---: Lật ảnh (webcam thường bị ngược)
                frame = cv2.flip(frame, 1)

                # --- MỚI ---: Xử lý frame bằng processor
                # annotated_frame là ảnh BGR đã vẽ, data là dict kết quả
                annotated_frame, data = self.processor.process_frame(frame)

                # --- CẬP NHẬT ---: Chuyển đổi ảnh đã vẽ (annotated_frame)
                rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
                )
                
                # Gửi ảnh đi
                self.change_pixmap_signal.emit(convert_to_Qt_format)
                
                # --- MỚI ---: Gửi dữ liệu (EAR, MAR, v.v.) đi
                self.detection_data_signal.emit(data)

        cap.release()
        print("Đã giải phóng camera.")

    def stop(self):
        self._run_flag = False
        self.wait()
        # --- MỚI ---: Giải phóng tài nguyên MediaPipe
        if self.processor:
            self.processor.close()
            print("Đã đóng FaceProcessor.")


# --- Cửa sổ chính (ĐÃ CẬP NHẬT) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hệ thống Giám sát Lái xe")
        self.setGeometry(100, 100, 1024, 768)
        self.video_thread = None

        # --- MỚI ---: Thêm biến trạng thái giao diện
        self.current_theme = "dark" # Bắt đầu với theme tối

        # --- MỚI ---: Khởi tạo các biến cấu hình và trạng thái
        self.init_config_vars()
        self.init_state_vars()
        # --- MỚI: Khởi tạo module âm thanh ---
        self.sound_module = SoundModule()

        self.initUI()
        self.apply_styles() # <-- Sẽ áp dụng theme "dark" mặc định
        self.show_monitoring_page()

    # --- MỚI ---: Hàm khởi tạo các biến CẤU HÌNH (settings)
    def init_config_vars(self):
        """Lưu trữ các giá trị ngưỡng từ trang Cài đặt"""
        
        # Ngưỡng vật lý (nội bộ, không đổi)
        self.INTERNAL_EAR_THRESHOLD = 0.25 
        self.INTERNAL_MAR_THRESHOLD = 0.5   
        self.INTERNAL_YAWN_RESET_TIME_SEC = 60 
        
        # Ngưỡng do người dùng cài đặt (lấy từ giá trị mặc định của SpinBox)
        self.config_yawn_threshold_count = 3  # (lần)
        self.config_eye_time_sec = 2          # (giây)
        self.config_head_angle_deg = 20       # (độ)
        self.config_audio_alert = "Tiếng Bíp (Mặc định)" 
        self.config_recipient_email = ""  # Email nhận cảnh báo
    # --- MỚI ---: Hàm khởi tạo các biến TRẠNG THÁI (state)
    def init_state_vars(self):
        """Reset các biến theo dõi trạng thái (dùng khi bắt đầu/dừng)"""
        self.eye_closed_start_time = None
        # --- MỚI: Biến theo dõi thời gian cho Ngáp và Mất mặt ---
        self.no_face_start_time = None # Thời điểm bắt đầu mất mặt
        self.yawn_start_time = None    # Thời điểm bắt đầu mở miệng (ngáp)
        self.is_yawning_state = False # Trạng thái đang ngáp (để đếm 1 lần)
        self.eye_closed_start_time = None
        self.yawn_count = 0
        self.last_yawn_time = None
        self.last_sound_time = 0
        self.last_email_time = 0
    # --- MỚI: Biến lưu góc lệch của đầu (Calibration) ---
        # Nếu chưa calibrate thì mặc định là 0
        if not hasattr(self, 'roll_offset'):
            self.roll_offset = 0

    # --- LOGIC MỚI: Cân bằng đầu ---
    @Slot()
    def calibrate_head_pose(self):
        """Lấy góc nghiêng hiện tại làm mốc 0"""
        # Chúng ta cần lấy giá trị roll hiện tại. 
        # Vì biến roll nằm trong luồng thread, ta sẽ truy cập qua biến tạm hoặc
        # đơn giản là set flag để lần update sau tự lấy.
        # Cách đơn giản nhất: Lưu giá trị raw_roll mới nhất vào self
        if hasattr(self, 'current_raw_roll'):
            self.roll_offset = self.current_raw_roll
            self.status_bar_label.setText(f"Đã cân bằng! Góc lệch mới: {self.roll_offset:.1f} độ")
        else:
            self.status_bar_label.setText("Chưa nhận diện được khuôn mặt để cân bằng!")

    # --- LOGIC MỚI: Tắt còi thủ công ---
    @Slot()
    def manual_stop_alarm(self):
        """Tắt âm thanh ngay lập tức và reset trạng thái"""
        # 1. Dừng nhạc
        self.sound_module.stop_sound()
        
        # 2. Reset toàn bộ bộ đếm
        self.init_state_vars()
        
        # 3. Thông báo
        self.status_bar_label.setText("Trạng thái: Đã tắt còi & Reset hệ thống")
        print("Người dùng đã tắt cảnh báo thủ công.")

    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(15)
        title_label = QLabel("Giám sát Lái xe")
        title_label.setObjectName("SidebarTitle")
        
        self.menu_giam_sat = QPushButton("Giám sát")
        self.menu_giam_sat.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.menu_tai_khoan = QPushButton("Tài khoản")
        self.menu_tai_khoan.setObjectName("MenuButton")
        self.menu_tai_khoan.setEnabled(True) # <-- CẬP NHẬT: Mở khóa
        self.menu_tai_khoan.setCursor(Qt.CursorShape.PointingHandCursor) # <-- MỚI
        
        self.btn_cai_dat = QPushButton("Cài đặt cá nhân")
        self.btn_cai_dat.setToolTip("Tùy chỉnh âm thanh và ngưỡng cảnh báo")
        self.btn_cai_dat.setObjectName("SettingsButton_Unselected")
        self.btn_cai_dat.setCursor(Qt.CursorShape.PointingHandCursor)
        
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(self.menu_giam_sat)
        sidebar_layout.addWidget(self.menu_tai_khoan)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.btn_cai_dat)
        main_layout.addWidget(sidebar)

        # 2. Main Area
        main_area = QWidget()
        main_area.setObjectName("MainArea")
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(20, 20, 20, 10)
        main_area_layout.setSpacing(10)
        self.stacked_widget = QStackedWidget()
        
        # --- CẬP NHẬT THỨ TỰ INDEX ---
        monitoring_page = self.create_monitoring_page() # Index 0
        account_page = self.create_account_page()       # Index 1 (MỚI)
        settings_page = self.create_settings_page()     # Index 2 (Dời xuống)

        self.stacked_widget.addWidget(monitoring_page)
        self.stacked_widget.addWidget(account_page)   # <-- THÊM VÀO
        self.stacked_widget.addWidget(settings_page)

        main_area_layout.addWidget(self.stacked_widget)

        self.status_bar_label = QLabel("Trạng thái: Idle (User: GX6dYP8C63db3jEVACfvmw3uJDH2)")
        self.status_bar_label.setObjectName("StatusBar")
        self.status_bar_label.setFixedHeight(25)
        
        main_area_layout.addWidget(self.status_bar_label)
        main_layout.addWidget(main_area, 1)

        # Kết nối sự kiện
        self.btn_bat_dau.clicked.connect(self.start_video)
        self.btn_dung_lai.clicked.connect(self.stop_video)
        self.menu_giam_sat.clicked.connect(self.show_monitoring_page)
        self.menu_tai_khoan.clicked.connect(self.show_account_page) # <-- MỚI
        self.btn_cai_dat.clicked.connect(self.show_settings_page)

    def create_monitoring_page(self):
        page_widget = QWidget()
        layout = QVBoxLayout(page_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.video_label = QLabel("No video")
        self.video_label.setObjectName("VideoLabel")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        layout.addWidget(self.video_label, 1)
        # --- MỚI: Hàng nút chức năng phụ ---
        tools_layout = QHBoxLayout()
        
        # Nút Cân bằng đầu (Fix lỗi nghiêng đầu)
        self.btn_calibrate = QPushButton("Cân bằng vị trí đầu")
        self.btn_calibrate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_calibrate.setStyleSheet("background-color: #3498db; color: white; padding: 8px;")
        self.btn_calibrate.clicked.connect(self.calibrate_head_pose)
        
        # Nút Tắt còi khẩn cấp (Fix lỗi kêu mãi)
        self.btn_stop_alarm = QPushButton("🔕 TẮT CÒI / RESET")
        self.btn_stop_alarm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop_alarm.setStyleSheet("background-color: #f1c40f; color: black; font-weight: bold; padding: 8px;")
        self.btn_stop_alarm.clicked.connect(self.manual_stop_alarm)
        
        tools_layout.addWidget(self.btn_calibrate)
        tools_layout.addWidget(self.btn_stop_alarm)
        layout.addLayout(tools_layout)
        control_layout = QHBoxLayout()
        self.btn_bat_dau = QPushButton("BẮT ĐẦU GIÁM SÁT")
        self.btn_bat_dau.setObjectName("StartButton")
        self.btn_bat_dau.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dung_lai = QPushButton("DỪNG LẠI")
        self.btn_dung_lai.setObjectName("StopButton")
        self.btn_dung_lai.setEnabled(False)
        self.btn_dung_lai.setCursor(Qt.CursorShape.PointingHandCursor)
        control_layout.addStretch()
        control_layout.addWidget(self.btn_bat_dau)
        control_layout.addWidget(self.btn_dung_lai)
        control_layout.addStretch()
        layout.addLayout(control_layout)
        return page_widget

    # --- HÀM MỚI ---: Tạo trang Tài khoản
    def create_account_page(self):
        """Tạo widget cho trang Tài khoản & Giao diện"""
        page_widget = QWidget()
        main_layout = QVBoxLayout(page_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        form_container = QWidget()
        form_container.setObjectName("FormContainer")
        form_container.setMaximumWidth(500)
        form_layout = QVBoxLayout(form_container)
        
        title = QLabel("Tài khoản & Giao diện")
        title.setObjectName("FormTitle")
        
        settings_form = QFormLayout()
        settings_form.setSpacing(15)

        # 1. Chế độ Giao diện (Theme)
        self.theme_toggle_cb = QCheckBox("Bật Giao diện Sáng (Light Mode)")
        self.theme_toggle_cb.setCursor(Qt.CursorShape.PointingHandCursor)
        # Kết nối chức năng đổi theme
        self.theme_toggle_cb.toggled.connect(self.toggle_theme) 
        settings_form.addRow(QLabel("Giao diện:"), self.theme_toggle_cb)

        # 2. Các nút chức năng
        self.btn_switch_account = QPushButton("CHUYỂN TÀI KHOẢN")
        self.btn_switch_account.setObjectName("MenuButton") # Dùng style nút menu
        self.btn_switch_account.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_switch_account.clicked.connect(self.do_switch_account) # Kết nối

        self.btn_logout = QPushButton("ĐĂNG XUẤT")
        self.btn_logout.setObjectName("StopButton") # Dùng style nút Dừng màu đỏ
        self.btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_logout.clicked.connect(self.do_logout) # Kết nối

        form_layout.addWidget(title)
        form_layout.addLayout(settings_form)
        form_layout.addSpacing(20)
        form_layout.addWidget(self.btn_switch_account)
        form_layout.addSpacing(10)
        form_layout.addWidget(self.btn_logout)
        
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        main_layout.addWidget(form_container)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        return page_widget

    # --- HÀM create_settings_page (CẬP NHẬT) ---
    def create_settings_page(self):
        """Tạo widget cho trang Cài đặt cá nhân"""
        page_widget = QWidget()
        main_layout = QVBoxLayout(page_widget)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        form_container = QWidget()
        form_container.setObjectName("FormContainer")
        form_container.setMaximumWidth(500)
        form_layout = QVBoxLayout(form_container)
        
        title = QLabel("Cài đặt cá nhân")
        title.setObjectName("FormTitle")
        
        settings_form = QFormLayout()
        settings_form.setSpacing(15)

# --- MỚI: Ô nhập Email người thân ---
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Ví dụ: nguoi_than@gmail.com")
        self.email_input.setText(self.config_recipient_email) # Hiển thị email cũ nếu có
        self.email_input.setStyleSheet("background-color: #ffffff; color: #2c3e50; padding: 8px; border-radius: 4px;")
        settings_form.addRow(QLabel("Email người thân:"), self.email_input)
        # 1. Âm thanh
        self.audio_alert_combo = QComboBox()
        self.audio_alert_combo.addItems(["Tiếng Bíp (Mặc định)", "Giọng nói cảnh báo", "Tắt âm thanh"])
        self.audio_alert_combo.setCurrentText(self.config_audio_alert)
        self.audio_alert_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Âm thanh cảnh báo:"), self.audio_alert_combo)

        # 2. Độ nhạy (tạm thời chưa dùng, nhưng giữ lại)
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sensitivity_slider.setTickInterval(1)
        self.sensitivity_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Độ nhạy chung:"), self.sensitivity_slider)
        
        # 3. Ngưỡng ngáp
        self.yawn_threshold_spinbox = QSpinBox()
        self.yawn_threshold_spinbox.setRange(1, 10) 
        self.yawn_threshold_spinbox.setValue(self.config_yawn_threshold_count) # Cập nhật
        self.yawn_threshold_spinbox.setSuffix(" lần")
        self.yawn_threshold_spinbox.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Ngưỡng ngáp:"), self.yawn_threshold_spinbox)
        
        # 4. Ngưỡng nhắm mắt
        self.eye_time_spinbox = QSpinBox()
        self.eye_time_spinbox.setRange(1, 10) 
        self.eye_time_spinbox.setValue(self.config_eye_time_sec) # Cập nhật
        self.eye_time_spinbox.setSuffix(" giây")
        self.eye_time_spinbox.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Nhắm mắt quá:"), self.eye_time_spinbox)
        
        # 5. Ngưỡng nghiêng đầu
        self.head_angle_spinbox = QSpinBox()
        self.head_angle_spinbox.setRange(10, 45) 
        self.head_angle_spinbox.setValue(self.config_head_angle_deg) # Cập nhật
        self.head_angle_spinbox.setSuffix(" độ")
        self.head_angle_spinbox.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Đầu nghiêng quá:"), self.head_angle_spinbox)

        # Nút Lưu
        btn_save = QPushButton("LƯU CÀI ĐẶT")
        btn_save.setObjectName("StartButton")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        # --- MỚI ---: Kết nối nút Lưu
        btn_save.clicked.connect(self.save_settings)

        form_layout.addWidget(title)
        form_layout.addLayout(settings_form)
        form_layout.addSpacing(20)
        form_layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        main_layout.addWidget(form_container)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        
        return page_widget

    # --- Các hàm chuyển trang (ĐÃ CẬP NHẬT) ---
    @Slot()
    def show_monitoring_page(self):
        self.stacked_widget.setCurrentIndex(0)
        self.menu_giam_sat.setObjectName("SelectedMenuButton")
        self.menu_tai_khoan.setObjectName("MenuButton") # <-- MỚI
        self.btn_cai_dat.setObjectName("SettingsButton_Unselected")
        self.refresh_styles()

    @Slot()
    def show_account_page(self):
        self.stacked_widget.setCurrentIndex(1) # Index 1 là trang Tài khoản
        self.menu_giam_sat.setObjectName("MenuButton")
        self.menu_tai_khoan.setObjectName("SelectedMenuButton") # <-- MỚI
        self.btn_cai_dat.setObjectName("SettingsButton_Unselected")
        self.refresh_styles()

    @Slot()
    def show_settings_page(self):
        self.stacked_widget.setCurrentIndex(2) # <-- CẬP NHẬT: Index 2
        self.menu_giam_sat.setObjectName("MenuButton")
        self.menu_tai_khoan.setObjectName("MenuButton") # <-- MỚI
        self.btn_cai_dat.setObjectName("SettingsButton_Selected")
        self.refresh_styles()

    def refresh_styles(self):
        self.style().unpolish(self.menu_giam_sat)
        self.style().polish(self.menu_giam_sat)
        self.style().unpolish(self.menu_tai_khoan) # <-- MỚI
        self.style().polish(self.menu_tai_khoan)   # <-- MỚI
        self.style().unpolish(self.btn_cai_dat)
        self.style().polish(self.btn_cai_dat)

    # --- Các hàm xử lý video (ĐÃ CẬP NHẬT) ---
    @Slot()
    def start_video(self):
        # --- MỚI ---: Reset trạng thái mỗi khi bắt đầu
        self.init_state_vars()

        if self.video_thread is not None:
            self.video_thread.stop()
            
        self.video_thread = VideoThread(source=0)
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        # --- MỚI ---: Kết nối với signal dữ liệu
        self.video_thread.detection_data_signal.connect(self.handle_detection_data)
        
        self.video_thread.start()
        self.btn_bat_dau.setEnabled(False)
        self.btn_dung_lai.setEnabled(True)
        self.video_label.setText("")
        self.status_bar_label.setText("Trạng thái: Đang khởi động...")

    @Slot()
    def stop_video(self):
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        self.btn_bat_dau.setEnabled(True)
        self.btn_dung_lai.setEnabled(False)
        self.video_label.setText("No video")
        # --- CẬP NHẬT ---: Reset status bar
        self.status_bar_label.setText("Trạng thái: Idle (User: GX6dYP8C63db3jEVACfvmw3uJDH2)")


    @Slot(QImage)
    def update_image(self, qt_img):
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    def closeEvent(self, event):
        self.stop_video()
        event.accept()

    # --- HÀM apply_styles (ĐÃ TÁCH RA ĐỂ HỖ TRỢ LIGHT/DARK MODE) ---
    def apply_styles(self):
        """Hàm điều khiển, gọi QSS phù hợp với theme hiện tại"""
        if self.current_theme == "light":
            style_sheet = self.get_light_stylesheet()
        else:
            style_sheet = self.get_dark_stylesheet()
        
        self.setStyleSheet(style_sheet)
        
        # Cập nhật lại style của các nút (quan trọng)
        self.refresh_styles()

    def get_dark_stylesheet(self):
        """Trả về QSS cho Giao diện Tối (Dark Mode)"""
        return """
            /* Nền chung */
            QWidget {
                background-color: #2c3e50;
                color: #ecf0f1;
                font-family: Arial;
            }

            /* --- Sidebar --- */
            QWidget#Sidebar {
                background-color: #34495e;
            }
            QLabel#SidebarTitle {
                font-size: 16px;
                font-weight: bold;
                color: white;
            }
            QPushButton#MenuButton {
                background-color: transparent;
                color: #bdc3c7;
                border: none;
                padding: 10px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton#MenuButton:hover {
                background-color: #405a74;
            }
            QPushButton#MenuButton:disabled {
                color: #7f8c8d;
                background-color: transparent;
            }
            
            QPushButton#SelectedMenuButton {
                background-color: #1abc9c;
                color: white;
                border: none;
                padding: 10px;
                text-align: left;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton#SettingsButton_Unselected {
                background-color: transparent;
                color: #bdc3c7;
                font-weight: bold;
                padding: 12px 5px;
                border-radius: 5px;
                font-size: 13px;
                border: 1px solid #7f8c8d;
            }
            QPushButton#SettingsButton_Unselected:hover {
                background-color: #405a74;
            }
            QPushButton#SettingsButton_Selected {
                background-color: #1abc9c;
                color: white;
                font-weight: bold;
                padding: 12px 5px;
                border-radius: 5px;
                font-size: 13px;
                border: none;
            }

            /* --- Main Area --- */
            QWidget#MainArea {
                background-color: #2c3e50;
            }
            QLabel#VideoLabel {
                background-color: black;
                color: #7f8c8d;
                font-size: 24px;
                border-radius: 5px;
            }
            QPushButton#StartButton {
                background-color: #1abc9c;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 5px;
                font-size: 13px;
                min-width: 150px;
            }
            QPushButton#StartButton:hover {
                background-color: #16a085;
            }
            QPushButton#StopButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 5px;
                font-size: 13px;
                min-width: 150px;
            }
            QPushButton#StopButton:hover {
                background-color: #c0392b;
            }
            QPushButton#StopButton:disabled {
                background-color: #7f8c8d;
                color: #bdc3c7;
            }
            
            QLabel#StatusBar {
                color: #95a5a6;
                font-size: 11px;
            }
            
            /* --- Trang Cài đặt (Form) --- */
            QWidget#FormContainer {
                background-color: #34495e;
                border-radius: 8px;
                padding: 20px;
            }
            QLabel#FormTitle {
                font-size: 18px;
                font-weight: bold;
                color: #1abc9c;
                margin-bottom: 10px;
                text-align: center;
            }
            QWidget#FormContainer QLabel {
                font-size: 14px;
                color: #ecf0f1;
            }
            
            /* Style cho QComboBox, QSlider, QSpinBox */
            QComboBox, QSpinBox {
                background-color: #2c3e50;
                border: 1px solid #7f8c8d;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
                color: white;
            }
            QComboBox QAbstractItemView {
                background-color: #34495e;
                border: 1px solid #7f8c8d;
                selection-background-color: #1abc9c;
            }

            QSlider::groove:horizontal {
                border: 1px solid #7f8c8d;
                height: 8px;
                background: #2c3e50;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1abc9c;
                border: 1px solid #1abc9c;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::tick:horizontal {
                height: 10px;
                width: 2px;
                background: #7f8c8d;
                margin-top: 1px;
            }
            
            /* MỚI: Style cho QCheckBox */
            QCheckBox {
                font-size: 14px;
                color: #ecf0f1;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #2c3e50;
                border: 1px solid #7f8c8d;
            }
            QCheckBox::indicator:checked {
                background-color: #1abc9c;
                border: 1px solid #1abc9c;
            }
        """

    def get_light_stylesheet(self):
        """Trả về QSS cho Giao diện Sáng (Light Mode)"""
        return """
            /* Nền chung */
            QWidget {
                background-color: #ecf0f1;
                color: #2c3e50;
                font-family: Arial;
            }

            /* --- Sidebar --- */
            QWidget#Sidebar {
                background-color: #ffffff;
                border-right: 1px solid #bdc3c7;
            }
            QLabel#SidebarTitle {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
            }
            QPushButton#MenuButton {
                background-color: transparent;
                color: #34495e;
                border: none;
                padding: 10px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton#MenuButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton#MenuButton:disabled {
                color: #bdc3c7;
                background-color: transparent;
            }
            
            QPushButton#SelectedMenuButton {
                background-color: #1abc9c;
                color: white;
                border: none;
                padding: 10px;
                text-align: left;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton#SettingsButton_Unselected {
                background-color: transparent;
                color: #34495e;
                font-weight: bold;
                padding: 12px 5px;
                border-radius: 5px;
                font-size: 13px;
                border: 1px solid #7f8c8d;
            }
            QPushButton#SettingsButton_Unselected:hover {
                background-color: #f0f0f0;
            }
            QPushButton#SettingsButton_Selected {
                background-color: #1abc9c;
                color: white;
                font-weight: bold;
                padding: 12px 5px;
                border-radius: 5px;
                font-size: 13px;
                border: none;
            }

            /* --- Main Area --- */
            QWidget#MainArea {
                background-color: #ecf0f1;
            }
            QLabel#VideoLabel {
                background-color: #2c3e50;
                color: #7f8c8d;
                font-size: 24px;
                border-radius: 5px;
            }
            
            /* (Giữ nguyên style các nút Start/Stop) */
            QPushButton#StartButton {
                background-color: #1abc9c; color: white; font-weight: bold;
                padding: 12px 20px; border-radius: 5px; font-size: 13px; min-width: 150px;
            }
            QPushButton#StartButton:hover { background-color: #16a085; }
            QPushButton#StopButton {
                background-color: #e74c3c; color: white; font-weight: bold;
                padding: 12px 20px; border-radius: 5px; font-size: 13px; min-width: 150px;
            }
            QPushButton#StopButton:hover { background-color: #c0392b; }
            QPushButton#StopButton:disabled { background-color: #bdc3c7; color: #ecf0f1; }
            
            QLabel#StatusBar {
                color: #34495e;
                font-size: 11px;
            }
            
            /* --- Trang Cài đặt (Form) --- */
            QWidget#FormContainer {
                background-color: #ffffff;
                border-radius: 8px;
                padding: 20px;
                border: 1px solid #bdc3c7;
            }
            QLabel#FormTitle {
                font-size: 18px;
                font-weight: bold;
                color: #1abc9c;
                margin-bottom: 10px;
                text-align: center;
            }
            QWidget#FormContainer QLabel {
                font-size: 14px;
                color: #2c3e50;
            }
            
            /* Style cho QComboBox, QSlider, QSpinBox */
            QComboBox, QSpinBox {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
                color: #2c3e50;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
                selection-background-color: #1abc9c;
            }

            QSlider::groove:horizontal {
                border: 1px solid #bdc3c7;
                height: 8px;
                background: #ffffff;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1abc9c; border: 1px solid #1abc9c;
                width: 18px; margin: -5px 0; border-radius: 9px;
            }
            QSlider::tick:horizontal {
                height: 10px; width: 2px;
                background: #bdc3c7;
                margin-top: 1px;
            }

            /* MỚI: Style cho QCheckBox */
            QCheckBox {
                font-size: 14px;
                color: #2c3e50;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
            }
            QCheckBox::indicator:checked {
                background-color: #1abc9c;
                border: 1px solid #1abc9c;
            }
        """
        
    
    # --- MỚI ---: Hàm lưu cài đặt
    @Slot()
    def save_settings(self):
        """Đọc giá trị từ SpinBox và lưu vào biến config"""
        self.config_yawn_threshold_count = self.yawn_threshold_spinbox.value()
        self.config_eye_time_sec = self.eye_time_spinbox.value()
        self.config_head_angle_deg = self.head_angle_spinbox.value()
        self.config_audio_alert = self.audio_alert_combo.currentText()
        # --- MỚI: Lưu email ---
        self.config_recipient_email = self.email_input.text().strip()
        
        print("--- CÀI ĐẶT ĐÃ LƯU ---")
        print(f"Email người nhận: {self.config_recipient_email}")
        
        print("--- CÀI ĐẶT ĐÃ LƯU ---")
        print(f"Âm thanh cảnh báo: {self.config_audio_alert}")
        print(f"Ngưỡng ngáp: {self.config_yawn_threshold_count} lần")
        print(f"Ngưỡng nhắm mắt: {self.config_eye_time_sec} giây")
        print(f"Ngưỡng nghiêng đầu: {self.config_head_angle_deg} độ")
        
        # Cập nhật thanh trạng thái (tạm thời)
        original_text = self.status_bar_label.text()
        self.status_bar_label.setText("Trạng thái: Đã lưu cài đặt!")
        
        # Tạo hiệu ứng thông báo ngắn
        QTimer.singleShot(2000, lambda: self.status_bar_label.setText(original_text))

    # --- MỚI ---: Các hàm cho trang Tài khoản
    @Slot()
    def do_switch_account(self):
        print("Chức năng 'Chuyển tài khoản' đã được nhấn.")
        # TODO: Thêm logic chuyển tài khoản (ví dụ: hiển thị cửa sổ đăng nhập)
        original_text = self.status_bar_label.text()
        self.status_bar_label.setText("Trạng thái: Yêu cầu chuyển tài khoản...")
        QTimer.singleShot(2000, lambda: self.status_bar_label.setText(original_text))

    @Slot()
    def do_logout(self):
        print("Chức năng 'Đăng xuất' đã được nhấn.")
        # TODO: Thêm logic đăng xuất (ví dụ: đóng cửa sổ này, mở đăng nhập)
        original_text = self.status_bar_label.text()
        self.status_bar_label.setText("Trạng thái: Đang đăng xuất...")
        # Ví dụ: Tự động đóng app sau 2s
        QTimer.singleShot(2000, lambda: self.close()) 

    @Slot(bool)
    def toggle_theme(self, checked):
        if checked:
            self.current_theme = "light"
            print("Chuyển sang Giao diện Sáng (Light Mode)")
        else:
            self.current_theme = "dark"
            print("Chuyển sang Giao diện Tối (Dark Mode)")
        
        self.apply_styles() # Áp dụng lại toàn bộ stylesheet

# --- HÀM MỚI: Xử lý phát âm thanh cảnh báo ---
    def trigger_warning_sound(self, sound_file, cooldown=3.0, loop=False):
        """Phát âm thanh cụ thể"""
        if self.config_audio_alert == "Tắt âm thanh":
            return
        current_time = time.time()
        # Nếu chưa đủ thời gian chờ từ lần phát trước -> Bỏ qua
        # Nếu đang báo động nguy hiểm (loop=True) thì bỏ qua cooldown
        if not loop and (current_time - self.last_sound_time < cooldown):
            return

        # Cập nhật thời gian phát mới
        self.last_sound_time = current_time
        # Gọi hàm bên module sound (đã có threading bên đó rồi)
        self.sound_module.play_sound(sound_file, loop=loop)
        
    # --- MỚI ---: Hàm xử lý dữ liệu từ VideoThread
    @Slot(dict)
    def handle_detection_data(self, data):
        current_time = time.time()
        status_messages = []

        # === 1. Xử lý: KHÔNG TÌM THẤY KHUÔN MẶT ===
        if not data["face_found"]:
            if self.no_face_start_time is None:
                self.no_face_start_time = current_time
            else:
                no_face_duration = current_time - self.no_face_start_time
                
                # Cấp độ 2: Mất mặt > 3s -> NGUY HIỂM (Kêu dồn dập mỗi 2s)
                if no_face_duration > 3:
                    self.status_bar_label.setText(f"NGUY HIỂM: KHÔNG THẤY TÀI XẾ ({no_face_duration:.1f}s)")
                    self.trigger_warning_sound("alarm_danger.mp3", cooldown=2.0, loop=True)
                    # --- [GỬI EMAIL] ---
                    self.trigger_alert_email(
                        subject="[CẢNH BÁO KHẨN] Mất tín hiệu tài xế!",
                        message=f"Hệ thống không thấy tài xế trong {no_face_duration:.1f} giây. Vui lòng kiểm tra ngay."
                    )
                    # Reset các timer khác để tránh xung đột
                    self.eye_closed_start_time = None
                    self.yawn_start_time = None
                    return # Thoát luôn để ưu tiên cảnh báo này
                else:
                    self.status_bar_label.setText(f"Cảnh báo: Mất tín hiệu khuôn mặt ({no_face_duration:.1f}s)")
            return
        else:
            self.no_face_start_time = None

        # Lấy dữ liệu
        ear = data["ear"]
        mar = data["mar"]
        raw_roll = data["roll"]
        # Lưu raw_roll để dùng cho nút Cân bằng
        self.current_raw_roll = raw_roll
        # Tính roll thực tế sau khi trừ đi góc lệch (offset)
        roll = raw_roll - self.roll_offset

        # === 2. Xử lý: NHẮM MẮT (EAR) ===
        if ear < self.INTERNAL_EAR_THRESHOLD:
            if self.eye_closed_start_time is None:
                self.eye_closed_start_time = current_time
            else:
                eye_duration = current_time - self.eye_closed_start_time
                
                if eye_duration > 5: # NGUY HIỂM
                    msg = f"NGUY HIỂM: NHẮM MẮT ({eye_duration:.1f}s)"
                    status_messages.append(msg)
                    # Ưu tiên cao nhất, cooldown ngắn (2s)
                    self.trigger_warning_sound("alarm_danger.mp3", cooldown=2.0, loop=True)
                    # --- [GỬI EMAIL] ---
                    self.trigger_alert_email(
                        subject="[CẢNH BÁO KHẨN] Tài xế ngủ gật!",
                        message=f"Tài xế đã nhắm mắt quá {eye_duration:.1f} giây. Nguy cơ tai nạn cao."
                    )
                elif eye_duration > self.config_eye_time_sec: # Cảnh báo thường
                    msg = f"Buồn ngủ ({eye_duration:.1f}s)"
                    status_messages.append(msg)
                    # Cảnh báo thường, cooldown dài hơn (3s)
                    self.trigger_warning_sound("warning_eye.mp3", cooldown=3.0)
        else:
            self.eye_closed_start_time = None

        # === 3. Xử lý: NGÁP (MAR) ===
        if mar > self.INTERNAL_MAR_THRESHOLD:
            if self.yawn_start_time is None:
                self.yawn_start_time = current_time
            else:
                yawn_duration = current_time - self.yawn_start_time
                
                if yawn_duration > 5: # NGUY HIỂM
                    msg = f"NGUY HIỂM: NGÁP DÀI ({yawn_duration:.1f}s)"
                    status_messages.append(msg)
                    self.trigger_warning_sound("alarm_eye.mp3", cooldown=2.0, loop=True)
                
                # Logic đếm số lần ngáp (giữ nguyên như cũ)
                if not self.is_yawning_state:
                    self.is_yawning_state = True
                    self.yawn_count += 1
                    # # Phát tiếng ngáp 1 lần duy nhất khi bắt đầu mở miệng
                    # self.trigger_warning_sound("warning_eye.mp3", cooldown=3.0)
        else:
            self.is_yawning_state = False
            self.yawn_start_time = None

        if self.yawn_count >= self.config_yawn_threshold_count:
             status_messages.append(f"Đã ngáp {self.yawn_count} lần")

        # === 4. Xử lý: NGHIÊNG ĐẦU ===
        if abs(roll) > self.config_head_angle_deg:
            msg = f"Nghiêng đầu ({roll:.0f} độ)"
            status_messages.append(msg)
            self.trigger_warning_sound("warning_eye.mp3", cooldown=3.0)

        # === 5. Hiển thị Status Bar ===
        if not status_messages:
            self.status_bar_label.setText("Trạng thái: Đang theo dõi... (An toàn)")
            self.status_bar_label.setStyleSheet("color: #95a5a6") 
        else:
            text = " | ".join(status_messages)
            self.status_bar_label.setText("⚠️ " + text)
            if "NGUY HIỂM" in text:
                self.status_bar_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            else:
                self.status_bar_label.setStyleSheet("color: #f39c12; font-weight: bold;")

    def trigger_alert_email(self, subject, message):
        """Gửi email cảnh báo đến người thân"""
        
        # 1. Kiểm tra xem đã nhập email người nhận chưa
        if not self.config_recipient_email:
            print("⚠️ Chưa nhập email người thân trong Cài đặt -> Không gửi mail.")
            return

        current_time = time.time()
        
        # 2. Chặn Spam (60s mới gửi 1 lần)
        EMAIL_COOLDOWN = 60 
        if current_time - self.last_email_time < EMAIL_COOLDOWN:
            return

        self.last_email_time = current_time
        recipient = self.config_recipient_email # Lấy từ cài đặt

        print(f"📧 Đang gửi email tới: {recipient}")
        
        # 3. Gửi trong luồng riêng
        def _send():
            success = send_alert_email(recipient, subject, message)
            # Log kết quả ra console nếu cần
                
        threading.Thread(target=_send, daemon=True).start()
# --- Chạy ứng dụng ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())