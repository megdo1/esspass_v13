"""
Helpers pour l'interface utilisateur
Gère automatiquement les curseurs sablier avant les QMessageBox
"""

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt


def clear_all_cursors():
    """Retire TOUS les curseurs sablier empilés"""
    while QApplication.overrideCursor():
        QApplication.restoreOverrideCursor()
    QApplication.processEvents()


def ask_question(parent, title, message, buttons=QMessageBox.Yes | QMessageBox.No, default_button=QMessageBox.No):
    """
    Affiche une question en restaurant automatiquement le curseur

    Args:
        parent: Widget parent
        title: Titre de la boîte de dialogue
        message: Message à afficher
        buttons: Boutons à afficher (par défaut Yes|No)
        default_button: Bouton par défaut

    Returns:
        La réponse (QMessageBox.Yes, QMessageBox.No, etc.)
    """
    clear_all_cursors()
    return QMessageBox.question(parent, title, message, buttons, default_button)


def show_info(parent, title, message):
    """Affiche un message d'information"""
    clear_all_cursors()
    return QMessageBox.information(parent, title, message)


def show_warning(parent, title, message):
    """Affiche un avertissement"""
    clear_all_cursors()
    return QMessageBox.warning(parent, title, message)


def show_error(parent, title, message):
    """Affiche un message d'erreur"""
    clear_all_cursors()
    return QMessageBox.critical(parent, title, message)


def show_custom(parent, icon, title, message, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
    """
    Affiche une boîte de dialogue personnalisée

    Args:
        icon: QMessageBox.Information, Warning, Critical, Question, NoIcon
        title: Titre
        message: Message
        buttons: Boutons (ex: QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        default_button: Bouton par défaut

    Returns:
        Le bouton cliqué
    """
    clear_all_cursors()
    msgbox = QMessageBox(parent)
    msgbox.setIcon(icon)
    msgbox.setWindowTitle(title)
    msgbox.setText(message)
    msgbox.setStandardButtons(buttons)
    msgbox.setDefaultButton(default_button)
    return msgbox.exec_()
