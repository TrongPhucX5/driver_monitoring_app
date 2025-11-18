"""
modules/face_processor.py
Xử lý khuôn mặt với MediaPipe (Bản Final)
Tính năng:
- Tính toán EAR (Mắt), MAR (Miệng), Head Pose (Đầu)
- Hỗ trợ Bật/Tắt vẽ lưới (draw=True/False)
"""
import cv2
import mediapipe as mp
import numpy as np
import math

# Các điểm landmark quan trọng
RIGHT_EYE = [33, 159, 145, 133, 158, 153]
LEFT_EYE = [263, 386, 374, 362, 385, 380]
MOUTH = [13, 14, 78, 308] 
POSE = [1, 152, 33, 263, 61, 291]

class FaceProcessor:
    def __init__(self):
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_face_mesh = mp.solutions.face_mesh
        
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Style vẽ lưới: Màu xám nhạt, nét mảnh
        self.draw_spec = self.mp_drawing.DrawingSpec(color=(200, 200, 200), thickness=1, circle_radius=1)

    def process_frame(self, frame, draw=True):
        """
        Xử lý frame ảnh.
        Args:
            frame: Ảnh đầu vào từ Camera.
            draw (bool): Nếu True thì vẽ lưới lên mặt, False thì không vẽ.
        Returns:
            annotated_image: Ảnh đã xử lý (có vẽ hoặc không).
            data: Dictionary chứa các chỉ số EAR, MAR, Roll...
        """
        h, w, _ = frame.shape
        
        # Chuyển sang RGB cho MediaPipe xử lý
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.face_mesh.process(rgb_frame)
        rgb_frame.flags.writeable = True
        
        # Tạo bản sao để vẽ (tránh làm hỏng frame gốc nếu cần dùng việc khác)
        annotated_image = frame.copy()
        
        data = {
            "face_found": False,
            "ear": 0.0, "mar": 0.0, 
            "roll": 0.0, "pitch": 0.0, "yaw": 0.0
        }

        if results.multi_face_landmarks:
            data["face_found"] = True
            face_landmarks = results.multi_face_landmarks[0]

            # --- LOGIC VẼ LƯỚI (QUAN TRỌNG) ---
            if draw:
                # Vẽ lưới tam giác (Tesselation)
                self.mp_drawing.draw_landmarks(
                    image=annotated_image,
                    landmark_list=face_landmarks,
                    connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.draw_spec
                )
                # Vẽ viền mắt/môi/khuôn mặt (Contours) - Màu xanh lá cho đẹp
                self.mp_drawing.draw_landmarks(
                    image=annotated_image,
                    landmark_list=face_landmarks,
                    connections=self.mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1)
                )

            # --- TÍNH TOÁN CHỈ SỐ (Luôn thực hiện) ---
            right_eye_coords = self._get_coords(face_landmarks, RIGHT_EYE, w, h)
            left_eye_coords = self._get_coords(face_landmarks, LEFT_EYE, w, h)
            mouth_coords = self._get_coords(face_landmarks, MOUTH, w, h)
            
            ear_right = self._ear(right_eye_coords)
            ear_left = self._ear(left_eye_coords)
            ear = (ear_right + ear_left) / 2.0
            
            mar = self._mar(mouth_coords)
            
            pitch, yaw, roll = self._head_pose(frame, face_landmarks)

            data.update({
                "ear": ear, 
                "mar": mar, 
                "roll": roll, 
                "pitch": pitch, 
                "yaw": yaw
            })

        return annotated_image, data

    def _get_coords(self, landmarks, indices, w, h):
        return [(int(landmarks.landmark[i].x * w), int(landmarks.landmark[i].y * h)) for i in indices]

    def _dist(self, p1, p2):
        return math.dist(p1, p2)

    def _ear(self, pts):
        # EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
        if not pts: return 0.0
        v1 = self._dist(pts[1], pts[5])
        v2 = self._dist(pts[2], pts[4])
        h = self._dist(pts[0], pts[3])
        return (v1 + v2) / (2.0 * h) if h != 0 else 0.0

    def _mar(self, pts):
        # MAR = |top-bottom| / |left-right|
        if not pts: return 0.0
        v = self._dist(pts[0], pts[1])
        h = self._dist(pts[2], pts[3])
        return v / h if h != 0 else 0.0

    def _head_pose(self, frame, landmarks):
        h, w, _ = frame.shape
        
        # Lấy tọa độ 2D
        img_pts = np.array([
            (landmarks.landmark[1].x * w, landmarks.landmark[1].y * h),     # Mũi
            (landmarks.landmark[152].x * w, landmarks.landmark[152].y * h), # Cằm
            (landmarks.landmark[33].x * w, landmarks.landmark[33].y * h),   # Mắt trái
            (landmarks.landmark[263].x * w, landmarks.landmark[263].y * h), # Mắt phải
            (landmarks.landmark[61].x * w, landmarks.landmark[61].y * h),   # Miệng trái
            (landmarks.landmark[291].x * w, landmarks.landmark[291].y * h)  # Miệng phải
        ], dtype="double")
        
        # Mô hình 3D chuẩn
        model_pts = np.array([
            (0.0, 0.0, 0.0), (0.0, -330.0, -65.0), (-225.0, 170.0, -135.0),
            (225.0, 170.0, -135.0), (-150.0, -150.0, -125.0), (150.0, -150.0, -125.0)
        ])
        
        # Ma trận Camera giả lập
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")
        
        dist_coeffs = np.zeros((4, 1)) # Giả sử không biến dạng
        
        try:
            (success, rotation_vector, translation_vector) = cv2.solvePnP(
                model_pts, img_pts, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
            )
            
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            mat = np.hstack((rotation_matrix, translation_vector))
            
            # Tách góc Euler
            # Pitch: Gật gù, Yaw: Quay trái phải, Roll: Nghiêng đầu
            pitch = math.degrees(math.asin(-rotation_matrix[2, 0]))
            yaw = math.degrees(math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
            roll = math.degrees(math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2]))
            
            return pitch, yaw, roll
        except:
            return 0.0, 0.0, 0.0

    def close(self):
        self.face_mesh.close()

if __name__ == "__main__":
    print("Vui lòng chạy file main.py!")