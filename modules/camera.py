"""
camera.py – Quản lý việc bật/tắt camera, chụp ảnh bằng OpenCV
"""

import cv2

class CameraModule:
    def open_camera(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Không thể mở camera")
            return

        print("📸 Nhấn Q để thoát camera")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        print("✅ Camera đã tắt")
