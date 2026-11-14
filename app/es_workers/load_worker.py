from PyQt5.QtCore import QObject, pyqtSignal


class LoadWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object, object)

    def __init__(self, file_name, func):
        super().__init__()
        self.file_name = file_name
        self.func = func

    def run(self):
        try:
            if self.func == 'extract_data_pigc_file_granular':
                from app.utils_excel import extract_data_pigc_file_granular

            def callback(percent):
                self.progress.emit(percent)

            # result = self.func(self.file_name, progress_callback=self.progress.emit)
            df_data, idx_en_tete = self.func(self.file_name, progress_callback=callback)
            self.progress.emit(100)
            self.finished.emit(df_data, idx_en_tete)
        except Exception as e:
            import traceback
            print(f"Worker {self.func} exception:", e, flush=True)
            print(traceback.format_exc(), flush=True)
            self.finished.emit(None, None)










