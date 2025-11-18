"""
modules/camera.py
Module Camera Thông Minh (Phiên bản PyQt5 chuẩn)
"""
import cv2
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QFormLayout, QComboBox, QSpinBox, QPushButton

# Import thư viện xử lý khuôn mặt
try:
    from modules.face_processor import FaceProcessor
except ImportError:
    import sys
    sys.path.append("..")
    from modules.face_processor import FaceProcessor

class VideoCaptureThread(QThread):
    # Các tín hiệu gửi ra ngoài giao diện
    change_pixmap_signal = pyqtSignal(np.ndarray) 
    detection_data_signal = pyqtSignal(dict)      
    status_changed = pyqtSignal(str)              

    def __init__(self, source=0, width=640, height=480, config=None):
        super().__init__()
        self.source = source
        self.width = width
        self.height = height
        self._run_flag = True
        self.processor = None
        
        # Biến điều khiển vẽ lưới (Mặc định tắt)
        self.show_mesh = False
        self.is_sunglasses_mode = False

        # Nhận cấu hình từ Main Window
        self.config = config if config else {}
        
        # Thiết lập ngưỡng mặc định
        self.EYE_AR_THRESH = 0.25      
        self.MAR_THRESH = 0.5          
        
        # Tính toán số frame dựa trên giây (Giả sử 30 FPS)
        eye_time = self.config.get('eye_time', 2.0)
        self.EYE_AR_CONSEC_FRAMES = int(eye_time * 25) 
        self.EYE_AR_SOS_FRAMES = self.EYE_AR_CONSEC_FRAMES * 2
        
        self.yawn_thresh_count = self.config.get('yawn_threshold', 3)

        # Biến đếm trạng thái
        self.counter_eye = 0     
        self.counter_mouth = 0
        self.counter_distract = 0
        self.total_yawns = 0     
        self.yawn_status = False 

    def set_draw_mesh(self, enabled):
        self.show_mesh = enabled
        
    def set_sunglasses_mode(self, enabled): 
        self.is_sunglasses_mode = enabled

    def update_config(self, new_config):
        """Cập nhật nóng cài đặt khi đang chạy"""
        self.config = new_config
        if 'eye_time' in new_config:
            self.EYE_AR_CONSEC_FRAMES = int(new_config['eye_time'] * 25)
            self.EYE_AR_SOS_FRAMES = self.EYE_AR_CONSEC_FRAMES * 2
        if 'yawn_threshold' in new_config:
            self.yawn_thresh_count = new_config['yawn_threshold']
        print(f"📷 Camera config updated: {new_config}")

    def run(self):
        try:
            self.processor = FaceProcessor()
            self.status_changed.emit("Đã tải AI Model...")
        except Exception as e:
            self.status_changed.emit(f"Lỗi AI: {e}")
            return

        src = int(self.source) if str(self.source).isdigit() else self.source
        
        # --- FIX LỖI ĐƠ CAMERA TRÊN WINDOWS ---
        if isinstance(src, int):
            cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(src)

        if not cap.isOpened():
            self.status_changed.emit("Không thể mở Camera!")
            return

        self.status_changed.emit("Đang giám sát...")

        while self._run_flag:
            ret, frame = cap.read()
            if not ret:
                self.status_changed.emit("Mất tín hiệu.")
                break

            if isinstance(src, int):
                frame = cv2.flip(frame, 1)
            
            if self.width:
                frame = cv2.resize(frame, (self.width, self.height))

            # 1. Xử lý AI
            annotated_frame, data = self.processor.process_frame(frame, draw=self.show_mesh)

            # 2. Logic cảnh báo
            self._process_logic(data, annotated_frame)

            # 3. Gửi dữ liệu đi
            self.change_pixmap_signal.emit(annotated_frame)
            self.detection_data_signal.emit(data)
            
            time.sleep(0.02) 

        cap.release()
        if self.processor:
            self.processor.close()
        self.status_changed.emit("Đã dừng.")

    def _process_logic(self, data, frame):
        """Logic xác định cấp độ cảnh báo"""
        if not data["face_found"]:
            self.counter_eye = 0
            return

        ear = data['ear']; mar = data['mar']
        pitch = data['pitch']; yaw = data['yaw']
        h, w, _ = frame.shape
        
        alert_level = 0; alert_msg = ""

        # 1. XAO NHÃNG
        if abs(yaw) > 30 or pitch > 25:
            self.counter_distract += 1
            if self.counter_distract > 15:
                alert_level = 2; alert_msg = "TẬP TRUNG LÁI XE!"
                cv2.putText(frame, "QUAY MAT DI DAU?", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
        else:
            self.counter_distract = 0

        # 2. MẮT & BUỒN NGỦ
        if self.counter_distract == 0:
            if self.is_sunglasses_mode: # Chế độ kính râm
                cv2.putText(frame, "MODE: KINH RAM", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
                if pitch > 20: self.counter_eye += 1
                else: self.counter_eye = max(0, self.counter_eye - 1)
            else: # Chế độ thường
                if ear < self.EYE_AR_THRESH: self.counter_eye += 1
                else: self.counter_eye = 0

            # Đánh giá cấp độ
            if self.counter_eye >= self.EYE_AR_SOS_FRAMES:
                alert_level = 4; alert_msg = "SOS: NGỦ GẬT QUÁ LÂU!"
                cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 0), 20) 
                cv2.putText(frame, "SOS !!!", (50, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 5)
            elif self.counter_eye >= self.EYE_AR_CONSEC_FRAMES:
                alert_level = 3; alert_msg = "NGUY HIỂM: TỈNH DẬY!"
                cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 10) 
                cv2.putText(frame, "TINH DAY !!!", (50, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 4)
            elif self.counter_eye >= self.EYE_AR_CONSEC_FRAMES // 2:
                if alert_level < 2: alert_level = 2; alert_msg = "Cảnh báo: Mắt lờ đờ..."
                cv2.rectangle(frame, (0, 0), (w, h), (0, 165, 255), 5)

        # 3. NGÁP
        if mar > self.MAR_THRESH:
            self.counter_mouth += 1
            if self.counter_mouth > 20:
                if not self.yawn_status:
                    self.yawn_status = True; self.total_yawns += 1
                cv2.putText(frame, "NGAP", (w - 150, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                if alert_level < 1: alert_level = 1; alert_msg = "Phát hiện ngáp"
        else:
            self.counter_mouth = 0; self.yawn_status = False

        data['alert_level'] = alert_level
        data['alert_msg'] = alert_msg

    def stop(self):
        self._run_flag = False
        self.wait()

class SettingsDialog(QDialog):
    def __init__(self, parent=None, current_source='0', width=640, height=480):
        super().__init__(parent)
        self.setWindowTitle("Cài đặt Camera")
        layout = QFormLayout(self)
        self.source_input = QComboBox(); self.source_input.addItems(['0', '1', '2']); self.source_input.setEditable(True); self.source_input.setCurrentText(str(current_source))
        layout.addRow("Nguồn:", self.source_input)
        self.w_input = QSpinBox(); self.w_input.setRange(320, 1920); self.w_input.setValue(width); layout.addRow("Rộng:", self.w_input)
        self.h_input = QSpinBox(); self.h_input.setRange(240, 1080); self.h_input.setValue(height); layout.addRow("Cao:", self.h_input)
        btn = QPushButton("Lưu"); btn.clicked.connect(self.accept); layout.addRow(btn)
    def values(self): return self.source_input.currentText(), self.w_input.value(), self.h_input.value()