"""
Module de gestion des utilisateurs et rôles pour l'application PASS

Fichier: app/views/pass_parametrage_view.py
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QTabWidget

from PyQt5.QtCore import Qt
from app.data.data_manager import DataManager
from app.data.data_manager import get_windows_user_info
from app.styles import style
from app.views.users.tabs_mixin import TabsMixin
from app.views.users.actions_mixin import ActionsMixin


# ========== CLASSE PRINCIPALE ==========

class GestionUtilisateursDialog(TabsMixin, ActionsMixin, QDialog):
    """Dialogue pour gérer les utilisateurs et leurs rôles"""

    def __init__(self, parent=None):
        super().__init__(parent)

        try:
            self.data_manager = DataManager()  # Lèvera une exception si DB inaccessible
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur d'accès à la base de données",
                str(e)  # Le message est déjà explicite depuis DataManager
            )
            self.reject()
            return

        self.setWindowTitle("👥 Gestion des Utilisateurs et Rôles")
        self.setMinimumSize(1000, 700)

        # Vérification des droits admin
        if not self.check_admin_access():
            self.reject()
            return

        self.init_ui()
        self.load_utilisateurs()

            
    def check_admin_access(self) -> bool:
        """Vérifie si l'utilisateur a les droits administrateur"""
        if not self.data_manager.is_current_user_admin():
            userwindows = get_windows_user_info()
            
            if userwindows.get("error"):
                QMessageBox.critical(
                    self,
                    "Outlook non disponible",
                    "Microsoft Outlook n'est pas lancé ou n'est pas correctement configuré.\n"
                    "Veuillez lancer Outlook avant d'ouvrir cette application."
                )
                return False
            
            user = self.data_manager.get_user_by_credentials(
                userwindows["lastname"],
                userwindows["email"]
            )
            
            if not user:
                QMessageBox.warning(
                    self,
                    "Accès refusé",
                    f"Utilisateur {userwindows['fullname']}\n\n"
                    "Vous n'avez pas les droits d'administrateur.\n"
                    "Votre compte n'existe pas encore.\n\n"
                    "Contactez votre administrateur système."
                )
            elif not user.get("actif"):
                QMessageBox.warning(
                    self,
                    "Compte inactif",
                    f"Utilisateur {user['nom']} {user['prenom']}\n\n"
                    "Votre compte est inactif.\n"
                    "Contactez votre administrateur système."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Droits insuffisants",
                    f"Utilisateur {user['nom']} {user['prenom']}\n"
                    f"Rôle actuel : {user['role']}\n\n"
                    "Vous n'avez pas les droits d'administrateur.\n"
                    "Seuls les administrateurs peuvent accéder à cette section."
                )
            
            return False
        
        return True

    def init_ui(self):
        """Initialise l'interface utilisateur"""
        main_layout = QVBoxLayout(self)

        title_label = QLabel("👥 GESTION DES UTILISATEURS ET RÔLES")
        title_label.setStyleSheet(style.TITLE_STYLE)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        tabs = QTabWidget()

        tab_utilisateurs = self.create_tab_utilisateurs()
        tabs.addTab(tab_utilisateurs, "📋 Liste des utilisateurs")

        tab_creer = self.create_tab_creer_utilisateur()
        tabs.addTab(tab_creer, "➕ Créer un utilisateur")

        tab_matrice = self.create_tab_matrice_droits()
        tabs.addTab(tab_matrice, "🔐 Matrice des droits")

        main_layout.addWidget(tabs)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        btn_close = QPushButton("❌ Fermer")
        btn_close.setStyleSheet(style.BUTTON_CLOSE_STYLE)
        btn_close.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_close)

        main_layout.addLayout(buttons_layout)


