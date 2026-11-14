import os

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMessageBox, QComboBox, QFileDialog, QRadioButton, QButtonGroup, QFrame
from PyQt5.QtCore import Qt, QThread, QTimer
import datetime

from app.dialogs.details_sauvegarde_dialog import DetailsSauvegardeDialog
from app.export.export_sar import export_sar_indicateurs
from app.utils_excel import check_required_columns
from app.dialogs.ui_graphdialog import GraphDialog
from app.ressources import MODEL_SAR_PATH
from app.views.common_view_mixins import CommonViewMixin, SharedIPSMixin, SharedISMixin, SharedISVMixin, SharedPSMixin, SharedPSVMixin, SharedSVMixin
import logging

logger = logging.getLogger(__name__)


class SARView(CommonViewMixin, SharedISVMixin, SharedPSVMixin, SharedIPSMixin, SharedISMixin, SharedPSMixin, SharedSVMixin, QWidget):
    REQUIRED_COLS = [
        "Catégorie", "Programme", "Etat d'avancement", "Urgence", "Date limite", "Date de réalisation",
        "Saisie de l'analyse de risque", "Mesure conservatoire différée", "Description mesure conservatoire",
        "Evènement / phénomène redouté", "Probabilité", "Hors délai"
    ]

        # print("DEBUG: __init__ - 4", flush=True)


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
        # annee_courante = datetime.datetime.now().year
        self.combo_annee.setToolTip("Année (extraites de la colonne Date du fichier chargé)")
        self.combo_annee.addItem("Année")
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
        self.btn_calculate = QPushButton("Calculer les indicateurs")
        btn_layout.addWidget(self.btn_calculate)
        btn_frame = QFrame()
        btn_frame.setLayout(btn_layout)
        return btn_frame

        # self.filters_scroll.setVisible(False)


    def harmoniser_bouton(self):
        height = 32  # Adapte selon le rendu visuel, 32 est standard pour Qt
        font = self.combo_annee.font()
        font.setPointSize(11)

        for btn in [self.btn_verify, self.btn_calculate, self.btn_load, self.btn_new_save, self.btn_export,
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


        # self.progress.setVisible(False)


    def init_etat(self):
        self.btn_verify.setEnabled(False)
        self.combo_annee.setEnabled(False)
        for btn in self.trimestre_radios:
            btn.setEnabled(False)
        self.btn_calculate.setEnabled(False)

        self.btn_export.setEnabled(False)
        self.btn_graph.setEnabled(False)

    # ***************************************** CONFIG: INTERFACE, BOUTONS... *****************************************

    def config_ui_post_verification(self):
        self.progress.setVisible(False)
        self.msg_label.setText("Vérification visuelle : données source.")
        self.msg_label.setVisible(True)

        self.filters_scroll.setVisible(True)
        self.table.setVisible(True)

        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)

    def config_ui_post_calcul(self):
        self.msg_label.setText("")
        self.msg_label.setVisible(False)

        self.table.setVisible(True)
        self.filters_scroll.setVisible(True)

        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

        self.btn_export.setVisible(True)
        self.btn_export.setEnabled(True)
        self.btn_graph.setVisible(False)
        # self.btn_graph.setEnabled(True)

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
        self.btn_calculate.setVisible(is_file or is_histo)

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

    # ********************************************** EVENEMENTS BOUTONS **********************************************
    def connect_signals(self):
        # sources
        self.radio_flux.toggled.connect(lambda checked: self.show_mode("flux" if checked else "file"))
        self.radio_file.toggled.connect(lambda checked: self.show_mode("file" if checked else "flux"))
        self.radio_histo.toggled.connect(lambda checked: self.show_mode("histo" if checked else "file"))
        # sauvegardes
        self.combo_sauvegarde.currentIndexChanged.connect(self.on_sauvegarde_selected)
        self.link_details.linkActivated.connect(self.show_details_sauvegarde_dialog)
        self.btn_new_save.clicked.connect(self.ouvrir_fenetre_sauvegarde)
        # boutons actions
        self.btn_load.clicked.connect(self.load_file)
        self.btn_verify.clicked.connect(self.verify_file)
        self.btn_calculate.clicked.connect(self.lancer_calcul)

        # Pagination
        self.btn_prev.clicked.connect(lambda: self.go_to_page(-1))
        self.btn_next.clicked.connect(lambda: self.go_to_page(+1))
        # Export et graphique (si présents)
        self.btn_export.clicked.connect(self.exporter)
        self.btn_graph.clicked.connect(self.afficher_graphique)


    def _on_load_finished(self, df_data, idx_en_tete):
        self.progress.setVisible(False)
        self.btn_calculate.setEnabled(True)
        self.msg_label.setText("Fichier chargé. Cliquez sur 'Vérifier le contenu' ou 'Calculer les indicateurs'.")
        self.msg_label.setVisible(True)
        self.btn_verify.setEnabled(True)
        self.combo_annee.setEnabled(True)
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


    def _on_verify_finished(self, df_verified):
        if df_verified is None or df_verified.empty:
            self.progress.setVisible(False)
            QMessageBox.warning(self, "Erreur", "Erreur lors de la vérification.")
            return

        self.progress.setValue(85)
        QTimer.singleShot(0, lambda: self._afficher_table_et_finaliser(df_verified))
        self.progress.setValue(100)
        self.config_ui_post_verification()

    # *******************************************  CALCUL des indicateurs ********************************************
    def lancer_calcul(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_calculate.setEnabled(False)

        from app.es_workers.sar_worker import SarCalcWorker

        annee = int(self.combo_annee.currentText())
        trimestre = self.get_selected_trimestre()

        self.thread_calc = QThread()
        self.worker_calc = SarCalcWorker(self.df_source.copy(), annee, trimestre)
        self.worker_calc.moveToThread(self.thread_calc)
        self.thread_calc.started.connect(self.worker_calc.run)
        self.worker_calc.progress.connect(self.progress.setValue)
        self.worker_calc.finished.connect(self.on_calcul_finished)
        self.worker_calc.finished.connect(self.thread_calc.quit)
        self.worker_calc.finished.connect(self.worker_calc.deleteLater)
        self.thread_calc.finished.connect(self.thread_calc.deleteLater)
        self.thread_calc.start()

    def on_calcul_finished(self, df_out):
        self.progress.setVisible(False)
        self.btn_calculate.setEnabled(True)

        if df_out is None or df_out.empty:
            QMessageBox.warning(self, "Erreur", "Aucun résultat de calcul.")
            return
        # Affiche le DataFrame (selon ton UI/table)
        self.df_indicateurs = df_out

        self.afficher_table(df_out)

        self.config_ui_post_calcul()

    # **********************************************  GESTION AFFICHAGE **********************************************
    def _afficher_table_et_finaliser(self, df_verified):
        self.afficher_table(df_verified)
        # self.progress.setValue(100)
        # self.progress.setVisible(False)
        # self.msg_label.setText("Vérification visuelle : données source.")
        # self.msg_label.setVisible(True)


        # self.filters_frame.setFixedWidth(self.table.viewport().width())


    # ********************************************** GESTION SAUVEGARDES **********************************************
    def refresh_sauvegardes(self):
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
                    logger.debug("Exception ignorée dans refresh_sauvegardes", exc_info=True)
        self.combo_sauvegarde.blockSignals(False)

    def on_sauvegarde_selected(self, idx):
        if idx <= 0 or not hasattr(self, 'sauvegardes_metadata') or idx > len(self.sauvegardes_metadata):
            # self.histo_action_frame.setVisible(False)
            self.histo_frame.setVisible(False)
            return

        self.link_details.setVisible(True)
        md = self.sauvegardes_metadata[idx - 1]

        self.sauvegarde_courante = md
        self.load_file(save=md['fichier'])

    def show_details_sauvegarde_dialog(self):
        idx = self.combo_sauvegarde.currentIndex()
        if idx <= 0 or not hasattr(self, 'sauvegardes_metadata') or idx > len(self.sauvegardes_metadata):
            return
        md = self.sauvegardes_metadata[idx - 1]
        # Ouvre la fenêtre non bloquante
        self._details_win = DetailsSauvegardeDialog(md, parent=self)
        self._details_win.show()


    # ************************************************** EXPORTATION **************************************************
    def exporter(self):
        df_to_export = self.sync_commentaires_from_table(
            self.df_indicateurs if hasattr(self, 'df_indicateurs') else self.df_filtered)
        if df_to_export is None or df_to_export.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à exporter.")
            return

        trimestre = self.get_selected_trimestre()

        try:
            annee = int(self.combo_annee.currentText())
        except Exception:
            annee = datetime.datetime.now().year

        today_str = datetime.datetime.now().strftime("%d-%m-%Y_%H%M")
        if trimestre == "Aujourd'hui":
            nom_fichier = f"Revue-SAR_{today_str}.xlsx"
        else:
            nom_fichier = f"Revue-SAR_{trimestre}_{annee}_{today_str}.xlsx"

        file_name, _ = QFileDialog.getSaveFileName(self, "Exporter", nom_fichier, "Excel Files (*.xlsx)")

        if not file_name:
            return

        try:
            export_sar_indicateurs(df_to_export, trimestre, annee, file_name, MODEL_SAR_PATH)
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

        dlg = GraphDialog(self.df_filtered, key=("ES-IND", "OA", "S.A.R"))
        dlg.exec_()
