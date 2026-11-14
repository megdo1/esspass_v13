from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem
from PyQt5.QtCore import Qt
import pandas as pd
from app.logic.logic_visite import calcul_indicateurs_visite
import sys,os
from app.data.data_manager import DataManager
from app.mainwindow.navigation_mixin import NavigationMixin
from app.mainwindow.traitement_mixin import TraitementMixin
from app.mainwindow.table_mixin import TableMixin
from app.mainwindow.export_mixin import ExportMixin

def resource_path(relative_path: str) -> str:
    """
    Chemin vers ressources ES-PIGC.
    - Dev : depuis la racine du projet.
    - Nuitka onefile : depuis le dossier de python.exe temporaire.
    """
    # Cas Nuitka / binaire
    if os.path.basename(sys.executable).lower().startswith("python") and "ONEFIL" in sys.executable.upper():
        exe_dir = os.path.dirname(sys.executable)
        candidate = os.path.join(exe_dir, relative_path)
        if os.path.exists(candidate):
            return candidate

    # Cas développement (tu lances main.py depuis la racine du projet)
    project_root = os.path.dirname(os.path.abspath(__file__))  # app/
    project_root = os.path.dirname(project_root)               # racine (ES-PIGC_GUI - DEMO_ad)
    return os.path.join(project_root, relative_path)


LINES_PER_PAGE = 1000  # Tu peux ajuster à 100, 200, 1000, etc. selon les besoins

class MainWindow(NavigationMixin, TraitementMixin, TableMixin, ExportMixin, QMainWindow):
    REQUIRED_COLS_PRECONISATIONS = [
        "Infrapôle", "Urgence", "Statut", "Statut échéance", "Echéance", "Enjeu sécurité"
    ]
    REQUIRED_COLS_VISITES = [
        "Infrapôle", "Catégorie", "Etat d'avancement", "Statut"
    ]

    def __init__(self):
        super().__init__()
        self.dm = DataManager()
        self.is_admin = self.dm.is_current_user_admin()
        self.setWindowTitle("ES-PIGC")
        self.setGeometry(100, 100, 1400, 900)

        self.menu_structure = {
            "ES-IND": {
                "OA": ["S.A.R", "Indicateurs trimestriels", "Autres"],
                "OT": ["Visites cycliques", "Préconisations", "Autres"]
            },
            "ES-TDB": {
                "DGII": ["Section Structures", "Section Compatibilité", "Section EMF"],
                "ZP": []
            },
            "ES-RAP": {
                "RGI": ["RSI 1", "RSI 2", "RSI 3"]
            },
            "PASS": {
                "LD Assistance PIGC": ["📋 Demandes", "👥 Utilisateurs", "⚙️ Configuration"]
            }
        }

        

        self.menu2_options = {
            ("ES-IND", "OA"): ["S.A.R", "Indicateurs trimestriels", "Autres"],
            ("ES-IND", "OT"): ["Visites cycliques", "Préconisations", "Autres"],
            ("ES-TDB", "DGII"): ["Section Structures", "Section Compatibilité", "Section EMF"],
            ("ES-TDB", "Autres"): ["Autres 1", "Autres 2"],
            ("ES-RAP", "RGI"): ["RSI 1", "RSI 2", "RSI 3"],
            ("PASS", "LD Assistance PIGC"): ["📋 Demandes", "👥 Utilisateurs", "⚙️ Configuration"]
        }
        self.menu_history = {}
        self.file_data_by_view = {}
        self.indicators_by_view = {}
        self.current_key = None
        self.current_M1_title = None
        self.current_M1_sub = None
        self.zone3_widgets = {}
        self.initUI()


    def initUI(self):
        app = QApplication.instance()
        css_path = resource_path("app/styles/style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        # url() des icônes du thème résolus en absolu : indépendant du dossier courant
        icons_dir = resource_path("app/styles/icons").replace("\\", "/")
        app.setStyleSheet(css.replace("url(app/styles/icons/", f"url({icons_dir}/"))
        
        main_layout = QHBoxLayout()
        # ✅ NOUVEAU : Créer le menu latéral (zone1)
        self.zone1 = self.create_zone1_drilldown()
        self.zone1.setStyleSheet(".QFrame { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; border-radius: 0px; }")

        # ✅ NOUVEAU : Zone centrale avec bouton toggle
        center_container = QWidget()
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)


        # Zone de contenu (zone3)
        self.zone3 = self.create_zone3()

        center_layout.addWidget(self.zone3)
        center_container.setLayout(center_layout)

        # Assembler le layout principal
        main_layout.addWidget(self.zone1)
        main_layout.addWidget(center_container, 1)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)


    def refresh_table_page(self, widget, table, editable_col=None):
        df = widget.df_filtered
        total_rows = len(df)
        per_page = LINES_PER_PAGE
        page = widget.page_index
        start = page * per_page
        end = min(start + per_page, total_rows)
        df_page = df.iloc[start:end]

        self.ensure_filters_exist(widget, df, editable_col)
        """
        # Suppression des anciens filtres
        while widget.filters_layout.count():
            item = widget.filters_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        
        widget.filters_editors = []

        # Création des filtres pour chaque colonne
        for col in df.columns:
            edit = QLineEdit()
            edit.setPlaceholderText(str(col))
            edit.setFixedWidth(140)
            edit.textChanged.connect(lambda val, colname=col: self.apply_filters(widget, editable_col))
            widget.filters_layout.addWidget(edit)
            widget.filters_editors.append(edit)
        """
        # Réinitialise la table
        table.clear()
        table.setRowCount(0)
        table.setColumnCount(0)
        table.setRowCount(len(df_page))
        table.setColumnCount(len(df_page.columns))
        table.setHorizontalHeaderLabels(df_page.columns)

        # Remplissage du tableau (page courante uniquement)
        for i in range(len(df_page)):
            for j in range(len(df_page.columns)):
                val = str(df_page.iat[i, j]) if pd.notna(df_page.iat[i, j]) else ""
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(i, j, item)

        self.update_table_display(df_page, table, editable_col)
        table.setVisible(True)

        # Pagination : infos et boutons (à mettre à jour ici)
        n_pages = (total_rows + per_page - 1) // per_page
        widget.label_page.setText(f"Page {page + 1} / {n_pages if n_pages else 1}")
        widget.btn_prev.setEnabled(page > 0)
        widget.btn_next.setEnabled(end < total_rows)


    def go_to_page(self, widget, delta, editable_col=None):
        n_rows = len(widget.df_filtered) if widget.df_filtered is not None else 0
        per_page = LINES_PER_PAGE
        n_pages = (n_rows + per_page - 1) // per_page
        new_page = max(0, min(widget.page_index + delta, n_pages - 1))
        if new_page != widget.page_index:
            widget.page_index = new_page
            self.refresh_table_page(widget, widget.table, editable_col)


    def restore_state(self):
        key = self.current_key
        if key and key in self.menu_history:
            state = self.menu_history[key]
            widget = self.zone3_widgets[key]
            if state["mode"] == "file":
                widget.radio_file.setChecked(True)
                self.file_data_by_view[key] = state["df"]
                state["df"] = state["df"].astype(str).fillna("")
                state["df"] = state["df"].reset_index(drop=True)
                self.display_table_for_view(state["df"], widget.table, widget)
