from PyQt5.QtCore import QObject, pyqtSignal


class IndOACalcWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)

    def __init__(self, df, annee, trimestre):
        super().__init__()
        self.df = df
        self.annee = annee
        self.trimestre = trimestre

    def run(self):
        from app.logic.logic_indicateurs_oa import calcul_indicateurs_trimestriels
        try:
            # print("IndOACalcWorker - lancement du calcul", flush=True)
            result = calcul_indicateurs_trimestriels(self.df, self.annee, self.trimestre, progress_callback=self.progress.emit)

        except Exception as e:
            import traceback
            print("KPI OA - Worker exception:", e)
            print(traceback.format_exc())
            result = None
        self.finished.emit(result)


