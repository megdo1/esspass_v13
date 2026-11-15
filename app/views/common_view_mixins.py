"""Mixins partagés par les vues d'import de fichiers. Initiales : I=IndicateursOAView, P=PreconisationsView, S=SARView, V=VisitesCycliquesView."""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QProgressBar, QLabel, QMessageBox, QComboBox, QFileDialog, QRadioButton, QButtonGroup, QLineEdit, QScrollArea, QFrame, QHeaderView, QSizePolicy, QDialog
from PyQt5.QtCore import Qt, QThread
import datetime
from app.dialogs.details_sauvegarde_dialog import DetailsSauvegardeDialog
from app.dialogs.new_save_dialog import DialogNouvelleSauvegarde
from app.es_workers.load_worker import LoadWorker
from app.es_workers.verify_worker import VerifyWorker
from app.utils_excel import check_required_columns, extract_data_pigc_file_granular
from app.widgets.sauvegardes_combo import load_sauvegardes_metadata, populate_sauvegardes_combo
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class CommonViewMixin:
    """Méthodes communes aux 4 vues d'import de fichiers (Indicateurs OA, Préconisations, SAR, Visites)."""

    # ************************************************  INITIALISATION ************************************************
    def init_sources(self):
        source_layout = QHBoxLayout()
        source_layout.addStretch()
        source_label = QLabel("Source des données")
        self.radio_flux = QRadioButton("PIGC (flux)")
        self.radio_file = QRadioButton("Fichier (chargement)")
        self.radio_histo = QRadioButton("Historique (base)")
        # self.radio_file.setChecked(True)
        self.radio_histo.setChecked(True)
        self.source_group = QButtonGroup(self)
        self.source_group.addButton(self.radio_flux)
        self.source_group.addButton(self.radio_file)
        self.source_group.addButton(self.radio_histo)
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.radio_flux)
        source_layout.addWidget(self.radio_file)
        source_layout.addWidget(self.radio_histo)
        source_layout.addStretch()
        return source_layout

    def init_sauvegardes(self):
        self.histo_frame = QFrame()
        self.histo_layout = QHBoxLayout()
        self.histo_frame.setLayout(self.histo_layout)
        self.histo_frame.setVisible(False)

        # Combo sélection sauvegarde
        self.histo_layout.addStretch(1)  # Pour centrer
        self.combo_sauvegarde = QComboBox()
        self.combo_sauvegarde.addItem("Choisir une sauvegarde")
        # Rendre le 1er item non sélectionnable :
        model = self.combo_sauvegarde.model()
        index = model.index(0, 0)
        model.setData(index, 0, Qt.UserRole - 1)  # Désactive le 1er item
        self.histo_layout.addWidget(self.combo_sauvegarde)

        self.link_details = QLabel('<a href="#">Détails</a>')
        self.link_details.setVisible(False)
        self.link_details.setTextFormat(Qt.RichText)
        self.link_details.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.link_details.setOpenExternalLinks(False)  # on veut capter le clic nous-même
        self.histo_layout.addWidget(self.link_details)

        # Bouton nouvelle sauvegarde
        self.btn_new_save = QPushButton("Nouvelle sauvegarde")
        self.histo_layout.addWidget(self.btn_new_save)
        self.histo_layout.addStretch(1)  # Pour centrer
        # self.histo_layout.addStretch()

        self.histo_layout.setSpacing(0)
        self.histo_layout.setContentsMargins(0, 0, 0, 0)
        self.histo_frame.setContentsMargins(0, 0, 0, 0)
        self.histo_frame.setStyleSheet("margin:0px; padding:0px;") # border:0px;
        self.histo_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

    def init_filtres(self):
        self.filters_frame = QFrame()
        self.filters_layout = QHBoxLayout()
        self.filters_layout.setSpacing(2)
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        # self.filters_layout.setContentsMargins(5, 2, 5, 2)
        self.filters_editors = []
        self.filters_frame.setLayout(self.filters_layout)

        self.filters_scroll = QScrollArea()
        self.filters_scroll.setWidgetResizable(True)
        self.filters_scroll.setFixedHeight(50)
        self.filters_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.filters_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.filters_scroll.setFrameShape(QFrame.NoFrame)
        self.filters_scroll.setWidget(self.filters_frame)

    def harmoniser_link(self):
        height = 32  # Adapte selon le rendu visuel, 32 est standard pour Qt
        font = self.combo_annee.font()
        font.setPointSize(11)

        self.link_details.setFixedHeight(height)
        self.link_details.setFont(font)
        self.link_details.setStyleSheet("""
                    QLabel {
                        color: #1F4E9C;
                        font-size: 13px;
                        padding-left: 10px;
                        padding-right: 10px;
                    }
                    QLabel:hover {
                        text-decoration: underline;
                    }
                """)

    def init_affichage_table(self):
        self.table = QTableWidget()
        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)

    def init_pagination(self):
        self.btn_prev = QPushButton("Précédent")
        self.btn_next = QPushButton("Suivant")
        self.label_page = QLabel("Page 1 / 1")
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addWidget(self.label_page)
        pagination_layout.addWidget(self.btn_next)
        pagination_layout.addStretch()
        return pagination_layout

    def init_boutons_post_actions(self):
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.setAlignment(Qt.AlignRight)
        self.btn_export = QPushButton("Exporter le résultat")
        self.btn_graph = QPushButton("Graphique")
        bottom_btn_layout.addWidget(self.btn_export)
        bottom_btn_layout.addWidget(self.btn_graph)
        return bottom_btn_layout

    def init_visibilite(self):
        self.progress.setVisible(False)
        self.filters_scroll.setVisible(False)
        self.msg_label.setVisible(False)
        self.table.setVisible(False)

        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)

    # ************************************************** CHARGEMENT **************************************************
    def load_file(self, save=None):
        if save:
            file_name = save
        else:
            # Chargement du fichier, préparation du DataFrame
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Charger un fichier Excel", "", "Excel Files (*.xlsx *.xls)"
            )
        if not file_name:
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.msg_label.setVisible(False)
        self.table.setVisible(False)
        self.filters_scroll.setVisible(False)
        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)

        self.thread = QThread()
        self.worker = LoadWorker(file_name, extract_data_pigc_file_granular)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_load_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    # ************************************************  GESTION FILTRES ***********************************************
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

    def on_filter_changed(self, idx, val):
        self.apply_filters()

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

    # *************************************************  PAGINATION **************************************************
    def go_to_page(self, delta):
        # Change de page, appelle refresh_table_page
        n_rows = len(self.df_filtered) if self.df_filtered is not None else 0
        per_page = self.LINES_PER_PAGE  # Utilise ta constante, ou self.LINES_PER_PAGE si attribut de classe
        n_pages = (n_rows + per_page - 1) // per_page

        new_page = max(0, min(self.page_index + delta, n_pages - 1))
        if new_page != self.page_index:
            self.page_index = new_page
            self.refresh_table_page()

    def ouvrir_fenetre_sauvegarde(self):
        dialog = DialogNouvelleSauvegarde(self)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_sauvegardes()


