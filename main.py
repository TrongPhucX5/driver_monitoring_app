"""
main.py – Điểm khởi động ứng dụng
Chạy giao diện chính, sử dụng các module con trong thư mục /modules
"""

from modules.ui import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
