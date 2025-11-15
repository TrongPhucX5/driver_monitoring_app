"""
Module Xử lý Khuôn mặt
Sử dụng MediaPipe Face Mesh để phát hiện landmarks
và tính toán các chỉ số (EAR, MAR, Head Pose).
"""

import cv2
import mediapipe as mp
import numpy as np
import math

# --- Định nghĩa các chỉ số landmark quan trọng (lấy từ sơ đồ của MediaPipe) ---

# 6 điểm để tính Eye Aspect Ratio (EAR)
# Mắt phải (của người dùng, bên trái ảnh)
RIGHT_EYE_EAR_POINTS = [33, 159, 145, 133, 158, 153]
# Mắt trái (của người dùng, bên phải ảnh)
LEFT_EYE_EAR_POINTS = [263, 386, 374, 362, 385, 380]

# 4 điểm để tính Mouth Aspect Ratio (MAR) - dùng môi trong
# Trên (13), Dưới (14), Trái (78), Phải (308)
MOUTH_MAR_POINTS = [13, 14, 78, 308] 

# 6 điểm để ước tính 3D Pose (Góc đầu)
# Dùng các điểm cố định trên khuôn mặt
POSE_LANDMARKS = [
    1,   # chóp mũi
    152, # cằm
    33,  # khóe mắt trái (của người dùng)
    263, # khóe mắt phải (của người dùng)
    61,  # khóe miệng trái (của người dùng)
    291  # khóe miệng phải (của người dùng)
]