class SharedIPVMixin:
    """Méthodes identiques partagées par IndicateursOAView + PreconisationsView + VisitesCycliquesView."""

    def refresh_sauvegardes(self):
        md_list = load_sauvegardes_metadata()
        self.sauvegardes_metadata = md_list  # si tu en as besoin ailleurs (ex: dialog détails)
        populate_sauvegardes_combo(self.combo_sauvegarde, md_list)

    def on_sauvegarde_selected(self, idx):
        if idx <= 0:
            self.histo_frame.setVisible(False)
            return

        model = self.combo_sauvegarde.model()
        idx_model = model.index(idx, 0)
        md = model.data(idx_model, Qt.UserRole)

        # Si c’est un header (non sélectionnable), md sera None
        if not isinstance(md, dict):
            # Réinitialiser sur un choix valide éventuel
            return

        self.link_details.setVisible(True)
        self.sauvegarde_courante = md

        # Charger la sauvegarde correspondante
        self.load_file(save=md.get('fichier', None))

    def show_details_sauvegarde_dialog_prod(self):
        idx = self.combo_sauvegarde.currentIndex()
        if idx <= 0 or not hasattr(self, 'sauvegardes_metadata') or idx > len(self.sauvegardes_metadata):
            return
        md = self.sauvegardes_metadata[idx - 1]
        # Ouvre la fenêtre non bloquante
        self._details_win = DetailsSauvegardeDialog(md, parent=self)
        self._details_win.show()

    def show_details_sauvegarde_dialog(self):
        idx = self.combo_sauvegarde.currentIndex()
        if idx <= 0:
            return

        model = self.combo_sauvegarde.model()
        idx_model = model.index(idx, 0)
        md = model.data(idx_model, Qt.UserRole)

        # Si l'utilisateur a cliqué sur un entête de catégorie ou un item invalide
        if not isinstance(md, dict):
            md = getattr(self, "sauvegarde_courante", None)

        if not isinstance(md, dict):
            # Rien à afficher
            return

        # Ouvre la fenêtre non bloquante
        self._details_win = DetailsSauvegardeDialog(md, parent=self)
        self._details_win.show()


