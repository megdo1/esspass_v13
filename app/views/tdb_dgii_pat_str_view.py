from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QLabel, QMessageBox, QComboBox, QFileDialog, QRadioButton, QButtonGroup, QLineEdit,
    QScrollArea, QFrame, QHeaderView, QSizePolicy, QCheckBox
)
from PyQt5.QtCore import Qt, QThread
import datetime
import pandas as pd

from app.utils_excel import extract_data_after_second_empty_row, check_required_columns
from app.logic_tdb import calcul_tdb_section_structure, calcul_tdb_section_structure_activite
from app.export.export_visite import export_visites_cycliques
from app.ressources import MODEL_VISITES_PATH
from app.es_worker import SectionStrCalcWorker
from app.dialogs.tdb_pat_str_graphdialog import PatStrGraphDialog
from app.dialogs.tdb_pat_str_graph_activite_dialog import PatStrActiviteGraphDialog

import logging
logger = logging.getLogger(__name__)



class TdbSectionPatStrView(QWidget):
    REQUIRED_COLS = [
        "Infrapôle", "Catégorie", "Etat d'avancement", "Statut"
    ]

    def __init__(self, parent=None):
        logger.debug("DEBUG: TdbSectionPatStrView - 0")
        super().__init__(parent)
        self.df_source = None
        self.df_indicateurs = None
        self.df_affichee = None
        self.init_ui()
        self.connect_signals()
        self.LINES_PER_PAGE = 1000  # Tu peux ajuster à 100, 200, 1000, etc. selon les besoins
        self.show_mode("file")

    def init_ui(self):
        layout = QVBoxLayout()

        # Ligne 1: choix de la source des données
        source_layout = QHBoxLayout()
        source_layout.addStretch()
        source_label = QLabel("Source des données")
        self.radio_flux = QRadioButton("PIGC (flux)")
        self.radio_file = QRadioButton("Fichier (chargement)")
        self.radio_file.setChecked(True)
        self.source_group = QButtonGroup(self)
        self.source_group.addButton(self.radio_flux)
        self.source_group.addButton(self.radio_file)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.radio_flux)
        source_layout.addWidget(self.radio_file)
        source_layout.addStretch()
        layout.addLayout(source_layout)

        # Ligne 2: Boutons chargement, vérification, année, trimestre et calcul
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        # btn_layout.setAlignment(Qt.AlignTop)

        self.btn_load = QPushButton("Charger un fichier")
        self.btn_verify = QPushButton("Vérifier le contenu")

        self.combo_annee = QComboBox()
        # annee_courante = datetime.datetime.now().year
        self.combo_annee.setToolTip("Année (extraites de la colonne Date du fichier chargé)")
        self.combo_annee.addItem("Année")  # Placeholder initial
        self.combo_annee.setFixedWidth(90)

        trimestre_labels = ["Aujourd'hui"] + [f"T{i}" for i in range(1, 6)]
        self.trimestre_group = QButtonGroup(self)
        self.trimestre_radios = []
        for label in trimestre_labels:
            btn = QRadioButton(label)
            self.trimestre_group.addButton(btn)
            btn.setChecked(label == "Aujourd'hui")
            self.trimestre_radios.append(btn)

        # positionnement des boutons de la ligne 2
        btn_layout.addWidget(self.btn_load)
        btn_layout.addWidget(self.btn_verify)
        btn_layout.addWidget(self.combo_annee)
        for btn in self.trimestre_radios:
            btn_layout.addWidget(btn)
        self.btn_calculate_activite = QPushButton("Activité")
        self.btn_calculate = QPushButton("Activité par mois")
        btn_layout.addWidget(self.btn_calculate_activite)
        btn_layout.addWidget(self.btn_calculate)
        self.chk_hide_empty_months = QCheckBox("Masquer les mois sans activité")
        self.chk_hide_empty_months.setChecked(False)
        btn_layout.addWidget(self.chk_hide_empty_months)
        btn_frame = QFrame()
        btn_frame.setLayout(btn_layout)
        layout.addWidget(btn_frame, alignment=Qt.AlignHCenter | Qt.AlignTop)

        # Filtres dans un QScrollArea horizontal
        self.filters_frame = QFrame()
        self.filters_layout = QHBoxLayout()
        self.filters_layout.setSpacing(2)
        # self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setContentsMargins(5, 2, 5, 2)
        self.filters_editors = []
        self.filters_frame.setLayout(self.filters_layout)

        self.filters_scroll = QScrollArea()
        self.filters_scroll.setWidgetResizable(True)
        self.filters_scroll.setFixedHeight(50)
        self.filters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.filters_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filters_scroll.setFrameShape(QFrame.NoFrame)
        self.filters_scroll.setWidget(self.filters_frame)
        self.filters_scroll.setVisible(False)
        layout.addWidget(self.filters_scroll)

        # Barre de progression
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Zone message
        self.msg_label = QLabel("Travaux en cours...")
        self.msg_label.setAlignment(Qt.AlignCenter)
        # self.msg_label.setVisible(False) ==> état initiaux
        layout.addWidget(self.msg_label)

        # Table de résultat
        self.table = QTableWidget()
        # self.table.setVisible(False) ==> état initiaux
        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        layout.addWidget(self.table)

        # Pagination
        self.btn_prev = QPushButton("Précédent")
        self.btn_next = QPushButton("Suivant")
        self.label_page = QLabel("Page 1 / 1")
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.label_page)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()
        layout.addLayout(pagination_layout)
        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        # 7. Export/graphique (en bas à droite, si présents)
        bottom_btn_layout = QHBoxLayout()
        # bottom_btn_layout.addStretch()
        bottom_btn_layout.setAlignment(Qt.AlignRight)
        self.btn_export = QPushButton("Exporter le résultat")
        self.btn_export.setVisible(False)
        self.btn_graph_activite = QPushButton("Graphique")
        self.btn_graph_activite.setVisible(False)
        self.btn_graph = QPushButton("Graphique")
        self.btn_graph.setVisible(False)
        bottom_btn_layout.addWidget(self.btn_export)
        bottom_btn_layout.addWidget(self.btn_graph_activite)
        bottom_btn_layout.addWidget(self.btn_graph)
        layout.addLayout(bottom_btn_layout)

        # 8. États initiaux
        self.setLayout(layout)
        self.btn_verify.setEnabled(False)

        self.combo_annee.setVisible(False)
        self.combo_annee.setEnabled(False)

        for btn in self.trimestre_radios:
            btn.setVisible(False)
            btn.setEnabled(False)

        self.btn_calculate_activite.setEnabled(False)
        self.btn_calculate.setEnabled(False)
        self.chk_hide_empty_months.setEnabled(False)
        self.table.setVisible(False)
        self.msg_label.setVisible(False)
        self.btn_export.setEnabled(False)
        self.btn_graph_activite.setEnabled(False)
        self.btn_graph.setEnabled(False)

    def connect_signals(self):
        self.radio_flux.toggled.connect(lambda checked: self.show_mode("flux" if checked else "file"))
        self.radio_file.toggled.connect(lambda checked: self.show_mode("file" if checked else "flux"))

        self.btn_load.clicked.connect(self.load_file)
        self.btn_verify.clicked.connect(self.verify_file)
        self.chk_hide_empty_months.stateChanged.connect(self.afficher_table_masque)
        self.btn_calculate_activite.clicked.connect(self.lancer_activite)
        self.btn_calculate.clicked.connect(self.calculer)
        # Pagination
        self.btn_prev.clicked.connect(lambda: self.go_to_page(-1))
        self.btn_next.clicked.connect(lambda: self.go_to_page(+1))
        # Export et graphique (si présents)
        self.btn_export.clicked.connect(self.exporter_sans_model)
        self.btn_graph_activite.clicked.connect(self.show_graph_activite)
        self.btn_graph.clicked.connect(self.afficher_graphique)

    def show_mode(self, mode):
        is_file = (mode == "file")
        self.btn_load.setVisible(is_file)
        self.btn_verify.setVisible(is_file)
        # self.combo_annee.setVisible(is_file)
        self.combo_annee.setVisible(False)

        for btn in self.trimestre_radios:
            # btn.setVisible(is_file)
            btn.setVisible(False)

        self.btn_calculate_activite.setVisible(is_file)
        self.btn_calculate.setVisible(is_file)
        self.chk_hide_empty_months.setVisible(is_file)
        self.chk_hide_empty_months.setEnabled(is_file and self.btn_calculate.isEnabled())

        self.progress.setVisible(False)
        self.table.setVisible(False)
        self.msg_label.setVisible(False)
        self.filters_scroll.setVisible(False)

        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        self.btn_export.setVisible(is_file and getattr(self, "df_indicateurs", None) is not None)
        self.btn_graph_activite.setVisible(is_file and getattr(self, "df_indicateurs", None) is not None)
        self.btn_graph.setVisible(is_file and getattr(self, "df_indicateurs", None) is not None)

        if not is_file:
            self.msg_label.setText("Le mode 'PIGC (flux)' n'est pas encore implémenté.")
            self.msg_label.setVisible(True)

    def fill_annee(self, df):
        self.combo_annee.clear()

        if "Date de réalisation" in df.columns:
            # Convertir la colonne Date en datetime, puis extraire les années uniques
            try:
                dates = pd.to_datetime(df["Date de réalisation"], errors="coerce", dayfirst=True)
                annees_uniques = sorted(dates.dropna().dt.year.unique(), reverse=True)
                if annees_uniques:
                    self.combo_annee.setEnabled(True)
                    for an in annees_uniques:
                        self.combo_annee.addItem(str(an))
                else:
                    self.combo_annee.setEnabled(False)
                    QMessageBox.warning(self, "Date de réalisation",
                                        "Aucune année détectée dans la colonne <Date de réalisation> du fichier chargé.")
                    self.combo_annee.addItem("Année")
            except Exception as e:
                self.combo_annee.setEnabled(False)
                self.combo_annee.addItem("Année")
                QMessageBox.warning(self, "Date", f"Erreur lors de la lecture des années : {e}")
        else:
            self.combo_annee.setEnabled(False)
            self.combo_annee.addItem("Année")
            QMessageBox.warning(self, "Date",
                                "La colonne <Date de réalisation> est absente du fichier chargé.\nLe champ Année est "
                                "indisponible pour le traitement des reliquats")

    def load_file(self):
        # Chargement du fichier, préparation du DataFrame
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Charger un fichier Excel", "", "Excel Files (*.xlsx *.xls)"
        )
        if not file_name:
            return

        self.progress.setVisible(True)
        self.progress.setValue(33)
        self.msg_label.setVisible(False)
        self.table.setVisible(False)
        self.filters_scroll.setVisible(False)
        self.btn_export.setVisible(False)
        self.btn_graph_activite.setVisible(False)
        self.btn_graph.setVisible(False)

        df, header_idx = extract_data_after_second_empty_row(file_name)

        if df is None:
            QMessageBox.critical(self, "Erreur", "Le fichier chargé ne respecte pas le format attendu.")
            self.progress.setVisible(False)
            return

        # Adapter cette liste aux colonnes indispensables pour ta vue
        missing_cols = check_required_columns(df, self.REQUIRED_COLS)
        if missing_cols:
            QMessageBox.critical(self, "Colonnes absentes", f"Colonnes manquantes : {', '.join(missing_cols)}")
            self.progress.setVisible(False)
            return

        self.df_source = df
        # self.fill_annee(self.df_source)
        self.progress.setVisible(False)
        self.msg_label.setText("Fichier chargé. Cliquez sur 'Vérifier le contenu' ou 'Calculer les indicateurs'.")
        self.msg_label.setVisible(True)
        self.btn_verify.setEnabled(True)
        self.btn_calculate_activite.setEnabled(True)
        self.btn_calculate.setEnabled(True)
        self.chk_hide_empty_months.setEnabled(True)
        for btn in self.trimestre_radios:
            # btn.setEnabled(True)
            btn.setVisible(False)
            btn.setEnabled(False)

        self.table.setVisible(False)
        self.filters_scroll.setVisible(False)
        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)
        self.btn_export.setVisible(False)
        self.btn_graph_activite.setVisible(False)
        self.btn_graph.setVisible(False)

    def verify_file(self):
        # Vérification du contenu, progression, affichage
        if self.df_source is None:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.table.setVisible(False)
        self.filters_scroll.setVisible(False)
        self.btn_export.setVisible(False)
        self.btn_graph_activite.setVisible(False)
        self.btn_graph.setVisible(False)
        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        # Ici, tu pourrais ajouter une animation, un thread de progression, etc.
        # Pour une version instantanée :
        df = self.df_source.astype(str).fillna("").reset_index(drop=True)
        self.afficher_table(df)
        self.msg_label.setText("Vérification visuelle : données source.")
        self.msg_label.setVisible(True)
        self.progress.setVisible(False)
        self.table.setVisible(True)
        self.filters_scroll.setVisible(True)
        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

    def afficher_table(self, df, editable_col=None):
        # Affichage du tableau, appel ensure_filters_exist, refresh_table_page
        # Stocke le DataFrame à filtrer
        self.df_current = df
        self.df_filtered = df
        self.page_index = 0

        # S'assure que les filtres existent (créés une seule fois par structure)
        self.ensure_filters_exist(df)

        # Affiche la page courante
        self.refresh_table_page(editable_col)

        # Affiche les widgets
        self.table.setVisible(True)
        self.filters_scroll.setVisible(True)
        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

    def afficher_table_masque(self):
        if self.df_indicateurs is not None:
            if self.chk_hide_empty_months.isChecked():
                df_affiche = self.get_df_masque_mois_vides(self.df_indicateurs)
            else:
                df_affiche = self.df_indicateurs
            self.afficher_table(df_affiche)

    def get_df_masque_mois_vides(self, df):
        # On ne masque QUE les colonnes (mois) où toutes les lignes "Réalisé..." et "Soumis..." == 0
        # On cherche les lignes qui concernent la réalisation/soumission (labels fixes)
        mask_realise = df["Catégorie - Sous-catégorie"].str.endswith("- Réalisé dans le mois (dans les temps)")
        mask_realise |= df["Catégorie - Sous-catégorie"].str.endswith("- Réalisé dans le mois (hors délai)")
        mask_realise |= df["Catégorie - Sous-catégorie"].str.endswith("- Réalisé dans le mois (absence d'échéance)")
        mask_realise |= df["Catégorie - Sous-catégorie"].str.endswith("- Soumis dans le mois")
        df_sub = df[mask_realise]
        mois_cols = [col for col in df.columns if col != "Catégorie - Sous-catégorie"]
        # Colonnes où toutes les valeurs de ces lignes sont 0
        mois_to_hide = []
        for col in mois_cols:
            if (df_sub[col] == 0).all():
                mois_to_hide.append(col)
        # On masque ces colonnes
        cols_affichees = ["Catégorie - Sous-catégorie"] + [col for col in mois_cols if col not in mois_to_hide]
        return df[cols_affichees]

    def on_filter_changed(self, idx, val):
        # Réapplique TOUS les filtres (on ne filtre pas juste la colonne idx)
        self.apply_filters()

    def ensure_filters_exist(self, df):
        # Création intelligente des filtres dynamiques
        if hasattr(self, "filters_editors") and len(self.filters_editors) == len(df.columns):
            return

        # Supprimer anciens filtres
        while self.filters_layout.count():
            item = self.filters_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self.filters_editors = []

        for i, col in enumerate(df.columns):
            edit = QLineEdit()
            edit.setPlaceholderText(str(col))
            edit.setFixedWidth(140)
            edit.textChanged.connect(lambda val, idx=i: self.on_filter_changed(idx, val))
            self.filters_layout.addWidget(edit)
            self.filters_editors.append(edit)

    def apply_filters(self):
        # Filtre le DataFrame global, remet la page à 0, appelle refresh_table_page
        df = self.df_current
        if df is None:
            return

        df_filtered = df.copy()
        for i, edit in enumerate(self.filters_editors):
            val = edit.text().strip()
            if val:
                col = df.columns[i]
                df_filtered = df_filtered[df_filtered[col].astype(str).str.contains(val, case=False, na=False)]
        df_filtered = df_filtered.astype(str).fillna("").reset_index(drop=True)
        self.df_filtered = df_filtered
        self.page_index = 0
        self.refresh_table_page()

    def go_to_page(self, delta):
        # Change de page, appelle refresh_table_page
        n_rows = len(self.df_filtered) if self.df_filtered is not None else 0
        per_page = self.LINES_PER_PAGE  # Utilise ta constante, ou self.LINES_PER_PAGE si attribut de classe
        n_pages = (n_rows + per_page - 1) // per_page

        new_page = max(0, min(self.page_index + delta, n_pages - 1))
        if new_page != self.page_index:
            self.page_index = new_page
            self.refresh_table_page()

    def refresh_table_page(self, editable_col=None):
        # Affiche la page courante du DataFrame filtré
        df = self.df_filtered
        total_rows = len(df)
        per_page = self.LINES_PER_PAGE
        page = self.page_index
        start = page * per_page
        end = min(start + per_page, total_rows)
        df_page = df.iloc[start:end]

        # Reset la table pour la page courante
        self.table.clear()
        self.table.setRowCount(len(df_page))
        self.table.setColumnCount(len(df_page.columns))
        self.table.setHorizontalHeaderLabels(df_page.columns)

        # Remplissage de la table
        for i in range(len(df_page)):
            for j in range(len(df_page.columns)):
                val = str(df_page.iat[i, j]) if pd.notna(df_page.iat[i, j]) else ""
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)

        # Optionnel : stylisation/merge/coloraion
        self.update_table_display(df_page, editable_col)

        # Pagination
        n_pages = (total_rows + per_page - 1) // per_page
        self.label_page.setText(f"Page {page + 1} / {n_pages if n_pages else 1}")
        self.btn_prev.setEnabled(page > 0)
        self.btn_next.setEnabled(end < total_rows)

    def update_table_display(self, df, editable_col=None):
        from PyQt5.QtGui import QBrush, QColor

        df = df.astype(str).fillna("")
        df = df.reset_index(drop=True)

        # Défusionner toutes les cellules avant réaffichage
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                self.table.setSpan(row, col, 1, 1)

        self.table.clear()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)

        for i in range(len(df)):
            # Détection d’une ligne "Données manquantes"
            is_missing = (
                    "Indicateur (Validation) en %" in df.columns and
                    str(df.at[i, "Indicateur (Validation) en %"]).strip().lower() == "données manquantes"
            )

            if is_missing:
                jaune_clair = QBrush(QColor(255, 255, 153))  # Jaune pâle

                # 1. Afficher l’infrapôle (1ère colonne)
                item_infrapole = QTableWidgetItem(str(df.at[i, "Infrapôles"]))
                item_infrapole.setFlags(item_infrapole.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 0, item_infrapole)

                # 2. Créer la cellule fusionnée pour le reste, fond jaune clair
                item_missing = QTableWidgetItem("Données manquantes")
                font = item_missing.font()
                font.setBold(True)
                item_missing.setFont(font)
                item_missing.setTextAlignment(Qt.AlignCenter)
                item_missing.setFlags(item_missing.flags() & ~Qt.ItemIsEditable)
                item_missing.setBackground(jaune_clair)

                # Fusionner toutes les colonnes sauf la 1ère (de 1 à N)
                self.table.setSpan(i, 1, 1, self.table.columnCount() - 1)
                self.table.setItem(i, 1, item_missing)
                # Vider les autres cellules fusionnées (optionnel)
                for j in range(2, self.table.columnCount()):
                    cell = QTableWidgetItem()
                    cell.setBackground(jaune_clair)
                    self.table.setItem(i, j, cell)
            else:
                for j in range(len(df.columns)):
                    value = str(df.iat[i, j])
                    item = QTableWidgetItem(value)
                    if editable_col and df.columns[j] == editable_col:
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
                    else:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(i, j, item)

    def lancer_activite(self):
        if self.df_source is None:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")
            return
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_calculate_activite.setEnabled(False)
        self.btn_calculate.setEnabled(False)
        self.thread_activite = QThread()
        from app.es_worker import SectionStrCalcWorker
        self.worker_activite = SectionStrCalcWorker(self.df_source.copy(), calcul_tdb_section_structure_activite)
        self.worker_activite.moveToThread(self.thread_activite)
        self.thread_activite.started.connect(self.worker_activite.run)
        self.worker_activite.progress.connect(self.progress.setValue)
        self.worker_activite.finished.connect(self._on_activite_finished)
        self.worker_activite.finished.connect(self.thread_activite.quit)
        self.worker_activite.finished.connect(self.worker_activite.deleteLater)
        self.thread_activite.finished.connect(self.thread_activite.deleteLater)
        self.thread_activite.start()

    def _on_activite_finished(self, df_result):
        self.progress.setVisible(False)
        self.btn_calculate_activite.setEnabled(True)
        self.btn_calculate.setEnabled(True)
        if df_result is None:
            QMessageBox.critical(self, "Erreur", "Erreur lors du calcul activité.")
            return
        self.df_activite = df_result
        self.afficher_table(df_result)

        self.msg_label.setText("Analyse réalisée.")
        self.msg_label.setVisible(True)
        self.btn_export.setVisible(True)
        self.btn_export.setEnabled(True)
        self.btn_graph_activite.setVisible(True)
        self.btn_graph_activite.setEnabled(True)

    def calculer(self):
        if self.df_source is None:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_calculate_activite.setEnabled(False)
        self.btn_calculate.setEnabled(False)
        self.chk_hide_empty_months.setEnabled(False)

        self.thread = QThread()
        self.worker = SectionStrCalcWorker(self.df_source, calcul_tdb_section_structure)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_calc_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def _on_calc_finished(self, df_result):
        self.progress.setVisible(False)
        self.btn_calculate_activite.setEnabled(True)
        self.btn_calculate.setEnabled(True)
        self.chk_hide_empty_months.setEnabled(True)
        if df_result is None:
            QMessageBox.critical(self, "Erreur", "Erreur lors du calcul ou pas de données exploitables.")
            return
        self.df_indicateurs = df_result
        self.afficher_table_masque()
        self.msg_label.setText("Analyse réalisée.")
        self.msg_label.setVisible(True)
        self.btn_export.setVisible(True)
        self.btn_export.setEnabled(True)
        self.btn_graph.setVisible(True)
        self.btn_graph.setEnabled(True)

    def exporter(self):
        # 1. Synchroniser les commentaires éventuels édités
        df_to_export = self.sync_commentaires_from_table(
            self.df_indicateurs if hasattr(self, 'df_indicateurs') else self.df_filtered)
        if df_to_export is None or df_to_export.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à exporter.")
            return

        # 2. Déterminer trimestre et année sélectionnés
        trimestre = self.get_selected_trimestre()
        try:
            annee = int(self.combo_annee.currentText())
        except Exception:
            annee = datetime.datetime.now().year

        # 3. Générer nom de fichier
        today_str = datetime.datetime.now().strftime("%d-%m-%Y")

        if trimestre == "Aujourd'hui":
            nom_fichier = f"Tdb_pat_str_{today_str}.xlsx"
        else:
            nom_fichier = f"Visites-cycliques_indicateur-OT_{trimestre}_{annee}.xlsx"

        nom_fichier = f"Tdb_pat_str_{today_str}.xlsx"

        file_name, _ = QFileDialog.getSaveFileName(self, "Exporter", nom_fichier, "Excel Files (*.xlsx)")
        if not file_name:
            return

        # 4. Appeler la fonction d’export
        try:
            export_visites_cycliques(
                df_to_export,
                trimestre,
                annee,
                file_name,
                MODEL_VISITES_PATH  # À adapter à la constante de chemin de modèle dans ton projet
            )
            QMessageBox.information(self, "Export", "Export terminé.")
        except Exception as e:
            QMessageBox.critical(self, "Erreur export", f"Erreur lors de l'export : {e}")

    def exporter_sans_model(self):
        today_str = datetime.datetime.now().strftime("%d-%m-%Y")
        nom_fichier = f"TDB_PAT_Structures_{today_str}.xlsx"
        file_name, _ = QFileDialog.getSaveFileName(self, "Exporter", nom_fichier, "Excel Files (*.xlsx)")
        if not file_name:
            return
        if self.chk_hide_empty_months.isChecked():
            df_export = self.get_df_masque_mois_vides(self.df_indicateurs)
        else:
            df_export = self.df_indicateurs
        df_export.to_excel(file_name, index=False)

    def afficher_graphique(self):
        if self.df_indicateurs is None or self.df_indicateurs.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à afficher.")
            return
        dlg = PatStrGraphDialog(self.df_indicateurs, self)
        dlg.exec_()

    def show_graph_activite(self):
        if self.df_activite is None or self.df_activite.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à afficher.")
            return
        dlg = PatStrActiviteGraphDialog(self.df_activite, self)
        dlg.exec_()
