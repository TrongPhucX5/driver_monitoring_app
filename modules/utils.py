"""
utils.py – Hàm phụ trợ (ghi log, xử lý đường dẫn, v.v.)
"""

import datetime

def write_log(message: str):
    with open("data/logs.txt", "a", encoding="utf-8") as f:
        time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{time}] {message}\n")
