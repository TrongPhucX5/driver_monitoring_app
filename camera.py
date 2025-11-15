"""
Camera Module - Tích hợp MediaPipe Face Processor
Sử dụng PySide6 cho GUI và MediaPipe để xử lý
"""

import sys
import cv2
import time  # --- MỚI ---: Cần để theo dõi thời gian (nhắm mắt, ngáp)

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget,
    QFormLayout, QSpacerItem, QSizePolicy,
    QSlider, QComboBox, QSpinBox
)

# --- MỚI ---: Import FaceProcessor từ file face_processor.py
try:
    from modules.face_processor import FaceProcessor
except ImportError:
    print("Lỗi: Không tìm thấy file 'face_processor.py'.")
    print("Hãy đảm bảo file đó nằm cùng thư mục với 'camera.py'.")
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

        # --- MỚI ---: Khởi tạo các biến cấu hình và trạng thái
        self.init_config_vars()
        self.init_state_vars()

        self.initUI()
        self.apply_styles()
        self.show_monitoring_page()

    # --- MỚI ---: Hàm khởi tạo các biến CẤU HÌNH (settings)
    def init_config_vars(self):
        """Lưu trữ các giá trị ngưỡng từ trang Cài đặt"""
        
        # Ngưỡng vật lý (nội bộ, không đổi)
        # Giá trị EAR dưới đây là mắt nhắm
        self.INTERNAL_EAR_THRESHOLD = 0.25 
        # Giá trị MAR trên đây là đang ngáp
        self.INTERNAL_MAR_THRESHOLD = 0.5   
        # Thời gian (giây) để reset bộ đếm ngáp nếu không ngáp nữa
        self.INTERNAL_YAWN_RESET_TIME_SEC = 60 
        
        # Ngưỡng do người dùng cài đặt (lấy từ giá trị mặc định của SpinBox)
        self.config_yawn_threshold_count = 3  # (lần)
        self.config_eye_time_sec = 2          # (giây)
        self.config_head_angle_deg = 20       # (độ)

    # --- MỚI ---: Hàm khởi tạo các biến TRẠNG THÁI (state)
    def init_state_vars(self):
        """Reset các biến theo dõi trạng thái (dùng khi bắt đầu/dừng)"""
        self.eye_closed_start_time = None
        self.is_yawning_state = False # Trạng thái đang ngáp (để đếm 1 lần)
        self.yawn_count = 0
        self.last_yawn_time = None

    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar (Không thay đổi)
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
        self.menu_tai_khoan.setEnabled(False)
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

        # 2. Main Area (Không thay đổi cấu trúc)
        main_area = QWidget()
        main_area.setObjectName("MainArea")
        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(20, 20, 20, 10)
        main_area_layout.setSpacing(10)
        self.stacked_widget = QStackedWidget()
        
        monitoring_page = self.create_monitoring_page() # Index 0
        settings_page = self.create_settings_page()     # Index 1

        self.stacked_widget.addWidget(monitoring_page)
        self.stacked_widget.addWidget(settings_page)
        main_area_layout.addWidget(self.stacked_widget)

        self.status_bar_label = QLabel("Trạng thái: Idle (User: GX6dYP8C63db3jEVACfvmw3uJDH2)")
        self.status_bar_label.setObjectName("StatusBar")
        self.status_bar_label.setFixedHeight(25)
        
        main_area_layout.addWidget(self.status_bar_label)
        main_layout.addWidget(main_area, 1)

        # Kết nối sự kiện (Không thay đổi)
        self.btn_bat_dau.clicked.connect(self.start_video)
        self.btn_dung_lai.clicked.connect(self.stop_video)
        self.menu_giam_sat.clicked.connect(self.show_monitoring_page)
        self.btn_cai_dat.clicked.connect(self.show_settings_page)

    def create_monitoring_page(self):
        # (Không thay đổi)
        page_widget = QWidget()
        layout = QVBoxLayout(page_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.video_label = QLabel("No video")
        self.video_label.setObjectName("VideoLabel")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        layout.addWidget(self.video_label, 1)
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

    # --- HÀM create_settings_page (ĐÃ CẬP NHẬT) ---
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

        # 1. Âm thanh
        self.audio_alert_combo = QComboBox()
        self.audio_alert_combo.addItems(["Tiếng Bíp (Mặc định)", "Giọng nói cảnh báo", "Tắt âm thanh"])
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

    # --- Các hàm chuyển trang (Không thay đổi) ---
    @Slot()
    def show_monitoring_page(self):
        self.stacked_widget.setCurrentIndex(0)
        self.menu_giam_sat.setObjectName("SelectedMenuButton")
        self.btn_cai_dat.setObjectName("SettingsButton_Unselected")
        self.refresh_styles()

    @Slot()
    def show_settings_page(self):
        self.stacked_widget.setCurrentIndex(1)
        self.menu_giam_sat.setObjectName("MenuButton")
        self.btn_cai_dat.setObjectName("SettingsButton_Selected")
        self.refresh_styles()

    def refresh_styles(self):
        self.style().unpolish(self.menu_giam_sat)
        self.style().polish(self.menu_giam_sat)
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
        # (Không thay đổi)
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(pixmap)

    def closeEvent(self, event):
        # (Không thay đổi)
        self.stop_video()
        event.accept()

    # --- HÀM apply_styles (Không thay đổi) ---
    def apply_styles(self):
        style_sheet = """
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
            QComboBox {
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
            
            QSpinBox {
                background-color: #2c3e50;
                border: 1px solid #7f8c8d;
                padding: 8px;
                border-radius: 4px;
                font-size: 14px;
                color: white;
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
        """
        self.setStyleSheet(style_sheet)
        
    
    # --- MỚI ---: Hàm lưu cài đặt
    @Slot()
    def save_settings(self):
        """Đọc giá trị từ SpinBox và lưu vào biến config"""
        self.config_yawn_threshold_count = self.yawn_threshold_spinbox.value()
        self.config_eye_time_sec = self.eye_time_spinbox.value()
        self.config_head_angle_deg = self.head_angle_spinbox.value()
        
        # (Tùy chọn) Cập nhật độ nhạy từ slider
        # sensitivity = self.sensitivity_slider.value()
        # Ví dụ: Điều chỉnh ngưỡng nội bộ dựa trên độ nhạy
        # self.INTERNAL_EAR_THRESHOLD = 0.25 - (sensitivity - 5) * 0.01 
        
        print("--- CÀI ĐẶT ĐÃ LƯU ---")
        print(f"Ngưỡng ngáp: {self.config_yawn_threshold_count} lần")
        print(f"Ngưỡng nhắm mắt: {self.config_eye_time_sec} giây")
        print(f"Ngưỡng nghiêng đầu: {self.config_head_angle_deg} độ")
        
        # Cập nhật thanh trạng thái (tạm thời)
        original_text = self.status_bar_label.text()
        self.status_bar_label.setText("Trạng thái: Đã lưu cài đặt!")
        
        # Tạo hiệu ứng thông báo ngắn
        QTimer.singleShot(2000, lambda: self.status_bar_label.setText(original_text))


    # --- MỚI ---: Hàm xử lý dữ liệu từ VideoThread
    @Slot(dict)
    def handle_detection_data(self, data):
        """
        Đây là "bộ não" của ứng dụng.
        Nhận dữ liệu (EAR, MAR, Roll) và kích hoạt cảnh báo.
        """
        if not data["face_found"]:
            self.status_bar_label.setText("Trạng thái: Không tìm thấy khuôn mặt...")
            # Reset trạng thái nếu mất mặt
            self.init_state_vars() 
            return

        current_time = time.time()
        ear = data["ear"]
        mar = data["mar"]
        roll = data["roll"]

        status_messages = [] # Danh sách các cảnh báo

        # === 1. Xử lý Nghiêng đầu (Đơn giản nhất) ===
        if abs(roll) > self.config_head_angle_deg:
            msg = f"CẢNH BÁO: NGHIÊNG ĐẦU ({roll:.0f} độ)"
            status_messages.append(msg)
            # TODO: Phát âm thanh cảnh báo

        # === 2. Xử lý Nhắm mắt (EAR) ===
        if ear < self.INTERNAL_EAR_THRESHOLD:
            # Mắt đang nhắm
            if self.eye_closed_start_time is None:
                # Bắt đầu đếm
                self.eye_closed_start_time = current_time
            else:
                # Đã nhắm được 1 lúc, kiểm tra thời gian
                duration = current_time - self.eye_closed_start_time
                if duration > self.config_eye_time_sec:
                    # Vượt ngưỡng
                    msg = f"CẢNH BÁO: BUỒN NGỦ (Nhắm {duration:.1f}s)"
                    status_messages.append(msg)
                    # TODO: Phát âm thanh cảnh báo
                else:
                    # Đang nhắm nhưng chưa đủ lâu
                    status_messages.append(f"Nhắm mắt {duration:.1f}s...")
        else:
            # Mắt đang mở, reset bộ đếm
            self.eye_closed_start_time = None

        # === 3. Xử lý Ngáp (MAR) ===
        
        # Reset bộ đếm ngáp sau 1 phút không ngáp
        if self.last_yawn_time and (current_time - self.last_yawn_time > self.INTERNAL_YAWN_RESET_TIME_SEC):
            self.yawn_count = 0
            self.last_yawn_time = None
        
        if mar > self.INTERNAL_MAR_THRESHOLD:
            # Miệng đang mở (đủ lớn để coi là ngáp)
            if not self.is_yawning_state:
                # Đây là frame đầu tiên của hành động ngáp -> đếm 1 lần
                self.is_yawning_state = True
                self.yawn_count += 1
                self.last_yawn_time = current_time # Cập nhật thời điểm ngáp cuối
        else:
            # Miệng đã đóng lại, reset trạng thái "đang ngáp"
            self.is_yawning_state = False

        # Hiển thị số lần ngáp nếu > 0
        if self.yawn_count > 0:
            msg = f"Đã ngáp: {self.yawn_count} lần"
            status_messages.append(msg)

        # Kiểm tra nếu vượt ngưỡng ngáp
        if self.yawn_count >= self.config_yawn_threshold_count:
            msg = f"CẢNH BÁO: MỆT MỎI (Ngáp {self.yawn_count} lần)"
            status_messages.append(msg)
            # TODO: Phát âm thanh cảnh báo

        # === 4. Cập nhật Status Bar ===
        if not status_messages:
            self.status_bar_label.setText("Trạng thái: Đang theo dõi... (Bình thường)")
        else:
            # Nối tất cả các cảnh báo lại
            self.status_bar_label.setText("Trạng thái: " + " | ".join(status_messages))


# --- Chạy ứng dụng ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())