class SharedISVMixin:
    """Méthodes identiques partagées par IndicateursOAView + SARView + VisitesCycliquesView."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_source = None
        self.df_indicateurs = None
        self.df_affichee = None
        self.init_ui()
        self.connect_signals()
        self.LINES_PER_PAGE = 1000
        self.show_mode("histo")

    # ************************************************  UTILITAIRES **************************************************
    def get_selected_trimestre(self):
        for i, btn in enumerate(self.trimestre_radios):
            if btn.isChecked():
                return ["Aujourd'hui", "T1", "T2", "T3", "T4", "T5"][i]
        return "Aujourd'hui"

    def sync_commentaires_from_table(self, df, commentaire_col="Commentaires"):
        """
        Met à jour le DataFrame 'df' avec les valeurs de la colonne 'Commentaires' du QTableWidget self.table.
        """
        if commentaire_col not in df.columns:
            return df
        df = df.copy()
        col_index = list(df.columns).index(commentaire_col)
        for row in range(self.table.rowCount()):
            new_val = self.table.item(row, col_index)
            if new_val:
                df.iat[row, col_index] = new_val.text()
        return df


class SharedPSVMixin:
    """Méthodes identiques partagées par PreconisationsView + SARView + VisitesCycliquesView."""

    def harmoniser_combo(self):
        height = 32  # Adapte selon le rendu visuel, 32 est standard pour Qt
        font = self.combo_annee.font()
        font.setPointSize(11)

        for combo in [self.combo_sauvegarde, self.combo_annee]:
            combo.setFixedHeight(height)
            combo.setFont(font)
            combo.setStyleSheet("""
                QComboBox {
                    border: 1px solid #aaa;
                    border-radius: 6px;
                    padding: 4px 12px 4px 8px;
                    font-size: 13px;
                    background: white;
                }
                QComboBox:focus {
                    border: 1.5px solid #1F4E9C;
                }
            """)

    def init_ui(self):
        layout = QVBoxLayout()

        # Ligne 1: sources
        layout.addLayout(self.init_sources())

        # Ligne 2: gestion des sauvegardes
        self.init_sauvegardes()
        layout.addWidget(self.histo_frame)

        # Ligne 2/3: Boutons chargement, vérification, année, trimestre et calcul
        layout.addWidget(self.init_boutons_actions(), alignment=Qt.AlignHCenter | Qt.AlignTop)

        # Ligne 4: Filtres
        self.init_filtres()
        layout.addWidget(self.filters_scroll)

        # Barre de progression
        self.init_barre_progression()
        layout.addWidget(self.progress)

        # Zone message
        self.msg_label = QLabel("Travaux en cours...")
        self.msg_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.msg_label)

        # Table de résultat
        self.init_affichage_table()
        layout.addWidget(self.table)

        # Pagination
        layout.addLayout(self.init_pagination())

        # 7. Export/graphique
        layout.addLayout(self.init_boutons_post_actions())

        # Harmonisation
        self.harmoniser_combo()
        self.harmoniser_bouton()
        self.harmoniser_link()

        # 8. États initiaux
        self.init_visibilite()
        self.init_etat()

        self.setLayout(layout)


class SharedIPSMixin:
    """Méthodes identiques partagées par IndicateursOAView + PreconisationsView + SARView."""

    def update_table_display(self, df, editable_col=None):
        from PyQt5.QtGui import QBrush, QColor

        df = df.astype(str).fillna("")
        df = df.reset_index(drop=True)

        pourcentage_colors = [
            ("#f98c8c", 0, 0),
            ("#ffcc99", 0.01, 33),
            ("#fff799", 33.01, 66),
            ("#b7ffb7", 66.01, 99.99),
            ("#3eb94a", 100, 100),
        ]

        # données manquantes
        for row in range(self.table.rowCount()):
            # Gestion "données manquantes"
            is_missing = (
                    "Indicateur (Validation) en %" in df.columns and
                    str(df.at[row, "Indicateur (Validation) en %"]).strip().lower() == "données manquantes"
            )
            if is_missing:
                jaune_clair = QBrush(QColor(255, 255, 153))  # Jaune pâle
                item_infrapole = QTableWidgetItem(str(df.at[row, "Infrapôles"]))
                item_infrapole.setFlags(item_infrapole.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, item_infrapole)
                item_missing = QTableWidgetItem("Données manquantes")
                font = item_missing.font()
                font.setBold(True)
                item_missing.setFont(font)
                item_missing.setTextAlignment(Qt.AlignCenter)
                item_missing.setFlags(item_missing.flags() & ~Qt.ItemIsEditable)
                item_missing.setBackground(jaune_clair)
                self.table.setSpan(row, 1, 1, self.table.columnCount() - 1)
                self.table.setItem(row, 1, item_missing)
                for j in range(2, self.table.columnCount()):
                    cell = QTableWidgetItem()
                    cell.setBackground(jaune_clair)
                    self.table.setItem(row, j, cell)
            else:
                for col in range(self.table.columnCount()):
                    value = str(df.iat[row, col])
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    header = df.columns[col].strip().lower()
                    # Gras sur colonne "Indicateur"
                    if header == "indicateur":
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    # Coloration des pourcentages
                    is_percent_col = "%" in header or "pourcent" in header or "en %" in header
                    is_percent_val = "%" in value
                    if is_percent_col or is_percent_val:
                        val = value.replace("%", "").replace(",", ".").strip()
                        try:
                            val_num = float(val)
                            couleur = None
                            for hexcol, mini, maxi in pourcentage_colors:
                                if mini <= val_num <= maxi:
                                    couleur = hexcol
                                    break
                            if couleur:
                                item.setBackground(QBrush(QColor(couleur)))
                                if couleur in ["#f98c8c", "#3eb94a"]:
                                    item.setForeground(QBrush(QColor("white")))
                        except Exception as e:
                            logger.debug("Exception ignorée dans update_table_display", exc_info=True)
                    if is_percent_col or is_percent_val or value.replace('.', '', 1).isdigit():
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)

        # Zebra stripes (après, mais sans écraser couleurs spéciales)
        for row in range(self.table.rowCount()):
            is_missing = (
                    "Indicateur (Validation) en %" in df.columns and
                    str(df.at[row, "Indicateur (Validation) en %"]).strip().lower() == "données manquantes"
            )
            if not is_missing and row % 2 == 1:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        couleur = item.background().color().name().lower()
                        if couleur not in [
                            "#f98c8c", "#ffcc99", "#fff799", "#b7ffb7", "#3eb94a"
                        ]:
                            item.setBackground(QBrush(QColor("#F4F6FA")))


class SharedPVMixin:
    """Méthodes identiques partagées par PreconisationsView + VisitesCycliquesView."""

    def harmoniser_bouton(self):
        height = 32  # Adapte selon le rendu visuel, 32 est standard pour Qt
        font = self.combo_annee.font()
        font.setPointSize(11)

        for btn in [self.btn_verify, self.btn_calcul, self.btn_load, self.btn_new_save, self.btn_export,
                    self.btn_graph]:
            btn.setFixedHeight(height)
            btn.setFont(font)
            btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #1F4E9C;
                    border-radius: 6px;
                    background: #F8FAFC;
                    font-size: 13px;
                    padding: 4px 18px;
                }
                QPushButton:focus {
                    border: 2px solid #1F4E9C;
                }
            """)

    def init_barre_progression(self):
        self.progress = QProgressBar()

        self.progress.setStyleSheet("""
                    QProgressBar {
                        border: none;
                        text-align: center;
                        height: 16px;
                        background-color: #EEE;
                        border-radius: 8px;
                    }
                    QProgressBar::chunk {
                        background-color: #4DB37D;  /* vert légèrement désaturé */
                        border-radius: 8px;
                        margin: 0px;
                    }
                """)

    def init_etat(self):
        self.btn_verify.setEnabled(False)
        self.combo_annee.setEnabled(False)
        for btn in self.trimestre_radios:
            btn.setEnabled(False)
        self.btn_calcul.setEnabled(False)

        self.btn_export.setEnabled(False)
        self.btn_graph.setEnabled(False)

    def config_ui_post_calcul(self):
        self.msg_label.setText("")
        self.msg_label.setVisible(False)

        self.filters_scroll.setVisible(True)
        self.table.setVisible(True)
        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

        self.btn_export.setVisible(True)
        self.btn_export.setEnabled(True)
        self.btn_graph.setVisible(True)
        self.btn_graph.setEnabled(True)

    def show_mode(self, mode):
        is_flux = (mode == "flux")
        is_file = (mode == "file")
        is_histo = (mode == "histo")

        self.btn_load.setVisible(is_file)
        self.btn_verify.setVisible(is_file or is_histo)
        # self.combo_infrapole.setVisible(is_file or is_histo)
        self.combo_annee.setVisible(is_file or is_histo)
        for btn in self.trimestre_radios:
            btn.setVisible(is_file or is_histo)
        self.btn_calcul.setVisible(is_file or is_histo)

        self.progress.setVisible(False)
        self.table.setVisible(False)
        self.msg_label.setVisible(False)
        self.filters_scroll.setVisible(False)

        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        self.btn_export.setVisible(is_file and getattr(self, "df_indicateurs", None) is not None)
        self.btn_graph.setVisible(is_file and getattr(self, "df_indicateurs", None) is not None)

        if not (is_file or is_histo):
            self.msg_label.setText("Le mode 'PIGC (flux)' n'est pas encore implémenté.")
            self.msg_label.setVisible(True)

        self.histo_frame.setVisible(is_histo)

        if is_histo:
            self.btn_verify.setText("Vérifier le contenu de la sauvegarde")
            self.refresh_sauvegardes()

    # ********************************************** GESTION SAUVEGARDES **********************************************
    def refresh_sauvegardes_prod(self):
        import os, json
        dir_saves = os.path.join(os.getcwd(), "sauvegardes")
        metadata_path = os.path.join(dir_saves, "metadata.json")
        self.combo_sauvegarde.blockSignals(True)
        self.combo_sauvegarde.clear()
        self.combo_sauvegarde.addItem("Choisir une sauvegarde")
        # Rendre le 1er item non sélectionnable :
        model = self.combo_sauvegarde.model()
        index = model.index(0, 0)
        model.setData(index, 0, Qt.UserRole - 1)  # Désactive le 1er item
        self.sauvegardes_metadata = []
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                try:
                    self.sauvegardes_metadata = json.load(f)
                    for md in self.sauvegardes_metadata:
                        label = f"{md['nom_sauvegarde']} ({md['categorie']}, {md['date_valeur']})"
                        self.combo_sauvegarde.addItem(label)
                except Exception:
                    logger.debug("Exception ignorée dans refresh_sauvegardes_prod", exc_info=True)
        self.combo_sauvegarde.blockSignals(False)

    def on_sauvegarde_selected_prod(self, idx):
        if idx <= 0 or not hasattr(self, 'sauvegardes_metadata') or idx > len(self.sauvegardes_metadata):
            # self.histo_action_frame.setVisible(False)
            self.histo_frame.setVisible(False)
            return

        self.link_details.setVisible(True)
        md = self.sauvegardes_metadata[idx - 1]

        self.sauvegarde_courante = md
        self.load_file(save=md['fichier'])

    def _on_load_finished(self, df_data, idx_en_tete):
        self.progress.setVisible(False)
        self.btn_calcul.setEnabled(True)
        self.msg_label.setText("Fichier chargé. Cliquez sur 'Vérifier le contenu' ou 'Calculer les indicateurs'.")
        self.msg_label.setVisible(True)
        self.btn_verify.setEnabled(True)
        # self.combo_annee.setEnabled(True)
        for btn in self.trimestre_radios:
            btn.setEnabled(True)
        self.table.setVisible(False)
        self.filters_scroll.setVisible(False)

        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)

        if df_data is None:
            QMessageBox.critical(self, "Erreur", "Le fichier chargé ne respecte pas le format attendu.")
            return

        missing_cols = check_required_columns(df_data, self.REQUIRED_COLS)
        if missing_cols:
            QMessageBox.critical(self, "Colonnes absentes", f"Colonnes manquantes : {', '.join(missing_cols)}")
            self.progress.setVisible(False)
            return
        self.df_source = df_data
        self.fill_annee()


