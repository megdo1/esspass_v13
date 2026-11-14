import os

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QTableWidgetItem, QMessageBox, QComboBox, QFileDialog, QRadioButton, QButtonGroup, QFrame
from PyQt5.QtCore import Qt
import datetime
import pandas as pd

from app.logic.logic_visite import calcul_indicateurs_visite
from app.export.export_visite import export_visites_cycliques
from app.dialogs.ui_graphdialog import GraphDialog
from app.ressources import MODEL_VISITES_PATH
from app.views.common_view_mixins import CommonViewMixin, SharedIPVMixin, SharedISVMixin, SharedPSVMixin, SharedPVMixin, SharedSVMixin
import logging

logger = logging.getLogger(__name__)


class VisitesCycliquesView(CommonViewMixin, SharedIPVMixin, SharedISVMixin, SharedPSVMixin, SharedPVMixin, SharedSVMixin, QWidget):
    REQUIRED_COLS = [
        "Infrapôle", "Catégorie", "Etat d'avancement", "Statut"
    ]


    def init_boutons_actions(self):
        # Ligne 2-3 (en fonction de la source): Boutons chargement, vérification, année, trimestre et calcul
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        # btn_layout.setAlignment(Qt.AlignTop)

        self.btn_load = QPushButton("Charger un fichier")
        self.btn_verify = QPushButton("Vérifier le contenu")
        """
        self.combo_infrapole = QComboBox()
        self.combo_infrapole.addItem("Infrapôle")
        self.combo_infrapole.setEnabled(False)
        self.combo_infrapole.setFixedWidth(220)
        """
        self.combo_annee = QComboBox()
        self.combo_annee.setToolTip("Année (extraites de la colonne Date du fichier chargé)")
        annee_courante = datetime.datetime.now().year
        self.combo_annee.addItem(str(annee_courante))
        # self.combo_annee.addItems([str(annee_courante), str(annee_courante + 1)])
        # self.combo_annee.addItem("Année")
        # self.combo_annee.addItem("2025")
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
        # btn_layout.addWidget(self.combo_infrapole)
        btn_layout.addWidget(self.combo_annee)
        for btn in self.trimestre_radios:
            btn_layout.addWidget(btn)
        self.btn_calcul = QPushButton("Calculer les indicateurs")
        btn_layout.addWidget(self.btn_calcul)
        btn_frame = QFrame()
        btn_frame.setLayout(btn_layout)
        return btn_frame

        # self.filters_scroll.setVisible(False)


        # self.progress.setVisible(False)


    # ***************************************** CONFIG: INTERFACE, BOUTONS... *****************************************
    def config_ui_post_verification(self):
        self.progress.setVisible(False)
        self.msg_label.setText("Vérification visuelle : données source.")
        self.msg_label.setVisible(True)

        self.table.setVisible(True)
        self.filters_scroll.setVisible(True)

        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)


    # ********************************************** EVENEMENTS BOUTONS **********************************************
    def connect_signals(self):
        # sources
        self.radio_flux.toggled.connect(lambda checked: self.show_mode("flux" if checked else "file"))
        self.radio_file.toggled.connect(lambda checked: self.show_mode("file" if checked else "flux"))
        self.radio_histo.toggled.connect(lambda checked: self.show_mode("histo" if checked else "file"))
        # print("DEBUG(Préconisations): connect_signals - 1", flush=True)
        # sauvegardes
        self.combo_sauvegarde.currentIndexChanged.connect(self.on_sauvegarde_selected)
        self.link_details.linkActivated.connect(self.show_details_sauvegarde_dialog)
        self.btn_new_save.clicked.connect(self.ouvrir_fenetre_sauvegarde)
        # print("DEBUG(Préconisations): connect_signals - 2", flush=True)
        # boutons actions
        self.btn_load.clicked.connect(self.load_file)
        self.btn_verify.clicked.connect(self.verify_file)
        self.btn_calcul.clicked.connect(self.calculer)
        # print("DEBUG(Préconisations): connect_signals - 3", flush=True)
        # Pagination
        self.btn_prev.clicked.connect(lambda: self.go_to_page(-1))
        self.btn_next.clicked.connect(lambda: self.go_to_page(+1))
        # print("DEBUG(Préconisations): connect_signals - 4", flush=True)
        # Export et graphique (si présents)
        self.btn_export.clicked.connect(self.exporter)
        self.btn_graph.clicked.connect(self.afficher_graphique)
        # print("DEBUG(Préconisations): connect_signals - 5", flush=True)


    def fill_annee(self):
        df = self.df_source
        self.combo_annee.clear()

        if "Date" in df.columns:
            # Convertir la colonne Date en datetime, puis extraire les années uniques
            try:
                dates = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
                annees_uniques = sorted(dates.dropna().dt.year.unique(), reverse=True)
                if annees_uniques:
                    self.combo_annee.setEnabled(True)
                    for an in annees_uniques:
                        self.combo_annee.addItem(str(an))
                else:
                    self.combo_annee.setEnabled(False)
                    QMessageBox.warning(self, "Date",
                                        "Aucune année détectée dans la colonne Date du fichier chargé.")
                    self.combo_annee.addItem("Année")
            except Exception as e:
                self.combo_annee.setEnabled(False)
                self.combo_annee.addItem("Année")
                QMessageBox.warning(self, "Date", f"Erreur lors de la lecture des années : {e}")
        else:
            self.combo_annee.setEnabled(False)
            self.combo_annee.addItem("Année")
            QMessageBox.warning(self, "Date",
                                "La colonne Date est absente du fichier chargé.\nLe champ Année est "
                                "indisponible pour le traitement des reliquats")

    # ******************************************  VERIFICATION DU CONTENU ********************************************
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
        self.btn_graph.setVisible(False)
        self.btn_prev.setVisible(False)
        self.btn_next.setVisible(False)
        self.label_page.setVisible(False)

        # Ici, tu pourrais ajouter une animation, un thread de progression, etc.
        # Pour une version instantanée :
        df = self.df_source.astype(str).fillna("").reset_index(drop=True)

        self.afficher_table(df)  # ou self.display_table(df)
        self.config_ui_post_verification()

        """self.msg_label.setText("Vérification visuelle : données source.")
        self.msg_label.setVisible(True)
        self.progress.setVisible(False)
        self.table.setVisible(True)
        self.filters_scroll.setVisible(True)
        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)"""

    # *******************************************  CALCUL des indicateurs ********************************************
    def calculer(self):
        trimestre = self.get_selected_trimestre()
        annee = int(self.combo_annee.currentText())

        # print("DEBUG: Calcul des indicateurs VC", flush=True)
        if self.df_source is None:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")
            return

        try:
            indic = calcul_indicateurs_visite(self.df_source, trimestre, annee)
            self.df_indicateurs = indic.astype(str).fillna("").reset_index(drop=True)
            self.afficher_table(self.df_indicateurs, editable_col="Commentaires")
            self.config_ui_post_calcul()

        except Exception as e:
            QMessageBox.critical(self, "Erreur calcul", str(e))


    # **********************************************  GESTION AFFICHAGE **********************************************
    def afficher_table(self, df, editable_col=None):
        # Affichage du tableau, appel ensure_filters_exist, refresh_table_page
        # Stocke le DataFrame à filtrer
        self.df_current = df
        self.df_filtered = df
        self.page_index = 0

        # S'assure que les filtres existent (créés une seule fois par structure)
        self.ensure_filters_exist(df)
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

        for row in range(self.table.rowCount()):
            # Gestion "données manquantes"
            is_missing = (
                    "Indicateur (Validation) en %" in df.columns and
                    str(df.at[row, "Indicateur (Validation) en %"]).strip().lower() == "données manquantes"
            )
            if is_missing:
                jaune_clair = QBrush(QColor(255, 255, 153))  # Jaune pâle

                # Affichage normal pour les 3 premières colonnes (0, 1, 2)
                for col in range(3):
                    value = str(df.iat[row, col])
                    item = QTableWidgetItem(value)
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    if "données manquantes" in value.lower():
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    item.setBackground(jaune_clair)
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)

                # Fusion à partir de la 4ᵉ colonne (index 3)
                span_col_start = 3
                span_col_count = self.table.columnCount() - span_col_start
                item_missing = QTableWidgetItem("Données manquantes")
                font = item_missing.font()
                font.setBold(True)
                item_missing.setFont(font)
                item_missing.setTextAlignment(Qt.AlignCenter)
                item_missing.setFlags(item_missing.flags() & ~Qt.ItemIsEditable)
                item_missing.setBackground(jaune_clair)
                self.table.setSpan(row, span_col_start, 1, span_col_count)
                self.table.setItem(row, span_col_start, item_missing)

                # Remplir le reste des colonnes fusionnées avec des cellules vides (facultatif, pour propreté)
                for j in range(span_col_start + 1, self.table.columnCount()):
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


    def exporter(self):
        # 1. Synchroniser les commentaires éventuels édités
        df_to_export = self.sync_commentaires_from_table(
            self.df_indicateurs if hasattr(self, 'df_indicateurs') else self.df_filtered)
        if df_to_export is None or df_to_export.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à exporter.")
            return

        # 2. Déterminer trimestre et année sélectionnés
        trimestre = self.get_selected_trimestre()  # À implémenter selon ton UI (radio boutons, combo, ...)
        try:
            annee = int(self.combo_annee.currentText())
        except Exception:
            annee = datetime.datetime.now().year

        # 3. Générer nom de fichier
        # today_str = datetime.datetime.now().strftime("%d-%m-%Y")
        today_str = datetime.datetime.now().strftime("%d-%m-%Y_%H%M")
        if trimestre == "Aujourd'hui":
            nom_fichier = f"Visites-cycliques_OT_{today_str}.xlsx"
        else:
            nom_fichier = f"Visites-cycliques_OT_{trimestre}_{annee}_{today_str}.xlsx"
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
            # QMessageBox.information(self, "Export", "Export terminé.")
            reponse = QMessageBox.question(
                self,
                "Fichier généré",
                "L'export est terminé.\nSouhaitez-vous ouvrir le fichier ?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reponse == QMessageBox.Yes:
                try:
                    os.startfile(file_name)
                except Exception as e:
                    QMessageBox.warning(self, "Ouverture impossible", f"Erreur lors de l'ouverture : {e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur export", f"Erreur lors de l'export : {e}")

    # *************************************************** GRAPHIQUE ***************************************************
    def afficher_graphique(self):
        # Affichage du graphique (si présent)
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à visualiser.")
            return

        dlg = GraphDialog(self.df_filtered, key=("ES-IND", "OT", "Visites cycliques"))
        dlg.exec_()
