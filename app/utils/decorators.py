from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from functools import wraps


def busy_cursor(func):
    """Décorateur pour afficher le sablier - GARDE tous les arguments"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # ✅ Retire TOUS les curseurs empilés
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()
            QApplication.processEvents()

    return wrapper


def busy_cursor_no_args(func):
    """Décorateur pour les slots Qt - IGNORE les arguments des signaux"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()

        try:
            result = func(self)
            return result
        finally:
            # ✅ Retire TOUS les curseurs empilés
            while QApplication.overrideCursor():
                QApplication.restoreOverrideCursor()
            QApplication.processEvents()

    return wrapper
