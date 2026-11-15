from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QComboBox, QFileDialog, QRadioButton, QButtonGroup, QFrame
from PyQt5.QtCore import Qt, QThread, QTimer
from PyQt5.QtGui import QFont, QIcon
import datetime
from app.es_workers.load_worker import LoadWorker
from app.utils_excel import check_required_columns, extract_data_pigc_file_granular
from app.dialogs.indicateurs_oa_graph_dialog import (
    IndicateursOAGraphDialog,
    AnalyseSurveillanceDialog,
)
from app.views.common_view_mixins import CommonViewMixin, SharedIPMixin, SharedIPSMixin, SharedIPVMixin, SharedISMixin, SharedISVMixin
import logging

logger = logging.getLogger(__name__)


class IndicateursOAView(CommonViewMixin, SharedIPVMixin, SharedISVMixin, SharedIPSMixin, SharedISMixin, SharedIPMixin, QWidget):
    REQUIRED_COLS = [
        "Catégorie", "Programme", "Etat d'avancement", "Date de fin", "Date validation"
    ]


    def init_boutons_actions(self):
        # Ligne 2-3 (en fonction de la source): Boutons chargement, vérification, année, trimestre et calcul
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        # btn_layout.setAlignment(Qt.AlignTop)

        self.btn_load = QPushButton("Charger un fichier")
        self.btn_verify = QPushButton("Vérifier le contenu")

        self.combo_infrapole = QComboBox()
        self.combo_infrapole.addItem("Infrapôle")
        self.combo_infrapole.setEnabled(False)
        self.combo_infrapole.setFixedWidth(220)

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
        btn_layout.addWidget(self.combo_infrapole)
        btn_layout.addWidget(self.combo_annee)
        for btn in self.trimestre_radios:
            btn_layout.addWidget(btn)

        self.btn_analyse_surv = QPushButton("Situation")
        btn_layout.addWidget(self.btn_analyse_surv)

        self.btn_calculate = QPushButton("Indicateurs")
        btn_layout.addWidget(self.btn_calculate)
        btn_frame = QFrame()
        btn_frame.setLayout(btn_layout)
        return btn_frame

        # self.filters_scroll.setVisible(False)

    def harmoniser_combo(self):
        height = 32  # Adapte selon le rendu visuel, 32 est standard pour Qt
        font = self.combo_annee.font()
        font.setPointSize(11)

        for combo in [self.combo_sauvegarde, self.combo_infrapole, self.combo_annee]:
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

    def harmoniser_bouton(self):
        height = 32  # Adapte selon le rendu visuel, 32 est standard pour Qt
        font = self.combo_annee.font()
        font.setPointSize(11)

        for btn in [self.btn_verify, self.btn_calculate, self.btn_load, self.btn_new_save, self.btn_analyse_surv]:
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
        self.btn_analyse_surv.setEnabled(False)
        self.btn_calculate.setEnabled(False)

        self.btn_export.setEnabled(False)
        self.btn_graph.setEnabled(False)

    def init_ui(self):
        layout = QVBoxLayout()

        # Ligne 1: sources
        layout.addLayout(self.init_sources())

        # Ligne 2: gestion des sauvegardes
        self.init_sauvegardes()
        layout.addWidget(self.histo_frame)

        # Ligne 2/3: Boutons actions - chargement, vérification, année, trimestre, calcul
        layout.addWidget(self.init_boutons_actions(), alignment=Qt.AlignHCenter | Qt.AlignTop)

        # Harmonisation
        self.harmoniser_combo()
        self.harmoniser_bouton()
        self.harmoniser_link()

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
        # gestion des filtres à revoir...
        # self.table.horizontalScrollBar().valueChanged.connect(self.on_table_scroll)
        layout.addWidget(self.table)

        # Pagination
        layout.addLayout(self.init_pagination())

        # 7. Export/graphique
        layout.addLayout(self.init_boutons_post_actions())

        # 8. initialisation de la visibilité et des états
        self.init_visibilite()
        self.init_etat()

        self.setLayout(layout)

    # ********************************************** EVENEMENTS BOUTONS **********************************************
    def connect_signals(self):
        self.radio_flux.toggled.connect(lambda checked: self.show_mode("flux" if checked else "file"))
        self.radio_file.toggled.connect(lambda checked: self.show_mode("file" if checked else "flux"))
        self.radio_histo.toggled.connect(lambda checked: self.show_mode("histo" if checked else "file"))

        self.combo_sauvegarde.currentIndexChanged.connect(self.on_sauvegarde_selected)
        self.link_details.linkActivated.connect(self.show_details_sauvegarde_dialog)
        self.btn_new_save.clicked.connect(self.ouvrir_fenetre_sauvegarde)

        # self.btn_verify_save.clicked.connect(self.verify_file_histo)
        # self.btn_calculate_histo.clicked.connect(self.lancer_calcul_histo)

        self.btn_load.clicked.connect(self.load_file)
        self.btn_verify.clicked.connect(self.verify_file)
        # self.btn_verify_save.clicked.connect(self.verify_file)
        self.btn_analyse_surv.clicked.connect(self.afficher_analyse_surveillance)
        self.btn_calculate.clicked.connect(self.lancer_calcul)
        # self.btn_calculate_histo.clicked.connect(self.lancer_calcul)
        # Pagination
        self.btn_prev.clicked.connect(lambda: self.go_to_page(-1))
        self.btn_next.clicked.connect(lambda: self.go_to_page(+1))
        # Export et graphique (si présents)
        self.btn_export.clicked.connect(self.exporter)
        self.btn_graph.clicked.connect(self.afficher_graphique)

    def show_mode(self, mode):
        is_flux = (mode == "flux")
        is_file = (mode == "file")
        is_histo = (mode == "histo")

        self.btn_load.setVisible(is_file)
        self.btn_verify.setVisible(is_file or is_histo)
        self.combo_infrapole.setVisible(is_file or is_histo)
        self.combo_annee.setVisible(is_file or is_histo)
        for btn in self.trimestre_radios:
            btn.setVisible(is_file or is_histo)
        self.btn_analyse_surv.setVisible(is_file or is_histo)
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


    def _on_load_finished(self, df_data, idx_en_tete):
        self.progress.setVisible(False)
        self.btn_analyse_surv.setEnabled(True)
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
        self.fill_infrapoles()
        self.fill_annee()

    def _on_load_finished_histo(self, df_data, idx_en_tete):
        self.progress.setVisible(False)
        self.btn_analyse_surv.setEnabled(True)
        self.btn_calculate_histo.setEnabled(True)
        self.btn_verify_save.setEnabled(True)
        self.combo_infrapole_histo.setEnabled(True)
        self.combo_annee_histo.setEnabled(True)
        for btn in self.trimestre_radios_histo:
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
        # Utiliser fill_infrapoles/fill_annee sur les combos Histo
        self.fill_infrapoles(mode="histo")
        self.fill_annee(mode="histo")
        self.msg_label.setText("Sauvegarde chargée. Cliquez sur 'Vérifier le contenu' ou 'Calculer les indicateurs'.")
        self.msg_label.setVisible(True)

    # ********************************************** GESTION SAUVEGARDES **********************************************
    def charger_sauvegarde(self, fichier):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.msg_label.setVisible(False)
        self.table.setVisible(False)
        self.filters_scroll.setVisible(False)
        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)

        self.thread = QThread()
        self.worker = LoadWorker(fichier, extract_data_pigc_file_granular)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.finished.connect(self._on_load_finished_histo)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def fill_infrapoles(self):
        self.combo_infrapole.clear()

        if self.df_source is not None and "Infrapôle" in self.df_source.columns:
            infrapoles = self.df_source["Infrapôle"].dropna().astype(str).unique()
            infrapoles = sorted(set(map(str.strip, infrapoles)))
            self.combo_infrapole.addItem("Tous")
            for ip in infrapoles:
                self.combo_infrapole.addItem(ip)
            self.combo_infrapole.setEnabled(True)
        else:
            self.combo_infrapole.setEnabled(False)


    def _on_verify_finished(self, df_verified):
        if df_verified is None or df_verified.empty:
            self.progress.setVisible(False)
            QMessageBox.warning(self, "Erreur", "Erreur lors de la vérification.")
            return

        self.progress.setValue(85)
        self.btn_export.setVisible(False)
        self.btn_graph.setVisible(False)
        QTimer.singleShot(0, lambda: self._afficher_table_et_finaliser(df_verified))

    def on_table_scroll(self, value):
        # Décale les filtres horizontalement pour suivre le scroll de la table
        self.filters_frame.move(-value, self.filters_frame.y())

    # **********************************************  GESTION AFFICHAGE **********************************************
    def _afficher_table_et_finaliser(self, df_verified):
        self.afficher_table(df_verified)

        self.progress.setValue(100)
        self.progress.setVisible(False)
        self.msg_label.setText("Vérification visuelle : données source.")
        self.msg_label.setVisible(True)

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

        # Affiche les widgets
        self.table.setVisible(True)
        self.filters_scroll.setVisible(True)
        self.btn_prev.setVisible(True)
        self.btn_next.setVisible(True)
        self.label_page.setVisible(True)

        self.btn_export.setVisible(True)
        self.btn_export.setEnabled(True)
        self.btn_graph.setVisible(True)
        self.btn_graph.setEnabled(True)


        # self.filters_frame.setFixedWidth(self.table.viewport().width())


    def refresh_sauvegardes_prod(self):
        import os, json
        from datetime import datetime

        def parse_date(s):
            if not s:
                return datetime.min
            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
                try:
                    return datetime.strptime(str(s), fmt)
                except Exception:
                    logger.debug("Exception ignorée dans parse_date", exc_info=True)
                    continue
            return datetime.min

        dir_saves = os.path.join(os.getcwd(), "sauvegardes")
        metadata_path = os.path.join(dir_saves, "metadata.json")

        self.combo_sauvegarde.blockSignals(True)
        self.combo_sauvegarde.clear()
        self.combo_sauvegarde.addItem("Choisir une sauvegarde")
        model = self.combo_sauvegarde.model()
        index0 = model.index(0, 0)
        model.setData(index0, 0, Qt.UserRole - 1)

        self.sauvegardes_metadata = []

        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    self.sauvegardes_metadata = json.load(f)
            except Exception:
                self.sauvegardes_metadata = []

        # Regrouper par catégorie
        by_cat = {}
        for md in self.sauvegardes_metadata:
            cat = str(md.get("categorie", "(Sans catégorie)")).strip() or "(Sans catégorie)"
            by_cat.setdefault(cat, []).append(md)

        # Icône disque (utilise un icône système ou un PNG perso)
        disk_icon = QIcon.fromTheme("media-floppy")  # ou QIcon("ressources/icone_disque.png")

        # Tri et ajout
        for cat in sorted(by_cat.keys(), key=lambda x: x.lower()):
            # Entête
            header_text = f"— {cat} —"
            self.combo_sauvegarde.addItem(header_text)
            idx = self.combo_sauvegarde.count() - 1
            idx_model = model.index(idx, 0)
            model.setData(idx_model, 0, Qt.UserRole - 1)
            font = QFont(self.font())
            font.setBold(True)
            model.setData(idx_model, font, Qt.FontRole)

            # Sauvegardes triées par date décroissante
            items = sorted(by_cat[cat], key=lambda m: parse_date(m.get("date_valeur")), reverse=True)
            for md in items:
                nom = md.get("nom_sauvegarde", "Sans nom")
                date_valeur = md.get("date_valeur", "")
                text = f"   •  {nom}   ({date_valeur})"
                self.combo_sauvegarde.addItem(disk_icon, text)  # ⬅️ Icône disque ici
                row = self.combo_sauvegarde.count() - 1
                row_index = model.index(row, 0)
                model.setData(row_index, md, Qt.UserRole)

        # Style pro
        self.combo_sauvegarde.setStyleSheet("""
            QComboBox {
                border: 1px solid #aaa;
                border-radius: 6px;
                padding: 4px 12px 4px 8px;
                font-size: 13px;
                background: white;
                min-width: 320px;
            }
            QComboBox:focus {
                border: 1.5px solid #1F4E9C;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #1F4E9C;
                padding: 4px;
                outline: 0;
                selection-background-color: #E8EEF9;
                selection-color: #0B1F3F;
            }
            QComboBox QAbstractItemView::item {
                height: 28px;
                padding: 2px 8px;
            }
        """)

        self.combo_sauvegarde.blockSignals(False)


    # *******************************************  CALCUL des indicateurs ********************************************
    def lancer_calcul(self):
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_calculate.setEnabled(False)

        infrapole_choisi = self.combo_infrapole.currentText()
        df_filtered = self.df_source.copy()

        if infrapole_choisi != "Tous" and infrapole_choisi != "Infrapôle":
            mask = self.df_source["Infrapôle"].astype(str).str.strip() == infrapole_choisi
            df_filtered = self.df_source[mask].copy()
            # Réindexer pour éviter des effets de bord
            df_filtered = df_filtered.reindex(columns=self.df_source.columns)
        else:
            df_filtered = self.df_source

        annee = int(self.combo_annee.currentText())
        trimestre = self.get_selected_trimestre()

        # print(f"infrapôle = {infrapole_choisi}", flush=True)
        # print(f"trimestre = {trimestre}", flush=True)
        # print(f"trimestre utilisé = {int(trimestre[1])}", flush=True)

        from app.es_workers.ind_oa_worker import IndOACalcWorker

        self.thread_calc = QThread()
        self.worker_calc = IndOACalcWorker(df_filtered.copy(), annee, trimestre)
        self.worker_calc.moveToThread(self.thread_calc)
        self.thread_calc.started.connect(self.worker_calc.run)
        self.worker_calc.progress.connect(self.progress.setValue)
        self.worker_calc.finished.connect(self.on_calcul_finished)
        self.worker_calc.finished.connect(self.thread_calc.quit)
        self.worker_calc.finished.connect(self.worker_calc.deleteLater)
        self.thread_calc.finished.connect(self.thread_calc.deleteLater)
        self.thread_calc.start()

    def on_calcul_finished(self, df_out):
        # print(type(df_out))
        self.progress.setVisible(False)
        self.btn_calculate.setEnabled(True)
        if df_out is None or df_out.empty:
            QMessageBox.warning(self, "Erreur", "Aucun résultat de calcul.")
            return

        self.btn_export.setVisible(True)

        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        # print(f" colonne du DF résultat: {df_out.columns}", flush=True)
        if today_str in df_out.columns:
            self.btn_export.setEnabled(False)
        else:
            self.btn_export.setEnabled(True)

        self.df_indicateurs = df_out
        self.msg_label.setText("")
        self.afficher_table(df_out)


    # ************************************************** EXPORTATION **************************************************
    def exporter(self):
        import os
        from PyQt5.QtWidgets import QMessageBox
        from app.export.export_indicateurs_oa import export_oa_indicateurs
        from app.ressources import MODEL_INDICATEURS_OA_PATH

        # 1. Synchronisation des commentaires éventuels
        df_to_export = self.sync_commentaires_from_table(
            self.df_indicateurs if hasattr(self, 'df_indicateurs') else self.df_filtered)
        if df_to_export is None or df_to_export.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à exporter.")
            return

        # 2. Lecture des sélections
        trimestre = self.get_selected_trimestre()
        try:
            annee = int(self.combo_annee.currentText())
        except Exception:
            annee = datetime.datetime.now().year

        infrapole = self.combo_infrapole.currentText()
        today_str = datetime.datetime.now().strftime("%d-%m-%Y")

        # 3. Proposition d’enregistrement
        nom_fichier = f"Indicateurs_OA_{infrapole.replace(' ', '_')}_{trimestre}_{annee}_{today_str}.xlsx"
        file_name, _ = QFileDialog.getSaveFileName(self, "Exporter", nom_fichier, "Excel Files (*.xlsx)")
        if not file_name:
            return

        # 4. Export via modèle
        try:
            export_oa_indicateurs(df_to_export, trimestre, annee, infrapole, file_name, MODEL_INDICATEURS_OA_PATH)
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
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Erreur", "Aucune donnée à visualiser.")
            return

        dlg = IndicateursOAGraphDialog(self.df_filtered, programme=int(self.combo_annee.currentText()),
                                       parent=self)
        dlg.exec_()

    # Analyse de la Surveillance
    def afficher_analyse_surveillance(self):
        logger.debug("DEBUG: - afficher_analyse_surveillance - 1")
        from app.logic.logic_indicateurs_oa import (
            analyse_surveillance_statuts,
            maintenance_utm_hors_delai,
            maintenance_nb_par_categorie_urgence,
        )

        if self.df_source is None:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé.")
            return
        logger.debug("DEBUG: - afficher_analyse_surveillance - 2")
        # Filtre Infrapôle comme dans lancer_calcul()
        infrapole_choisi = self.combo_infrapole.currentText()
        if infrapole_choisi != "Tous" and infrapole_choisi != "Infrapôle":
            mask = self.df_source["Infrapôle"].astype(str).str.strip() == infrapole_choisi
            df_filtered = self.df_source[mask].copy()
            df_filtered = df_filtered.reindex(columns=self.df_source.columns)
        else:
            df_filtered = self.df_source

        # Année sélectionnée
        try:
            annee = int(self.combo_annee.currentText())
        except Exception:
            QMessageBox.warning(self, "Année manquante", "Veuillez sélectionner une année.")
            return

        # Calcul métier
        logger.debug("DEBUG: - afficher_analyse_surveillance - 3")
        data_surv = analyse_surveillance_statuts(
            df_filtered,
            annee=annee,
            categories=("VI", "VD", "IDE", "IDR")  # ordre d’affichage demandé
        )
        logger.debug("DEBUG: - afficher_analyse_surveillance - 4")
        u0_utm_df = maintenance_utm_hors_delai(df_filtered, annee, "U0s")
        logger.debug("DEBUG: - afficher_analyse_surveillance - 4.1")
        u1_utm_df = maintenance_utm_hors_delai(df_filtered, annee, "U1s")
        logger.debug("DEBUG: - afficher_analyse_surveillance - 4.2")
        cat_urg_df = maintenance_nb_par_categorie_urgence(df_filtered, annee)
        logger.debug("DEBUG: - afficher_analyse_surveillance - 5")

        if not data_surv or all(len(v) == 0 for v in data_surv.values()):
            QMessageBox.information(self, "Analyse", "Aucune donnée exploitable pour l’analyse.")
            return

        # Affichage 2x2 camemberts
        # option: Affichage bloquant
        # dlg = AnalyseSurveillanceDialog(data_surv, programme=annee, parent=self)
        # dlg.exec_()

        # option: Affichage NON bloquant
        logger.debug("DEBUG: - afficher_analyse_surveillance - 6")
        self._analyse_win = AnalyseSurveillanceDialog(
            data_surv, programme=annee,
            u0_utm_df=u0_utm_df, u1_utm_df=u1_utm_df, cat_urg_df=cat_urg_df,
            parent=self)
        self._analyse_win.setModal(False)  # facultatif, show() suffit à être non bloquant
        self._analyse_win.show()  # -> n’empêche plus d’utiliser l’appli


