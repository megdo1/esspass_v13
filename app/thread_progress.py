from PyQt5.QtCore import QThread, pyqtSignal


class ProgressThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal()

    def __init__(self, total_steps=10, sleep_time=60):
        super().__init__()
        self.total_steps = total_steps
        self.sleep_time = sleep_time

    def run(self):
        for i in range(self.total_steps):
            percent = int((i + 1) * 100 / self.total_steps)
            self.progress.emit(percent)
            self.msleep(self.sleep_time)
        self.finished.emit()

