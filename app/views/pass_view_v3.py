"""Vue PASS (demandes). Les dialogues et widgets vivent dans app.views.pass_v3.*
et sont ré-exportés ici pour compatibilité avec les anciens imports."""

import matplotlib

matplotlib.use("Agg")  # backend sans fenêtre : avant tout import pyplot

from PyQt5.QtWidgets import QWidget
from app.data.data_manager import DataManager
from app.data.data_manager import get_windows_user_info
from app.data.data_config import loadConfig
from app.utils.ui_helpers import show_warning, show_error
from app.views.pass_v3.widgets import (  # noqa: F401  (ré-export : compatibilité)
    NoScrollComboBox,
    PopupFiltre,
)
from app.views.pass_v3.demande_dialogs import (  # noqa: F401  (ré-export : compatibilité)
    EditDemandeDialog,
    CreateDemandeDialog,
    DuplicateDemandeDialog,
)
from app.views.pass_v3.mail_dialog import (  # noqa: F401  (ré-export : compatibilité)
    MailDetailsDialog,
)
from app.views.pass_v3.traitement_dialogs import (  # noqa: F401  (ré-export : compatibilité)
    TraiterDemandeDialog,
    TraiterMasseDialog,
    GererMasseDialog,
)
from app.views.pass_v3.rapports import (  # noqa: F401  (ré-export : compatibilité)
    RapportCOPILViewerDialog,
    RapportViewerDialog,
    RapportsDialog,
)
from app.views.pass_v3.permissions_mixin import PermissionsMixin
from app.views.pass_v3.layout_mixin import LayoutMixin
from app.views.pass_v3.filtres_mixin import FiltresMixin
from app.views.pass_v3.table_mixin import TableMixin
from app.views.pass_v3.actions_mixin import ActionsMixin
from app.views.pass_v3.export_mixin import ExportMixin
from app.views.pass_v3.edition_cellule_mixin import EditionCelluleMixin


class PassViewClean(PermissionsMixin, LayoutMixin, FiltresMixin, TableMixin, ActionsMixin, ExportMixin,
                    EditionCelluleMixin, QWidget):
    """Vue PASS - UTILISE UNIQUEMENT DataManager"""

    def __init__(self, parent=None, data_manager=None):
        super().__init__(parent)
        self.setWindowTitle("ES-PASS - Gestion des demandes d'assistance PIGC")
        self.setMinimumSize(1400, 900)
        self.open_dialogs = {}  # {id_demande: dialog_instance}

        try:
            # Instance partagée de la fenêtre principale si fournie : évite un 2e chargement des listes
            self.data_manager = data_manager or DataManager()  # Lèvera une exception si DB inaccessible
        except Exception as e:
            show_error(
                self,
                "Erreur d'accès à la base de données",
                str(e)  # Le message est déjà explicite depuis DataManager
            )
            return

        self.user_info = self.data_manager.get_current_user()
        if not self.user_info:
            userwindows = get_windows_user_info()

            if userwindows.get("error"):
                show_error(
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
                show_warning(
                    self,
                    "Accès refusé",
                    f"Utilisateur {userwindows['firstname']} {userwindows['lastname']}\n\n"
                    "Votre compte n'existe pas encore.\n\n"
                    "Contactez votre administrateur système."
                )
            elif not user.get("actif"):
                show_warning(
                    self,
                    "Compte inactif",
                    f"Utilisateur {user['nom']} {user['prenom']}\n\n"
                    "Votre compte est inactif.\n"
                    "Contactez votre administrateur système."
                )
            return

        self.collecte_info = self.data_manager.get_last_collecte()
        self.dashboard_stats = self.data_manager.get_dashboard_stats()

        self.init_ui()
        self.update_button_permissions()
        self.setup_corner_label()

        # Timer auto-refresh

        # Charger les données initiales
        self.update_display_info()
        # Pas de 2e load_demandes_table() ici : init_ui() a déjà chargé le tableau


        # Si is_enabled = True, ne rien faire (garder le style exact du bouton)


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    from app.data.data_config import loadConfig

    app = QApplication(sys.argv)
    window = PassViewClean(loadConfig())
    window.show()
    sys.exit(app.exec_())