class FaceProcessor:
    def __init__(self):
        """Khởi tạo MediaPipe Face Mesh"""
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_face_mesh = mp.solutions.face_mesh

        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,            # Chỉ xử lý 1 khuôn mặt (người lái xe)
            refine_landmarks=True,      # Bật để lấy landmark chi tiết cho mắt/môi
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Thông số vẽ lưới (màu xám mờ)
        self.mesh_drawing_spec = self.mp_drawing.DrawingSpec(
            color=(200, 200, 200), 
            thickness=1, 
            circle_radius=1
        )

    def _get_landmark_coords(self, frame, face_landmarks, indices):
        """Helper: Lấy toạ độ (x, y) pixel từ list các chỉ số (indices)"""
        h, w, _ = frame.shape
        coords = []
        for idx in indices:
            lm = face_landmarks.landmark[idx]
            x = int(lm.x * w)
            y = int(lm.y * h)
            coords.append((x, y))
        return coords

    def _calculate_euclidean_dist(self, p1, p2):
        """Tính khoảng cách Euclidean giữa 2 điểm (x, y)"""
        return math.dist(p1, p2)

    def _calculate_ear(self, eye_points):
        """
        Tính Eye Aspect Ratio (EAR) từ 6 điểm landmark của mắt.
        EAR = (||P2 - P6|| + ||P3 - P5||) / (2 * ||P1 - P4||)
        """
        p1, p2, p3, p4, p5, p6 = eye_points
        
        vertical_dist_1 = self._calculate_euclidean_dist(p2, p6)
        vertical_dist_2 = self._calculate_euclidean_dist(p3, p5)
        horizontal_dist = self._calculate_euclidean_dist(p1, p4)

        if horizontal_dist == 0:
            return 0.0
            
        ear = (vertical_dist_1 + vertical_dist_2) / (2.0 * horizontal_dist)
        return ear

    def _calculate_mar(self, mouth_points):
        """
        Tính Mouth Aspect Ratio (MAR) từ 4 điểm (trên, dưới, trái, phải).
        MAR = ||P_top - P_bottom|| / ||P_left - P_right||
        """
        p_top, p_bottom, p_left, p_right = mouth_points
        
        vertical_dist = self._calculate_euclidean_dist(p_top, p_bottom)
        horizontal_dist = self._calculate_euclidean_dist(p_left, p_right)

        if horizontal_dist == 0:
            return 0.0
            
        mar = vertical_dist / horizontal_dist
        return mar

    def _get_head_pose(self, frame, face_landmarks):
        """
        Ước tính góc quay 3D của đầu (Pitch, Yaw, Roll)
        sử dụng cv2.solvePnP.
        """
        h, w, _ = frame.shape
        
        # 1. Lấy tọa độ 2D của các điểm POSE_LANDMARKS
        image_points = np.array(
            self._get_landmark_coords(frame, face_landmarks, POSE_LANDMARKS), 
            dtype="double"
        )
        
        # 2. Tọa độ 3D (mô hình chung, không cần chính xác tuyệt đối)
        model_points = np.array([
            (0.0, 0.0, 0.0),             # Chóp mũi
            (0.0, -330.0, -65.0),        # Cằm
            (-225.0, 170.0, -135.0),     # Khóe mắt trái
            (225.0, 170.0, -135.0),      # Khóe mắt phải
            (-150.0, -150.0, -125.0),    # Khóe miệng trái
            (150.0, -150.0, -125.0)      # Khóe miệng phải
        ])
        
        # 3. Thông số camera (ước tính)
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")
        
        dist_coeffs = np.zeros((4, 1)) # Bỏ qua biến dạng ống kính
        
        # 4. Giải PnP
        try:
            (success, rotation_vector, translation_vector) = cv2.solvePnP(
                model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
            )
            
            # 5. Lấy góc Euler
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            
            # Tính góc pitch, yaw, roll (đơn vị: độ)
            pitch = math.degrees(math.asin(-rotation_matrix[2, 0]))
            yaw = math.degrees(math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
            roll = math.degrees(math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2]))
            
            return pitch, yaw, roll
            
        except Exception:
            # Có thể xảy ra lỗi nếu các điểm thẳng hàng
            return 0.0, 0.0, 0.0


    def process_frame(self, frame):
        """
        Hàm xử lý chính.
        Input: frame (ảnh BGR từ OpenCV)
        Output: (annotated_image, detection_data)
            - annotated_image: ảnh đã vẽ các landmarks (BGR)
            - detection_data: dict chứa các chỉ số
        """
        
        # 1. Chuẩn bị ảnh
        annotated_image = frame.copy()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False # Tối ưu hóa
        
        # 2. Chạy nhận diện
        results = self.face_mesh.process(rgb_frame)
        
        # 3. Khởi tạo dict kết quả
        detection_data = {
            "face_found": False,
            "ear": 0.0,  # Eye Aspect Ratio
            "mar": 0.0,  # Mouth Aspect Ratio
            "roll": 0.0, # Góc nghiêng (trái/phải)
            "pitch": 0.0, # Góc gật gù (lên/xuống)
            "yaw": 0.0   # Góc quay (trái/phải)
        }

        # 4. Xử lý kết quả nếu tìm thấy khuôn mặt
        if results.multi_face_landmarks:
            detection_data["face_found"] = True
            face_landmarks = results.multi_face_landmarks[0] # Lấy mặt đầu tiên
            
            # Vẽ lưới khuôn mặt lên ảnh
            self.mp_drawing.draw_landmarks(
                image=annotated_image,
                landmark_list=face_landmarks,
                connections=self.mp_face_mesh.FACEMESH_TESSELATION,
                landmark_drawing_spec=None,
                connection_drawing_spec=self.mesh_drawing_spec
            )
            
            # --- A. Tính toán EAR (Nhắm mắt) ---
            right_eye_coords = self._get_landmark_coords(frame, face_landmarks, RIGHT_EYE_EAR_POINTS)
            left_eye_coords = self._get_landmark_coords(frame, face_landmarks, LEFT_EYE_EAR_POINTS)
            
            ear_right = self._calculate_ear(right_eye_coords)
            ear_left = self._calculate_ear(left_eye_coords)
            
            # Lấy trung bình EAR của 2 mắt
            avg_ear = (ear_right + ear_left) / 2.0
            detection_data["ear"] = avg_ear

            # --- B. Tính toán MAR (Ngáp) ---
            mouth_coords = self._get_landmark_coords(frame, face_landmarks, MOUTH_MAR_POINTS)
            mar = self._calculate_mar(mouth_coords)
            detection_data["mar"] = mar

            # --- C. Tính toán Head Pose (Nghiêng đầu) ---
            pitch, yaw, roll = self._get_head_pose(frame, face_landmarks)
            detection_data["roll"] = roll
            detection_data["pitch"] = pitch
            detection_data["yaw"] = yaw
            
            # --- D. (Tùy chọn) Vẽ thông tin lên màn hình để debug ---
            cv2.putText(annotated_image, f"EAR: {avg_ear:.2f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated_image, f"MAR: {mar:.2f}", (10, 60), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(annotated_image, f"ROLL: {roll:.1f}", (10, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
        # 5. Trả về ảnh đã vẽ và dữ liệu
        return annotated_image, detection_data

    def close(self):
        """Giải phóng tài nguyên khi đóng ứng dụng"""
        self.face_mesh.close()


# --- Khối main để chạy test file này độc lập ---
if __name__ == "__main__":
    # Đoạn code này chỉ chạy khi bạn thực thi: python face_processor.py
    # Dùng để kiểm tra nhanh module
    
    print("Đang chạy kiểm tra FaceProcessor với MediaPipe...")
    cap = cv2.VideoCapture(0) # Mở webcam
    
    if not cap.isOpened():
        print("Lỗi: Không thể mở webcam.")
        exit()
        
    processor = FaceProcessor()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Lỗi: Không thể đọc frame.")
            break
            
        # Lật ảnh (vì webcam thường bị ngược)
        frame = cv2.flip(frame, 1) 
        
        # Xử lý frame
        annotated_frame, data = processor.process_frame(frame)
        
        if data["face_found"]:
            # In dữ liệu ra terminal
            print(f"EAR: {data['ear']:.2f}, MAR: {data['mar']:.2f}, Roll: {data['roll']:.1f}")
        else:
            print("Không tìm thấy khuôn mặt.")
            
        # Hiển thị ảnh
        cv2.imshow("MediaPipe Face Mesh Test", annotated_frame)
        
        # Nhấn 'q' để thoát
        if cv2.waitKey(5) & 0xFF == ord('q'):
            break
            
    # Dọn dẹp
    cap.release()
    cv2.destroyAllWindows()
    processor.close()
    print("Kiểm tra hoàn tất.")