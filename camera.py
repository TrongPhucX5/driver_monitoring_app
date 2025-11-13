"""
Camera Module - Nhận diện khuôn mặt, mắt, miệng
Sử dụng OpenCV Haar Cascades
"""

import cv2
import numpy as np
from datetime import datetime
import time
from modules.sound import SoundModule
from modules.email_alert import send_alert_email

class CameraModule:
    """Module xử lý camera và nhận diện khuôn mặt"""
    
    def __init__(self):
        # Khởi tạo các Haar Cascade classifiers
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        # Camera object
        self.cap = None
        self.is_running = False
        
        # Tracking variables cho cảnh báo
        self.closed_eyes_frames = 0
        self.no_face_frames = 0
        self.ALERT_THRESHOLD = 20  # 20 frames liên tiếp (~0.67 giây ở 30fps)
        
        # Statistics
        self.total_frames = 0
        self.alert_count = 0
        
    def start_camera(self, camera_id=0):
        """
        Khởi động camera
        Args:
            camera_id: ID của camera (0 là camera mặc định)
        Returns:
            bool: True nếu khởi động thành công
        """
        try:
            self.cap = cv2.VideoCapture(camera_id)
            
            if not self.cap.isOpened():
                print(f"Không thể mở camera ID: {camera_id}")
                return False
            
            # Cấu hình camera
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.is_running = True
            print("✓ Camera đã sẵn sàng")
            return True
            
        except Exception as e:
            print(f"Lỗi khởi động camera: {str(e)}")
            return False
    
    def detect_features(self, frame):
        """
        Phát hiện khuôn mặt, mắt và đánh giá trạng thái
        Args:
            frame: Frame từ camera (numpy array)
        Returns:
            tuple: (processed_frame, detection_data)
        """
        if frame is None:
            return None, None
        
        # Chuyển sang grayscale để xử lý nhanh hơn
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Phát hiện khuôn mặt
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        # Khởi tạo dữ liệu phát hiện
        detection_data = {
            'faces': len(faces),
            'eyes': 0,
            'alert_type': None,  # None, 'no_face', 'closed_eyes', 'drowsy'
            'alert_level': 0,  # 0: OK, 1: Warning, 2: Danger
            'timestamp': datetime.now(),
            'frame_number': self.total_frames
        }
        
        # Xử lý từng khuôn mặt
        for (x, y, w, h) in faces:
            # Vẽ hình chữ nhật cho khuôn mặt
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, 'Face', (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # ROI (Region of Interest) cho mắt
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]
            
            # Phát hiện mắt
            eyes = self.eye_cascade.detectMultiScale(
                roi_gray,
                scaleFactor=1.1,
                minNeighbors=10,
                minSize=(20, 20)
            )
            
            detection_data['eyes'] += len(eyes)
            
            # Vẽ hình chữ nhật cho mắt
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)
                cv2.putText(roi_color, 'Eye', (ex, ey-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
            
            # Phát hiện vùng miệng (dưới nửa khuôn mặt)
            mouth_roi_y = int(h * 0.6)
            mouth_roi = roi_color[mouth_roi_y:h, :]
            
            # Vẽ vùng miệng đơn giản
            mouth_x = int(w * 0.3)
            mouth_y = mouth_roi_y + int(h * 0.1)
            mouth_w = int(w * 0.4)
            mouth_h = int(h * 0.15)
            cv2.rectangle(roi_color, 
                         (mouth_x, mouth_y), 
                         (mouth_x + mouth_w, mouth_y + mouth_h), 
                         (0, 0, 255), 2)
            cv2.putText(roi_color, 'Mouth', (mouth_x, mouth_y-5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        
        # Đánh giá trạng thái và cảnh báo
        detection_data = self._evaluate_driver_state(detection_data)
        
        # Vẽ trạng thái lên frame
        self._draw_status(frame, detection_data)
        
        self.total_frames += 1
        return frame, detection_data
    
    def _evaluate_driver_state(self, data):
        """
        Đánh giá trạng thái tài xế dựa trên dữ liệu phát hiện
        """
        # Không phát hiện khuôn mặt
        if data['faces'] == 0:
            self.no_face_frames += 1
            self.closed_eyes_frames = 0
            
            if self.no_face_frames > self.ALERT_THRESHOLD:
                data['alert_type'] = 'no_face'
                data['alert_level'] = 2
                self.alert_count += 1
            elif self.no_face_frames > self.ALERT_THRESHOLD // 2:
                data['alert_type'] = 'no_face'
                data['alert_level'] = 1
        
        # Phát hiện khuôn mặt nhưng không có mắt (mắt đóng)
        elif data['faces'] > 0 and data['eyes'] < 2:
            self.closed_eyes_frames += 1
            self.no_face_frames = 0
            
            if self.closed_eyes_frames > self.ALERT_THRESHOLD:
                data['alert_type'] = 'closed_eyes'
                data['alert_level'] = 2
                self.alert_count += 1
            elif self.closed_eyes_frames > self.ALERT_THRESHOLD // 2:
                data['alert_type'] = 'drowsy'
                data['alert_level'] = 1
        
        # Trạng thái bình thường
        else:
            self.closed_eyes_frames = 0
            self.no_face_frames = 0
            data['alert_level'] = 0
        
        return data
    
    def _draw_status(self, frame, data):
        """Vẽ thông tin trạng thái lên frame"""
        h, w = frame.shape[:2]
        
        # Background cho text
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        
        # Thông tin cơ bản
        cv2.putText(frame, f"Khuon mat: {data['faces']}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Mat: {data['eyes']}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Frames: {self.total_frames}", (10, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Cảnh báo
        if data['alert_level'] > 0:
            alert_messages = {
                'no_face': 'CANH BAO: Khong phat hien tai xe!',
                'closed_eyes': 'NGUY HIEM: Tai xe dang ngu gat!',
                'drowsy': 'CHU Y: Tai xe co dau hieu buon ngu'
            }
            
            message = alert_messages.get(data['alert_type'], 'CANH BAO!')
            color = (0, 0, 255) if data['alert_level'] == 2 else (0, 165, 255)
            
            # Cảnh báo nổi bật
            cv2.rectangle(frame, (0, h-80), (w, h), color, -1)
            cv2.putText(frame, message, (w//2 - 250, h-40),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
            
            # Biểu tượng cảnh báo
            cv2.circle(frame, (50, h-40), 25, (255, 255, 255), -1)
            cv2.putText(frame, '!', (43, h-25),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)
    
    def get_frame(self):
        """
        Lấy frame hiện tại từ camera và xử lý
        Returns:
            tuple: (processed_frame, detection_data)
        """
        if not self.is_running or self.cap is None:
            return None, None
        
        ret, frame = self.cap.read()
        if not ret:
            print("Không thể đọc frame từ camera")
            return None, None
        
        return self.detect_features(frame)
    
    def get_statistics(self):
        """Lấy thống kê"""
        return {
            'total_frames': self.total_frames,
            'alert_count': self.alert_count,
            'uptime': time.time()
        }
    
    def release(self):
        """Giải phóng tài nguyên camera"""
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()
        print("✓ Đã dừng camera")


# Test code
if __name__ == "__main__":
    print("Testing Camera Module...")
    camera = CameraModule()
    
    if camera.start_camera():
        print("Nhấn 'q' để thoát")
        
        while True:
            frame, data = camera.get_frame()
            
            if frame is not None:
                cv2.imshow('Driver Monitor Test', frame)
                
                if data and data['alert_level'] > 0:
                    print(f"⚠️  Alert: {data['alert_type']} - Level: {data['alert_level']}")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        camera.release()
    else:
        print("❌ Không thể khởi động camera")



        # Test code
if __name__ == "__main__":
    print("Testing Camera Module...")
    camera = CameraModule()
    
    # Khởi tạo module âm thanh
    sound = SoundModule()

    # Cấu hình email người nhận
    RECIPIENT_EMAIL = "manager-email@example.com" # Thay bằng email quản lý

    # Biến theo dõi cooldown để tránh spam
    SOUND_COOLDOWN = 5  # Giây - 5 giây phát âm thanh 1 lần
    EMAIL_COOLDOWN = 300 # Giây - 5 phút gửi email 1 lần
    
    last_sound_alert = 0
    last_email_alert = 0
    
    if camera.start_camera():
        print("Nhấn 'q' để thoát")
        
        while True:
            frame, data = camera.get_frame()
            
            if frame is not None:
                cv2.imshow('Driver Monitor Test', frame)
                
                # ---- TÍCH HỢP CẢNH BÁO ----
                current_time = time.time()
                
                if data and data['alert_level'] > 0:
                    # 1. Cảnh báo Âm thanh (bất kỳ cảnh báo nào)
                    if (current_time - last_sound_alert) > SOUND_COOLDOWN:
                        print("🔊 Kích hoạt cảnh báo âm thanh...")
                        try:
                            # Chạy âm thanh ở thread riêng để không block
                            # (Nếu playsound bị treo, cần dùng thư viện khác như pygame.mixer)
                            # Đơn giản nhất là gọi trực tiếp:
                            sound.play_sound() 
                        except Exception as e:
                            print(f"Lỗi phát âm thanh: {e}")
                        last_sound_alert = current_time

                    # 2. Cảnh báo Email (chỉ khi nguy hiểm cấp 2)
                    if data['alert_level'] == 2 and (current_time - last_email_alert) > EMAIL_COOLDOWN:
                        print("📧 Kích hoạt gửi email cảnh báo...")
                        subject = f"[NGUY HIỂM] Tài xế có dấu hiệu ngủ gật!"
                        body = (
                            f"Phát hiện tài xế có dấu hiệu nguy hiểm (mã: {data['alert_type']})\n"
                            f"Vào lúc: {data['timestamp']}\n"
                            f"Vui lòng kiểm tra ngay lập tức."
                        )
                        # Gửi email (hàm này đã chạy nền, không cần thread)
                        send_alert_email(RECIPIENT_EMAIL, subject, body)
                        last_email_alert = current_time
                # -----------------------------
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        camera.release()
    else:
        print("❌ Không thể khởi động camera")