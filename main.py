import ctypes
import logging
import os
import sys
import traceback

from app.version import APP_NAME, APP_VERSION

# matplotlib : dossier de cache PERSISTANT. Sans cela (PyInstaller), il utilise un dossier temporaire
# jetable qui peut être nettoyé en cours de session et fait échouer les exports de rapports.
# À faire AVANT tout import de matplotlib (importé indirectement par l'application).
_MPL_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "ES-PIGC", "matplotlib")
try:
    os.makedirs(_MPL_DIR, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = _MPL_DIR
except OSError:
    pass

# CRITIQUE : définir l'AppUserModelID pour que Windows distingue l'application de Python.
# Format : company.product.subproduct.version (ne pas modifier : épinglage barre des tâches)
APP_USER_MODEL_ID = 'sncf.espigc.application.2.0'
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from app.ui_infodialog import InfoDialog
from app.ui_mainwindow_v3 import MainWindow
from app.utils.logging_setup import setup_logging
from app.utils.paths import bundle_dir


def exception_hook(exctype, value, tb):
    """Capture toutes les exceptions non gérées et les affiche dans une MessageBox."""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))

    # Journal fichier (dossier ES-PIGC de APPDATA) : seule trace exploitable en exe sans console
    logging.getLogger("espass.main").critical("Erreur non gérée : %s", error_msg)

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle("❌ Erreur Critique")
    msg.setText(f"Une erreur critique s'est produite :\n\n{exctype.__name__}: {value}")
    msg.setDetailedText(error_msg)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()

    sys.__excepthook__(exctype, value, tb)


def set_console_title(title):
    """Définit le titre de la fenêtre console Windows."""
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass


def print_banner():
    """Affiche une bannière ASCII dans la console."""
    version_line = f"{APP_NAME} - Version {APP_VERSION}".center(73)
    banner = rf"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║        ███████╗███████╗      ██████╗  █████╗ ███████╗███████╗             ║
║        ██╔════╝██╔════╝      ██╔══██╗██╔══██╗██╔════╝██╔════╝             ║
║        █████╗  ███████╗█████╗██████╔╝███████║███████╗███████╗             ║
║        ██╔══╝  ╚════██║╚════╝██╔═══╝ ██╔══██║╚════██║╚════██║             ║
║        ███████╗███████║      ██║     ██║  ██║███████║███████║             ║
║        ╚══════╝╚══════╝      ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝             ║
║                                                                           ║
║ {version_line} ║
║                                                                           ║
║            Application de suivi des demandes d’assistance PIGC            ║
║                             et données OA/OTH                             ║
║                                                                           ║
║                           © 2025 - SNCF Réseau                            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def get_logo_path():
    # Compatible PyInstaller (avec ou sans build)
    return os.path.join(bundle_dir(), "ressources", "icones", "favicon.ico")


def _make_console_safe():
    """Évite qu'un print() avec emoji plante sur une console non UTF-8 (cp1252...)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # pas de console (exe --noconsole) ou flux non reconfigurable


def main():
    _make_console_safe()
    sys.excepthook = exception_hook          # AVANT la création de l'application
    setup_logging()
    set_console_title(f"ES-PIGC v{APP_VERSION} - Ecosystème PIGC")
    print_banner()
    print("🚀 Démarrage de l'application...\n")

    os.makedirs(os.path.join(bundle_dir(), "sauvegardes"), exist_ok=True)

    app = QApplication(sys.argv)
    logo_path = get_logo_path()
    app.setWindowIcon(QIcon(logo_path))       # icône barre des tâches

    info = InfoDialog()
    info.setWindowIcon(QIcon(logo_path))
    info.exec_()

    window = MainWindow()
    window.setWindowIcon(QIcon(logo_path))
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