class SharedISMixin:
    """Méthodes identiques partagées par IndicateursOAView + SARView."""

    def init_barre_progression(self):
        self.progress = QProgressBar()

        self.progress.setStyleSheet("""
                    QProgressBar {
                        border: none;
                        text-align: center;
                        height: 16px;
                        background-color: #EEE;
                        border-radius: 8px;
                    }
                    QProgressBar::chunk {
                        background-color: #1F4E9C;  /* Violet doux */
                        border-radius: 8px;
                        margin: 0px;
                    }
                """)

    def fill_annee(self):
        self.combo_annee.clear()
        df = self.df_source

        if "Programme" in df.columns:
            # Convertir la colonne Date en datetime, puis extraire les années uniques
            try:
                # dates = pd.to_datetime(df["Programme"], errors="coerce", dayfirst=True)
                annees = df["Programme"].astype(str).str.extractall(r"(20\d{2})")[0]
                # annees_uniques = sorted(annees.dropna().dt.year.unique(), reverse=True)
                annees_uniques = sorted(annees.dropna().astype(int).unique(), reverse=True)

                if annees_uniques:
                    self.combo_annee.setEnabled(True)
                    for an in annees_uniques:
                        self.combo_annee.addItem(str(an))
                    try:
                        annee_courante = str(datetime.datetime.now().year)
                        index = self.combo_annee.findText(annee_courante)
                        if index != -1:
                            self.combo_annee.setCurrentIndex(index)
                    except Exception as e:
                        logger.error(f"Erreur positionnement année courante : {e}")
                else:
                    self.combo_annee.setEnabled(False)
                    QMessageBox.warning(self, "Programme",
                                        "Aucune année détectée dans la colonne Date du fichier chargé.")
                    self.combo_annee.addItem("Année")
            except Exception as e:
                self.combo_annee.setEnabled(False)
                self.combo_annee.addItem("Année")
                QMessageBox.warning(self, "Date", f"Erreur lors de la lecture des années : {e}")
        else:
            self.combo_annee.setEnabled(False)
            self.combo_annee.addItem("Année")
            QMessageBox.warning(self, "Programme",
                                "La colonne Programme est absente du fichier chargé.\nLe champ Année est "
                                "indisponible pour le traitement des reliquats")

    # ******************************************  VERIFICATION DU CONTENU ********************************************
    def verify_file(self):
        if self.df_source is None:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.progress.setFormat("Vérification... %p%")
        self.msg_label.setText("Vérification en cours...")
        self.msg_label.setVisible(True)
        self.table.setVisible(False)
        self.filters_scroll.setVisible(False)
        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)
        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        self.thread_verify = QThread()
        self.worker_verify = VerifyWorker(self.df_source.copy())
        self.worker_verify.moveToThread(self.thread_verify)
        self.thread_verify.started.connect(self.worker_verify.run)
        self.worker_verify.progress.connect(self.progress.setValue)
        self.worker_verify.finished.connect(self._on_verify_finished)
        self.worker_verify.finished.connect(self.thread_verify.quit)
        self.worker_verify.finished.connect(self.worker_verify.deleteLater)
        self.thread_verify.finished.connect(self.thread_verify.deleteLater)
        self.thread_verify.start()


