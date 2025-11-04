"""
ui.py – Xây dựng giao diện chính bằng CustomTkinter
"""

import customtkinter as ctk
from modules.camera import CameraModule
from modules.sound import SoundModule

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MyApp - Demo OpenCV + Tkinter + Sound")
        self.geometry("600x400")

        # Các module phụ
        self.camera = CameraModule()
        self.sound = SoundModule()

        # Nút điều khiển
        ctk.CTkButton(self, text="📷 Mở Camera", command=self.camera.open_camera).pack(pady=10)
        ctk.CTkButton(self, text="🔊 Phát Âm Thanh", command=self.sound.play_sound).pack(pady=10)
