from PyQt5.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)



class SarCalcWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)

    def __init__(self, df, annee, trimestre):
        super().__init__()
        self.df = df
        self.annee = annee
        self.trimestre = trimestre

    def run(self):
        from app.logic.logic_sar import calcul_sar_indicateurs
        try:
            result = calcul_sar_indicateurs(self.df, self.annee, self.trimestre, progress_callback=self.progress.emit)
        except Exception as e:
            logger.exception("SAR Worker exception : %s", e)
            result = None
        self.finished.emit(result)