class SharedPSMixin:
    """Méthodes identiques partagées par PreconisationsView + SARView."""

    # **********************************************  GESTION AFFICHAGE **********************************************
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

        self.table.setStyleSheet("""
                QTableWidget {
                    border: none;
                    font-family: 'Segoe UI', Arial, sans-serif;
                    font-size: 13px;
                    gridline-color: #E2E8F0;
                }
                QHeaderView::section {
                    color: #1A4286;
                    font-weight: bold;
                    border: 1px solid #CBD5E1;
                    padding: 6px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }
                QTableWidget::item:selected {
                    color: #0F2A52;
                    font-weight: bold;
                }
                QTableWidget::item:focus {
                    outline: none;
                }
                QTableWidget {
                    selection-color: #0F2A52;
                }
                """)


class SharedIPMixin:
    """Méthodes identiques partagées par IndicateursOAView + PreconisationsView."""

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

        self.update_table_display(df_page, editable_col)

        # Pagination
        n_pages = (total_rows + per_page - 1) // per_page
        self.label_page.setText(f"Page {page + 1} / {n_pages if n_pages else 1}")
        self.btn_prev.setEnabled(page > 0)
        self.btn_next.setEnabled(end < total_rows)


class SharedSVMixin:
    """Méthodes identiques partagées par SARView + VisitesCycliquesView."""

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
