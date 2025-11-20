"""
sound.py – Phát âm thanh từ file .mp3 trong thư mục assets
"""
import threading
import pygame
from playsound import playsound
import os

import pygame
import os
import threading

class SoundModule:
    def __init__(self):
        # Khởi tạo mixer của pygame
        try:
            pygame.mixer.init()
            self.is_playing = False
        except Exception as e:
            print(f"Lỗi khởi tạo âm thanh: {e}")

    def play_sound(self, filename="sound.mp3", loop=False):
        """
        Phát âm thanh.
        loop=True: Phát lặp lại (cho chế độ báo động căng)
        """
        def _run():
            try:
                sound_path = os.path.join("assets", filename)
                if not os.path.exists(sound_path):
                    print(f"⚠️ Không tìm thấy file: {sound_path}")
                    return

                if pygame.mixer.music.get_busy():
                    # Nếu đang phát bài khác thì thôi, hoặc dừng bài cũ tùy logic
                    # Ở đây ta dừng bài cũ để ưu tiên bài mới
                    pygame.mixer.music.stop()

                pygame.mixer.music.load(sound_path)
                
                # play(-1) là lặp vô tận, play(0) là 1 lần
                loops = -1 if loop else 0
                pygame.mixer.music.play(loops=loops)
                
            except Exception as e:
                print(f"Lỗi phát nhạc: {e}")

        # Chạy trên luồng chính hoặc luồng phụ đều được với pygame, 
        # nhưng để an toàn giao diện ta cứ bọc thread
        threading.Thread(target=_run, daemon=True).start()

    def stop_sound(self):
        """Dừng phát âm thanh ngay lập tức"""
        try:
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"Lỗi dừng nhạc: {e}")
