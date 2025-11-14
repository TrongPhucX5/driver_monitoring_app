"""
Camera Module - Nhận diện khuôn mặt, mắt, miệng
Sử dụng OpenCV Haar Cascades
"""

import sys
import cv2
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget,
    QFormLayout, QSpacerItem, QSizePolicy,
    QSlider, QComboBox, QSpinBox  # <-- THÊM QSpinBox
)

# --- Class VideoThread (Không thay đổi, giữ nguyên) ---
class VideoThread(QThread):
    change_pixmap_signal = Signal(QImage)
    def __init__(self, source=0):
        super().__init__()
        self._run_flag = True
        self.source = source
    def run(self):
        cap = cv2.VideoCapture(self.source)
        while self._run_flag and cap.isOpened():
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_Qt_format = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
                )
                self.change_pixmap_signal.emit(convert_to_Qt_format)
        cap.release()
    def stop(self):
        self._run_flag = False
        self.wait()
# --- Hết class VideoThread ---


# --- Cửa sổ chính (Được cập nhật) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hệ thống Giám sát Lái xe")
        self.setGeometry(100, 100, 1024, 768)
        self.video_thread = None

        self.initUI()
        self.apply_styles()
        self.show_monitoring_page()

    def initUI(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 1. Sidebar (Menu bên trái) ---
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(15)

        title_label = QLabel("Giám sát Lái xe")
        title_label.setObjectName("SidebarTitle")
        
        self.menu_giam_sat = QPushButton("Giám sát")
        self.menu_giam_sat.setCursor(Qt.CursorShape.PointingHandCursor) # <-- SỬA LỖI CURSOR
        
        self.menu_tai_khoan = QPushButton("Tài khoản")
        self.menu_tai_khoan.setObjectName("MenuButton")
        self.menu_tai_khoan.setEnabled(False) 
        
        self.btn_cai_dat = QPushButton("Cài đặt cá nhân")
        self.btn_cai_dat.setToolTip("Tùy chỉnh âm thanh và ngưỡng cảnh báo") # Cập nhật tooltip
        self.btn_cai_dat.setObjectName("SettingsButton_Unselected") 
        self.btn_cai_dat.setCursor(Qt.CursorShape.PointingHandCursor) # <-- SỬA LỖI CURSOR

        sidebar_layout.addWidget(title_label)
        sidebar_layout.addSpacing(20)
        sidebar_layout.addWidget(self.menu_giam_sat)
        sidebar_layout.addWidget(self.menu_tai_khoan)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.btn_cai_dat)
        
        main_layout.addWidget(sidebar)

        # --- 2. Main Area (Khu vực nội dung) ---
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

        self.btn_bat_dau.clicked.connect(self.start_video)
        self.btn_dung_lai.clicked.connect(self.stop_video)
        self.menu_giam_sat.clicked.connect(self.show_monitoring_page)
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
        control_layout = QHBoxLayout()
        
        self.btn_bat_dau = QPushButton("BẮT ĐẦU GIÁM SÁT")
        self.btn_bat_dau.setObjectName("StartButton")
        self.btn_bat_dau.setCursor(Qt.CursorShape.PointingHandCursor) # <-- SỬA LỖI CURSOR

        self.btn_dung_lai = QPushButton("DỪNG LẠI")
        self.btn_dung_lai.setObjectName("StopButton")
        self.btn_dung_lai.setEnabled(False)
        self.btn_dung_lai.setCursor(Qt.CursorShape.PointingHandCursor) # <-- SỬA LỖI CURSOR

        control_layout.addStretch()
        control_layout.addWidget(self.btn_bat_dau)
        control_layout.addWidget(self.btn_dung_lai)
        control_layout.addStretch()
        layout.addLayout(control_layout)
        return page_widget

    # *** THAY ĐỔI: HÀM NÀY ĐÃ ĐƯỢC CẬP NHẬT ***
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
        settings_form.setSpacing(15) # Giảm khoảng cách một chút

        # 1. Âm thanh
        self.audio_alert_combo = QComboBox()
        self.audio_alert_combo.addItems(["Tiếng Bíp (Mặc định)", "Giọng nói cảnh báo", "Tắt âm thanh"])
        self.audio_alert_combo.setCursor(Qt.CursorShape.PointingHandCursor) # <-- SỬA LỖI CURSOR
        settings_form.addRow(QLabel("Âm thanh cảnh báo:"), self.audio_alert_combo)

        # 2. Độ nhạy (từ code bạn cung cấp)
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(1, 10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sensitivity_slider.setTickInterval(1)
        self.sensitivity_slider.setCursor(Qt.CursorShape.PointingHandCursor) # <-- SỬA LỖI CURSOR
        settings_form.addRow(QLabel("Độ nhạy chung:"), self.sensitivity_slider)
        
        # --- THÊM CÁC NGƯỠNG KÍCH HOẠT ---
        
        # 3. Ngưỡng ngáp
        self.yawn_threshold_spinbox = QSpinBox()
        self.yawn_threshold_spinbox.setRange(1, 10) # Cho phép 1-10 lần ngáp
        self.yawn_threshold_spinbox.setValue(3)     # Mặc định là 3
        self.yawn_threshold_spinbox.setSuffix(" lần")
        self.yawn_threshold_spinbox.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Ngưỡng ngáp:"), self.yawn_threshold_spinbox)
        
        # 4. Ngưỡng nhắm mắt
        self.eye_time_spinbox = QSpinBox()
        self.eye_time_spinbox.setRange(1, 10) # Cho phép 1-10 giây
        self.eye_time_spinbox.setValue(2)     # Mặc định là 2 giây
        self.eye_time_spinbox.setSuffix(" giây")
        self.eye_time_spinbox.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Nhắm mắt quá:"), self.eye_time_spinbox)
        
        # 5. Ngưỡng nghiêng đầu
        self.head_angle_spinbox = QSpinBox()
        self.head_angle_spinbox.setRange(10, 45) # 10-45 độ
        self.head_angle_spinbox.setValue(20)     # Mặc định 20 độ
        self.head_angle_spinbox.setSuffix(" độ")
        self.head_angle_spinbox.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_form.addRow(QLabel("Đầu nghiêng quá:"), self.head_angle_spinbox)

        # Nút Lưu
        btn_save = QPushButton("LƯU CÀI ĐẶT")
        btn_save.setObjectName("StartButton")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor) # <-- SỬA LỖI CURSOR

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

    # --- Các hàm xử lý video (Không thay đổi) ---
    @Slot()
    def start_video(self):
        if self.video_thread is not None:
            self.video_thread.stop()
        self.video_thread = VideoThread(source=0) 
        self.video_thread.change_pixmap_signal.connect(self.update_image)
        self.video_thread.start()
        self.btn_bat_dau.setEnabled(False)
        self.btn_dung_lai.setEnabled(True)
        self.video_label.setText("")

    @Slot()
    def stop_video(self):
        if self.video_thread:
            self.video_thread.stop()
            self.video_thread = None
        self.btn_bat_dau.setEnabled(True)
        self.btn_dung_lai.setEnabled(False)
        self.video_label.setText("No video")

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

    def apply_styles(self):
        # *** THAY ĐỔI: ĐÃ XÓA TẤT CẢ 'cursor:' KHỎI QSS ***
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


# --- Chạy ứng dụng ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())