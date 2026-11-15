import os

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QMessageBox, QComboBox, QFileDialog, QRadioButton, QButtonGroup, QFrame
import datetime
import pandas as pd
from app.logic.logic_preco import calcul_indicateurs_preco
from app.export.export_preco import export_preconisations
from app.dialogs.ui_graphdialog import GraphDialog
from app.ressources import MODEL_PRECO_PATH
from app.views.common_view_mixins import CommonViewMixin, SharedIPMixin, SharedIPSMixin, SharedIPVMixin, SharedPSMixin, SharedPSVMixin, SharedPVMixin

import logging
logger = logging.getLogger(__name__)


class PreconisationsView(CommonViewMixin, SharedIPVMixin, SharedPSVMixin, SharedIPSMixin, SharedPVMixin, SharedPSMixin, SharedIPMixin, QWidget):
    """
    REQUIRED_COLS_PRECONISATIONS = [
        "Infrapôle", "Urgence", "Statut", "Statut échéance", "Echéance", "Enjeu sécurité"
    ]
    """

    REQUIRED_COLS = [
        "Infrapôle", "Urgence", "Statut", "Statut échéance", "Echéance", "Enjeu sécurité"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.df_source = None
        self.df_indicateurs = None
        self.df_affichee = None
        self.LINES_PER_PAGE = 1000
        # print("DEBUG(Préconisations): __init__ - 1", flush=True)
        self.init_ui()
        # print("DEBUG(Préconisations): __init__ - 2", flush=True)
        self.connect_signals()
        # print("DEBUG(Préconisations): __init__ - 3", flush=True)
        self.show_mode("histo")
        # print("DEBUG(Préconisations): __init__ - 4", flush=True)


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

        trimestre_labels = ["Aujourd'hui"] + [f"T{i}" for i in range(1, 5)]
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


    # ************************************************* A SUPPRIMER... ************************************************


    # ***************************************** CONFIG: INTERFACE, BOUTONS... *****************************************
    def config_ui_post_verification(self):
        self.progress.setVisible(False)
        # self.msg_label.setText("Vérification visuelle : données source.")
        self.msg_label.setText("Vérification visuelle : données source.")
        self.msg_label.setVisible(True)

        # Affiche les widgets
        self.filters_scroll.setVisible(True)
        self.table.setVisible(True)

        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)


    # ********************************************** EVENEMENTS BOUTONS **********************************************
    def update_radio_aujourdhui_state(self):
        # Trouver le bouton radio "Aujourd'hui"
        radio_aujourdhui = self.trimestre_radios[0]  # Le premier est "Aujourd'hui"
        try:
            annee_select = int(self.combo_annee.currentText())
        except Exception:
            annee_select = None
        annee_courante = datetime.datetime.now().year
        if annee_select is not None and annee_select < annee_courante:
            radio_aujourdhui.setEnabled(False)
            # Optionnel: si actuellement sélectionné, switch sur T1
            if radio_aujourdhui.isChecked():
                self.trimestre_radios[1].setChecked(True)
        else:
            radio_aujourdhui.setEnabled(True)

            # --- Ajout pour gestion des boutons export/graphique ---
            self.update_export_graph_buttons()

    def update_export_graph_buttons(self):
        trimestre = self.get_selected_trimestre()
        try:
            annee = int(self.combo_annee.currentText())
        except Exception:
            annee = datetime.datetime.now().year

        # --- Logique de détection "trimestre dans le passé"
        from app.logic.logic_preco import date_fin_trimestre, dernier_trimestre_termine
        if trimestre != "Aujourd'hui" and trimestre.startswith("T"):
            date_fin_selected = date_fin_trimestre(annee, trimestre)
            annee_termine, trimestre_termine = dernier_trimestre_termine()
            date_fin_trimestre_termine = date_fin_trimestre(annee_termine, trimestre_termine)
            trimestre_dans_le_passe = date_fin_selected < date_fin_trimestre_termine
        else:
            trimestre_dans_le_passe = False

        self.btn_export.setEnabled(not trimestre_dans_le_passe)
        self.btn_graph.setEnabled(not trimestre_dans_le_passe)

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
        self.combo_annee.currentIndexChanged.connect(self.update_radio_aujourdhui_state)
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
        colonne_ref_annee = "Date de la première préconisation"

        if colonne_ref_annee in df.columns:
            # Convertir la colonne REF en datetime, puis extraire les années uniques
            try:
                dates = pd.to_datetime(df[colonne_ref_annee], errors="coerce", dayfirst=True)
                annees_uniques = sorted(dates.dropna().dt.year.unique(), reverse=True)

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

                    self.update_radio_aujourdhui_state()

                else:
                    self.combo_annee.setEnabled(False)
                    QMessageBox.warning(self, "Date",
                                        f"Aucune année détectée dans la colonne {colonne_ref_annee} du fichier chargé.")
                    self.combo_annee.addItem("Année")
            except Exception as e:
                self.combo_annee.setEnabled(False)
                self.combo_annee.addItem("Année")
                QMessageBox.warning(self, "Date", f"Erreur lors de la lecture des années : {e}")
        else:
            self.combo_annee.setEnabled(False)
            self.combo_annee.addItem("Année")
            QMessageBox.warning(self, "Date",
                                f"La colonne {colonne_ref_annee} est absente du fichier chargé.\nLe champ Année est "
                                "indisponible pour le traitement de l'historique")

    # ************************************************  UTILITAIRES **************************************************
    def get_selected_trimestre(self):
        for i, btn in enumerate(self.trimestre_radios):
            if btn.isChecked():
                # return ["Aujourd'hui", "T1", "T2", "T3", "T4", "T5"][i]
                return ["Aujourd'hui", "T1", "T2", "T3", "T4"][i]
        return "Aujourd'hui"

    # ******************************************  VERIFICATION DU CONTENU ********************************************
    def verify_file(self):
        if self.df_source is not None:
            self.progress.setVisible(True)
            self.progress.setValue(5)

            self.btn_prev.setVisible(False)
            self.btn_next.setVisible(False)
            self.label_page.setVisible(False)

            self.afficher_table(self.df_source)

            self.progress.setValue(100)
            self.config_ui_post_verification()
            # self.progress.setVisible(False)
            # self.msg_label.setText("Vérification visuelle : données source.")
            # self.msg_label.setVisible(True)
        else:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")


    # *******************************************  CALCUL des indicateurs ********************************************
    def calculer(self):
        trimestre = self.get_selected_trimestre()
        annee = int(self.combo_annee.currentText())

        if self.df_source is None:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")
            return
        try:
            indic = calcul_indicateurs_preco(self.df_source, trimestre, annee)
            self.df_indicateurs = indic.astype(str).fillna("").reset_index(drop=True)
            self.afficher_table(self.df_indicateurs)
            self.config_ui_post_calcul()
            self.update_radio_aujourdhui_state()

        except Exception as e:
            QMessageBox.critical(self, "Erreur calcul", str(e))


        # self.filters_frame.setFixedWidth(self.table.viewport().width())


    # ************************************************** EXPORTATION **************************************************
    def exporter(self):
        if self.df_indicateurs is None:
            QMessageBox.warning(self, "Erreur", "Aucun indicateur à exporter.")
            return
        today_dt = datetime.datetime.now()
        trimestre = self.get_selected_trimestre()
        annee = self.combo_annee.currentText()
        today_str = today_dt.strftime("%d-%m-%Y")

        if trimestre == "Aujourd'hui":
            nom_fichier = f"Preconisations_indicateur-OT_{today_str}.xlsx"
        else:
            nom_fichier = f"Preconisations_indicateur-OT_{trimestre}_{annee}.xlsx"
        file_name, _ = QFileDialog.getSaveFileName(self, "Exporter", nom_fichier, "Excel Files (*.xlsx)")
        if not file_name:
            return
        try:
            export_preconisations(self.df_indicateurs, trimestre, int(annee), file_name, MODEL_PRECO_PATH)
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
        if self.df_indicateurs is None:
            QMessageBox.warning(self, "Erreur", "Aucun indicateur à visualiser.")
            return
        dlg = GraphDialog(self.df_indicateurs, key=("ES-IND", "OT", "Préconisations"))
        dlg.exec_()
