"""
utils/log.py
Hệ thống ghi Log đơn giản
"""
import logging
import os
from datetime import datetime

# Tạo thư mục logs nếu chưa có
if not os.path.exists("logs"):
    os.makedirs("logs")

# Tên file log theo ngày
log_filename = f"logs/app_{datetime.now().strftime('%Y-%m-%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'), # Ghi vào file
        logging.StreamHandler() # Hiện lên terminal
    ]
)

logger = logging.getLogger("DriverApp")

def log_info(msg):
    logger.info(msg)

def log_warning(msg):
    logger.warning(msg)

def log_error(msg):
    logger.error(msg)