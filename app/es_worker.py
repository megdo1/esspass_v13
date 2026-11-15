from PyQt5.QtCore import QObject, pyqtSignal
import logging

logger = logging.getLogger(__name__)



class SectionStrCalcWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)

    def __init__(self, df, func):
        super().__init__()
        self.df = df
        self.func = func

    def run(self):
        try:
            if self.func == 'calcul_tdb_section_structure':
                from app.logic_tdb import calcul_tdb_section_structure
            if self.func == 'calcul_tdb_section_structure_activite':
                from app.logic_tdb import calcul_tdb_section_structure_activite

            # result = calcul_tdb_section_structure(self.df, progress_callback=self.progress.emit)
            result = self.func(self.df, progress_callback=self.progress.emit)
        except Exception as e:
            logger.exception("Worker exception : %s", e)
            result = None
        self.finished.emit(result)

