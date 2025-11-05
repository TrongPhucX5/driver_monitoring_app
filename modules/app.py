"""
Ứng dụng GUI bằng Python hiển thị luồng video (webcam/RTSP) với các nút điều khiển:
- Bắt đầu giám sát
- Dừng lại
- Cài đặt (chọn camera index hoặc URL)
- Nhãn trạng thái

Yêu cầu: PyQt5, opencv-python, numpy
Chạy: pip install pyqt5 opencv-python numpy
       python video_monitor.py

Tệp: video_monitor.py
"""

import sys
import threading
import cv2
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets


class VideoCaptureThread(QtCore.QThread):
    frame_received = QtCore.pyqtSignal(np.ndarray)
    status_changed = QtCore.pyqtSignal(str)

    def __init__(self, source=0, width=640, height=480, parent=None):
        super().__init__(parent)
        self.source = source
        self.width = width
        self.height = height
        self._running = False
        self.cap = None

    def run(self):
        try:
            self.status_changed.emit('Connecting...')
            self.sleep(1)  # Chờ 5 giây trước khi mở camera
            # Khởi tạo VideoCapture
            self.cap = cv2.VideoCapture(self.source)
            if isinstance(self.source, str) and self.source.isdigit():
                self.cap = cv2.VideoCapture(int(self.source))

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            if not self.cap.isOpened():
                self.status_changed.emit('Error: Không mở được nguồn video')
                return

            self._running = True
            self.status_changed.emit('Streaming')

            while self._running:
                ret, frame = self.cap.read()
                if not ret:
                    self.status_changed.emit('Error: Không lấy được khung hình')
                    break

                self.frame_received.emit(frame)
                self.msleep(10)

        except Exception as e:
            self.status_changed.emit('Error: ' + str(e))
        finally:
            if self.cap is not None:
                try:
                    self.cap.release()
                except:
                    pass
            if self._running:
                self.status_changed.emit('Stopped')

    def stop(self):
        self._running = False
        self.wait(1000)


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, current_source='0', width=640, height=480):
        super().__init__(parent)
        self.setWindowTitle('Cài đặt nguồn video')
        self.setModal(True)

        layout = QtWidgets.QFormLayout(self)

        self.source_edit = QtWidgets.QLineEdit(str(current_source), self)
        self.source_edit.setToolTip('Nhập số camera (0,1,...) hoặc URL RTSP/HTTP')
        self.width_edit = QtWidgets.QLineEdit(str(width), self)
        self.height_edit = QtWidgets.QLineEdit(str(height), self)

        layout.addRow('Nguồn (index hoặc URL):', self.source_edit)
        layout.addRow('Chiều rộng (px):', self.width_edit)
        layout.addRow('Chiều cao (px):', self.height_edit)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            parent=self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def values(self):
        return self.source_edit.text().strip(), int(self.width_edit.text()), int(self.height_edit.text())


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Video Monitor')
        self.setMinimumSize(800, 600)

        self.source = '0'
        self.frame_width = 640
        self.frame_height = 480

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vbox = QtWidgets.QVBoxLayout(central)

        self.video_label = QtWidgets.QLabel('No video')
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet('background-color: #222; color: #fff;')
        vbox.addWidget(self.video_label)

        hbox = QtWidgets.QHBoxLayout()

        self.start_btn = QtWidgets.QPushButton('Bắt đầu giám sát')
        self.stop_btn = QtWidgets.QPushButton('Dừng lại')
        self.settings_btn = QtWidgets.QPushButton('Cài đặt')

        self.stop_btn.setEnabled(False)

        hbox.addWidget(self.start_btn)
        hbox.addWidget(self.stop_btn)
        hbox.addWidget(self.settings_btn)

        self.status_label = QtWidgets.QLabel('Trạng thái: Idle')
        self.status_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        hbox.addWidget(self.status_label)

        hbox.addStretch()

        vbox.addLayout(hbox)

        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.settings_btn.clicked.connect(self.open_settings)

        self.capture_thread = None

    def set_status(self, text):
        self.status_label.setText('Trạng thái: ' + text)

    def start_monitoring(self):
        if self.capture_thread and self.capture_thread.isRunning():
            self.set_status('Đang chạy')
            return

        self.capture_thread = VideoCaptureThread(source=self.source, width=self.frame_width, height=self.frame_height)
        self.capture_thread.frame_received.connect(self.update_frame)
        self.capture_thread.status_changed.connect(self.set_status)
        self.capture_thread.finished.connect(self.on_capture_finished)
        self.capture_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.settings_btn.setEnabled(False)
        self.set_status('Kết nối...')

    def stop_monitoring(self):
        if self.capture_thread:
            self.capture_thread.stop()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.settings_btn.setEnabled(True)
        self.set_status('Dừng')

    def on_capture_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.settings_btn.setEnabled(True)
        self.set_status('Stopped')

    @QtCore.pyqtSlot(np.ndarray)
    def update_frame(self, frame):
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            pix = QtGui.QPixmap.fromImage(qimg).scaled(self.video_label.width(), self.video_label.height(), QtCore.Qt.KeepAspectRatio)
            self.video_label.setPixmap(pix)
        except Exception as e:
            self.set_status('Error khi cập nhật khung: ' + str(e))

    def open_settings(self):
        dlg = SettingsDialog(self, current_source=self.source, width=self.frame_width, height=self.frame_height)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            try:
                src, w, h = dlg.values()
                self.source = src
                self.frame_width = w
                self.frame_height = h
                self.set_status(f'Cập nhật cài đặt: {src} ({w}x{h})')
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, 'Lỗi', 'Giá trị cài đặt không hợp lệ: ' + str(e))

    def closeEvent(self, event):
        if self.capture_thread and self.capture_thread.isRunning():
            self.capture_thread.stop()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
