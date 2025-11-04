"""
sound.py – Phát âm thanh từ file .mp3 trong thư mục assets
"""

from playsound import playsound
import os

class SoundModule:
    def play_sound(self):
        sound_path = os.path.join("assets", "sound.mp3")
        if os.path.exists(sound_path):
            playsound(sound_path)
            print("🔊 Đã phát âm thanh.")
        else:
            print("⚠️ Không tìm thấy file âm thanh:", sound_path)
