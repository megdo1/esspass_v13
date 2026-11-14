import os
import sys


def get_base_path():
    # Mode PyInstaller
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESSOURCES_DIR = os.path.join(PROJECT_ROOT, "ressources")

MODEL_VISITES_PATH = os.path.join(PROJECT_ROOT, "ressources", "modeles", "Model_Export_ES-IND_OT_Visites-Cycliques_v1.xlsx")
MODEL_PRECO_PATH = os.path.join(PROJECT_ROOT, "ressources", "modeles", "Model_Export_ES-IND_OT_Préconisations_v1.xlsx")
MODEL_SAR_PATH = os.path.join(PROJECT_ROOT, "ressources", "modeles", "Model_Export_ES-IND_OA_Revue SAR_v1.xlsx")
MODEL_INDICATEURS_OA_PATH = os.path.join(PROJECT_ROOT, "ressources", "modeles", "model_indicateurs_OA_Infrapôle_v1.1.xlsx")

LOGO_PATH = os.path.join(PROJECT_ROOT, "ressources", "icones", "logo.png")
APP_NAME = "ES-PIGC"
from app.version import APP_VERSION  # noqa: E402,F401  (source unique : app/version.py)
#MODEL_VISITES_PATH = "../ressources/modeles/Model_Export_ES-IND_OT_Visites-Cycliques_v1.xlsx"
#MODEL_PRECO_PATH = "../ressources/modeles/Model_Export_ES-IND_OT_Préconisations_v1.xlsx"
#LOGO_PATH = "../ressources/icones/logo.png"
