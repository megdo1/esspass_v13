from PyQt5.QtCore import QObject, pyqtSignal

import logging
logger = logging.getLogger(__name__)



class VerifyWorker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)

    def __init__(self, df):
        super().__init__()
        self.df = df

    def run(self):
        try:
            self.progress.emit(10)

            # Étape 1 : nettoyage du DataFrame
            df_clean = self.df.astype(str).fillna("").reset_index(drop=True)
            self.progress.emit(80)

            # Fin du traitement threadé : on retourne le DataFrame nettoyé
            self.finished.emit(df_clean)
        except Exception as e:
            logger.error(f"ERREUR dans VerifyWorker : {e}")
            self.finished.emit(None)

