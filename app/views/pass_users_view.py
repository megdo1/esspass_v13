"""
Module de gestion des utilisateurs et rôles pour l'application PASS

Fichier: app/views/pass_parametrage_view.py
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QTabWidget

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
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(14)

        # --- en-tête : titre, sous-titre
        titre = QLabel("Gestion des utilisateurs")
        titre.setStyleSheet("font-size: 22px; font-weight: 700; color: #0F2A52;")
        sous_titre = QLabel("Comptes, rôles, accès et responsables ES-PASS")
        sous_titre.setStyleSheet("font-size: 13px; color: #64748B;")
        main_layout.addWidget(titre)
        main_layout.addWidget(sous_titre)

        # --- tuiles de synthèse (mêmes que l'écran Demandes)
        self.create_zone_synthese(main_layout)

        # --- onglets (même habillage que l'écran de configuration)
        tabs = QTabWidget()
        tabs.setStyleSheet(style.TABS_STYLE)
        tabs.addTab(self.create_tab_utilisateurs(), "📋 Liste des utilisateurs")
        tabs.addTab(self.create_tab_creer_utilisateur(), "➕ Créer un utilisateur")
        tabs.addTab(self.create_tab_matrice_droits(), "🔐 Matrice des droits")
        main_layout.addWidget(tabs, 1)

        pied = QHBoxLayout()
        pied.addStretch()
        btn_close = QPushButton("Fermer")
        btn_close.clicked.connect(self.accept)
        pied.addWidget(btn_close)
        main_layout.addLayout(pied)
