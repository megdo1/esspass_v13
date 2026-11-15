"""Chargement des fichiers, vérification et calcul des indicateurs avec barre de progression."""

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QRadioButton, QButtonGroup, QTableWidget, QProgressBar, QMessageBox, QHeaderView, QScrollArea, QComboBox
from PyQt5.QtCore import Qt
import pandas as pd
import datetime
from app.logic.logic_visite import calcul_indicateurs_visite
from app.utils_excel import extract_data_after_second_empty_row, check_required_columns
from app.thread_progress import ProgressThread

import logging
logger = logging.getLogger(__name__)



class TraitementMixin:
    """Chargement des fichiers, vérification et calcul des indicateurs avec barre de progression."""

    def build_zone3_widget_for_view(self, key):
        # Vérification Outlook pour les vues nécessitant l'authentification
        if key in [
            ('PASS', 'LD Assistance PIGC', '📋 Demandes'),
            ('PASS', 'LD Assistance PIGC', '👥 Utilisateurs'),
            ('PASS', 'LD Assistance PIGC', '⚙️ Configuration')
        ]:                
            from app.data.data_manager import get_windows_user_info
            user_info = get_windows_user_info()

            if user_info.get('error') :
                QMessageBox.critical(
                    self,
                    "Outlook non disponible",
                    "⚠️ Microsoft Outlook n'est pas lancé ou n'est pas correctement configuré.\n\n"
                    "Veuillez lancer Outlook avant d'accéder à cette fonctionnalité.\n\n"
                    "L'application va maintenant se fermer."
                )
                QApplication.instance().quit()
                return QWidget()  # Retourner un widget vide
        ##################################################### OT #######################################################
        if key == ("ES-IND", "OT", "Préconisations"):
            from app.views.preconisations_view import PreconisationsView
            return PreconisationsView()

        if key == ("ES-IND", "OT", "Visites cycliques"):
            from app.views.visites_cycliques_view import VisitesCycliquesView
            return VisitesCycliquesView()
        ##################################################### OA #######################################################

        ##################################################### PASS #####################################################
        if key == ("PASS", "LD Assistance PIGC", "📋 Demandes"):
            from app.views.pass_view_v3 import PassViewClean
            return PassViewClean()

        if key == ("PASS", "LD Assistance PIGC", "👥 Utilisateurs"):
            from app.views.pass_users_view import GestionUtilisateursDialog
            return GestionUtilisateursDialog()
        if key == ("PASS", "LD Assistance PIGC", "⚙️ Configuration"):
            from app.views.pass_parametrage_view import ParametrageDialog
            return ParametrageDialog()   
        
        ################################################## à nettoyer ##################################################
        widget = QWidget()
        layout = QVBoxLayout()
        # Ligne source
        source_layout = QHBoxLayout()
        source_layout.addStretch()
        source_label = QLabel("Source des données")
        radio_flux = QRadioButton("PIGC (flux)")
        radio_file = QRadioButton("Fichier (chargement)")
        source_group = QButtonGroup(widget)
        source_group.addButton(radio_flux)
        source_group.addButton(radio_file)
        source_layout.addWidget(source_label)
        source_layout.addWidget(radio_flux)
        source_layout.addWidget(radio_file)
        source_layout.addStretch()
        layout.addLayout(source_layout)

        # Boutons dynamiques (haut)
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout()
        buttons_layout.setAlignment(Qt.AlignCenter)
        btn_load = QPushButton("Charger un fichier")
        btn_verify = QPushButton("Vérifier le contenu")
        btn_calculate = QPushButton("Calcul des indicateurs")

        # --- Ajout ComboBox Année ---
        combo_annee = QComboBox()
        combo_annee.setEnabled(False)
        combo_annee.setFixedWidth(100)
        combo_annee.setToolTip("Année (extraites de la colonne Date du fichier chargé)")
        combo_annee.addItem("Année")  # Placeholder initial

        # Insérer après btn_calculate et avant le premier bouton radio
        # buttons_layout.insertWidget(buttons_layout.indexOf(btn_calculate) + 1, combo_annee)
        # Trouver l'index du bouton 'Calcul des indicateurs' et l'insérer juste après
        idx_calculate = buttons_layout.indexOf(btn_calculate)
        buttons_layout.insertWidget(idx_calculate + 1, combo_annee)

        btn_calculate.setEnabled(False)
        buttons_layout.addWidget(btn_load)
        buttons_layout.addWidget(btn_verify)
        buttons_layout.addWidget(btn_calculate)
        trimestre_group = QButtonGroup(buttons_widget)
        trimestre_labels = ["Aujourd'hui"] + [f"T{i}" for i in range(1, 6)]
        trimestre_radios = [QRadioButton(label) for label in trimestre_labels]
        for btn in trimestre_radios:
            trimestre_group.addButton(btn)
            buttons_layout.addWidget(btn)
        buttons_widget.setLayout(buttons_layout)

        # FILTRES dans un QScrollArea horizontal
        filters_container = QScrollArea()
        filters_container.setWidgetResizable(True)
        filters_container.setFixedHeight(40)
        filters_inner = QWidget()
        filters_layout = QHBoxLayout()
        filters_layout.setContentsMargins(5, 5, 5, 5)
        filters_layout.setSpacing(2)
        filters_inner.setLayout(filters_layout)
        filters_container.setWidget(filters_inner)
        filters_container.setVisible(False)

        # Progression, table, message
        progress_bar = QProgressBar()
        progress_bar.setVisible(False)
        table = QTableWidget()
        table.setVisible(False)
        table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        msg_label = QLabel("Travaux en cours...")
        msg_label.setAlignment(Qt.AlignCenter)
        msg_label.setVisible(False)

        # --- Pagination PATCH début ---
        widget.df_filtered = None
        widget.page_index = 0
        widget.btn_prev = QPushButton("Précédent")
        widget.btn_next = QPushButton("Suivant")
        widget.label_page = QLabel("Page 1 / 1")
        pagination_layout = QHBoxLayout()
        pagination_layout.addStretch()
        pagination_layout.addWidget(widget.btn_prev)
        pagination_layout.addWidget(widget.label_page)
        pagination_layout.addWidget(widget.btn_next)
        pagination_layout.addStretch()

        widget.btn_prev.setVisible(False)
        widget.btn_next.setVisible(False)
        widget.label_page.setVisible(False)

        # Connecte les boutons pagination :
        widget.btn_prev.clicked.connect(lambda: self.go_to_page(widget, -1))
        widget.btn_next.clicked.connect(lambda: self.go_to_page(widget, +1))
        # --- Pagination PATCH fin ---

        # Boutons en bas à droite
        bottom_btn_widget = QWidget()
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.setAlignment(Qt.AlignRight)
        bottom_btn_widget.setLayout(bottom_btn_layout)
        btn_graph = QPushButton("Graphique")
        btn_graph.setVisible(False)
        btn_export = QPushButton("Exporter le résultat")
        btn_export.setVisible(False)
        bottom_btn_layout.addWidget(btn_graph)
        bottom_btn_layout.addWidget(btn_export)

        layout.addWidget(buttons_widget, alignment=Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(filters_container)
        layout.addWidget(progress_bar)
        layout.addWidget(table)
        layout.addLayout(pagination_layout)
        layout.addWidget(msg_label)
        layout.addWidget(bottom_btn_widget)
        widget.setLayout(layout)
        # Références utiles
        widget.btn_load = btn_load
        widget.btn_verify = btn_verify
        widget.btn_calculate = btn_calculate

        widget.combo_annee = combo_annee

        widget.btn_graph = btn_graph
        widget.btn_export = btn_export
        widget.bottom_btn_widget = bottom_btn_widget
        widget.trimestre_radios = trimestre_radios
        widget.progress_bar = progress_bar
        widget.table = table
        widget.radio_file = radio_file
        widget.radio_flux = radio_flux
        widget.msg_label = msg_label
        widget.buttons_widget = buttons_widget
        widget.filters_container = filters_container
        widget.filters_inner = filters_inner
        widget.filters_layout = filters_layout
        widget.filters_editors = []
        widget.df_current = None  # DataFrame affiché (pour filtre)
        # Affichage initial : SEULE la ligne source visible
        buttons_widget.setVisible(False)
        msg_label.setVisible(False)
        table.setVisible(False)
        btn_export.setVisible(False)
        btn_graph.setVisible(False)
        filters_container.setVisible(False)
        bottom_btn_widget.setVisible(True)
        # Connexions
        radio_file.toggled.connect(lambda checked: self.handle_source_choice(widget, checked, mode="file"))
        radio_flux.toggled.connect(lambda checked: self.handle_source_choice(widget, checked, mode="flux"))
        btn_load.clicked.connect(lambda: self.load_file_with_real_progress(key, widget))
        btn_verify.clicked.connect(lambda: self.verify_content_with_real_progress(key, widget))
        btn_calculate.clicked.connect(lambda: self.calculate_indicators_with_real_progress(key, widget))
        btn_graph.clicked.connect(lambda: self.show_graph_dialog(key, widget))
        btn_export.clicked.connect(lambda: self.export_result_for_view(key))
        return widget

    def handle_source_choice(self, widget, checked, mode):
        if mode == "file" and checked:
            widget.buttons_widget.setVisible(True)
            for btn in widget.trimestre_radios:
                btn.setVisible(True)
            widget.msg_label.setVisible(False)
            widget.table.setVisible(False)
            widget.btn_export.setVisible(False)
            widget.btn_graph.setVisible(False)
            widget.bottom_btn_widget.setVisible(True)
            widget.filters_container.setVisible(False)
        elif mode == "flux" and checked:
            widget.buttons_widget.setVisible(False)
            widget.msg_label.setVisible(True)
            widget.table.setVisible(False)
            widget.btn_export.setVisible(False)
            widget.btn_graph.setVisible(False)
            widget.bottom_btn_widget.setVisible(False)
            widget.filters_container.setVisible(False)

    def load_file_with_real_progress(self, key, widget):
        file_name, _ = QFileDialog.getOpenFileName(self, "Charger un fichier Excel", "",
                                                   "Excel Files (*.xlsx *.xls)")
        if not file_name:
            return

        widget.btn_prev.setVisible(False)
        widget.btn_next.setVisible(False)
        widget.label_page.setVisible(False)

        widget.progress_bar.setVisible(True)
        widget.progress_bar.setValue(0)
        widget.table.setVisible(False)
        widget.btn_export.setVisible(False)
        widget.btn_graph.setVisible(False)
        widget.bottom_btn_widget.setVisible(True)
        widget.msg_label.setVisible(False)
        widget.btn_load.setEnabled(False)
        widget.filters_container.setVisible(False)
        # Désactivation préventive du bouton calcul tant que le fichier n'est pas validé
        widget.btn_calculate.setEnabled(False)

        self.file_loader = ProgressThread(total_steps=8, sleep_time=80)
        self.file_loader.progress.connect(widget.progress_bar.setValue)

        def on_finish():
            try:
                # Détermination des colonnes attendues selon la vue
                view_type = key[2]
                if view_type == "Préconisations":
                    required_cols = self.REQUIRED_COLS_PRECONISATIONS
                elif view_type == "Visites cycliques":
                    required_cols = self.REQUIRED_COLS_VISITES
                else:
                    required_cols = []
                # Extraction zone utile
                df, header_idx = extract_data_after_second_empty_row(file_name)
                if df is None:
                    QMessageBox.critical(
                        self, "Erreur",
                        "Le fichier chargé ne respecte pas le format d'export Excel PIGC\n"
                        "Astuce : Vérifier que la recherche PIGC utilisée dispose d'au moins un critère de recherche (domaine, catégorie...)"
                    )
                    widget.progress_bar.setVisible(False)
                    widget.btn_load.setEnabled(True)
                    widget.btn_calculate.setEnabled(False)
                    return

                missing_cols = check_required_columns(df, required_cols)
                if missing_cols:
                    QMessageBox.critical(self, "Colonnes absentes",
                                         f"Colonnes manquantes : {', '.join(missing_cols)}")
                    widget.progress_bar.setVisible(False)
                    widget.btn_load.setEnabled(True)
                    widget.btn_calculate.setEnabled(False)
                    return
                else:
                    widget.btn_calculate.setEnabled(True)

                self.file_data_by_view[key] = df

                if key == ("ES-IND", "OT", "Visites cycliques"):
                    combo = widget.combo_annee
                    combo.clear()
                    if "Date" in df.columns:
                        # Convertir la colonne Date en datetime, puis extraire les années uniques
                        try:
                            dates = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
                            annees_uniques = sorted(dates.dropna().dt.year.unique(), reverse=True)
                            if annees_uniques:
                                combo.setEnabled(True)
                                for an in annees_uniques:
                                    combo.addItem(str(an))
                            else:
                                combo.setEnabled(False)
                                QMessageBox.warning(self, "Date",
                                                    "Aucune année détectée dans la colonne Date du fichier chargé.")
                                combo.addItem("Année")
                        except Exception as e:
                            combo.setEnabled(False)
                            combo.addItem("Année")
                            QMessageBox.warning(self, "Date", f"Erreur lors de la lecture des années : {e}")
                    else:
                        combo.setEnabled(False)
                        combo.addItem("Année")
                        QMessageBox.warning(self, "Date",
                                            "La colonne Date est absente du fichier chargé.\nLe champ Année est "
                                            "indisponible pour le traitement des reliquats")

                self.menu_history[key] = {"mode": "file", "df": df}
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur lors de la lecture du fichier : {e}")
                widget.progress_bar.setVisible(False)
                widget.btn_load.setEnabled(True)
                widget.btn_calculate.setEnabled(False)
                return
            widget.progress_bar.setVisible(False)
            widget.btn_load.setEnabled(True)

        self.file_loader.finished.connect(on_finish)
        self.file_loader.start()

    def verify_content_with_real_progress(self, key, widget):
        if key in self.file_data_by_view:
            df = self.file_data_by_view[key]
            widget.progress_bar.setVisible(True)
            widget.progress_bar.setValue(0)
            widget.table.setVisible(False)
            widget.btn_export.setVisible(False)
            widget.btn_graph.setVisible(False)
            widget.bottom_btn_widget.setVisible(True)
            widget.msg_label.setVisible(False)
            widget.filters_container.setVisible(False)

            # --------- PATCH: pré-traite le DataFrame AVANT le thread ! ---------
            try:
                df_display = df.astype(str).fillna("").reset_index(drop=True)
            except Exception as e:
                logger.error("Erreur lors du cast DataFrame : %s", e)
                QMessageBox.critical(self, "Erreur DataFrame", str(e))
                widget.progress_bar.setVisible(False)
                return
            # --------------------------------------------------------------------

            self.verif_loader = ProgressThread(total_steps=7, sleep_time=40)
            self.verif_loader.progress.connect(widget.progress_bar.setValue)

            def on_finish():
                if not hasattr(widget, "filters_layout") or not hasattr(widget, "filters_editors"):
                    logger.error("Erreur : widget de la mauvaise vue ou mal initialisé !")
                    return
                self.display_table_for_view(df, widget.table, widget)
                widget.progress_bar.setVisible(False)

            self.verif_loader.finished.connect(on_finish)
            self.verif_loader.start()
        else:
            QMessageBox.warning(self, "Erreur", "Aucun fichier chargé pour cette vue.")

    def calculate_indicators_with_real_progress(self, key, widget):
        if not any(btn.isChecked() for btn in widget.trimestre_radios):
            QMessageBox.warning(self, "Trimestre",
                                "Merci de choisir la date de valeur: un trimestre ou aujourd'hui")
            return

        df = self.file_data_by_view.get(key)

        if key == ("ES-IND", "OT", "Visites cycliques"):
            """
            year = datetime.datetime.now().year

            # éliminer les lignes avec "Année de programmation"
            if "Année de programmation" in df.columns:
                prog_col = pd.to_numeric(df["Année de programmation"], errors="coerce")
                df = df[prog_col.fillna(0).astype(int) >= year]
            else:
                QMessageBox.warning(self, "Avertissement",
                                    'Attention la colonne "Année de programmation" est absente du fichier chargé.\n'
                                    'le traitement des reliquats A-1, A-2 n\'est pas possible.')
            
            # *** NOUVEAU FILTRE : éliminer les "Annulée" ***
            if "Etat d'avancement" in df.columns:
                df = df[df["Etat d'avancement"] != "Annulée"]
            else:
                QMessageBox.warning(self, "Avertissement",
                                    'Attention la colonne "Etat d\'avancement" est absente du fichier chargé.\n'
                                    'les actions annulées, si présentes, seront considérées dans le calcul')

            """

        if df is None or "Infrapôle" not in df:
            QMessageBox.warning(self, "Erreur", "Données manquantes ou mal formatées")
            return

        widget.progress_bar.setVisible(True)
        widget.progress_bar.setValue(0)
        widget.table.setVisible(False)
        widget.btn_export.setVisible(False)
        widget.btn_graph.setVisible(False)
        widget.bottom_btn_widget.setVisible(True)
        widget.msg_label.setVisible(False)
        widget.filters_container.setVisible(False)

        self.calc_loader = ProgressThread(total_steps=12, sleep_time=30)
        self.calc_loader.progress.connect(widget.progress_bar.setValue)

        def on_finish():
            # Bloc Visites cycliques

            if key == ("ES-IND", "OT", "Visites cycliques"):
                trimestre_labels = ["Aujourd'hui", "T1", "T2", "T3", "T4", "T5"]
                trimestre_index = next((i for i, btn in enumerate(widget.trimestre_radios) if btn.isChecked()), 0)
                selected_trimestre = trimestre_labels[trimestre_index]
                # year = datetime.datetime.now().year

                # Année depuis la combo (si activée), sinon année courante
                try:
                    if widget.combo_annee.isEnabled():
                        year = int(widget.combo_annee.currentText())
                    else:
                        year = datetime.datetime.now().year
                except Exception:
                    year = datetime.datetime.now().year

                # CALCUL
                try:
                    indicator_df = calcul_indicateurs_visite(df, selected_trimestre, year)
                except ValueError as e:
                    QMessageBox.critical(self, "Erreur", f"Erreur dans le calcul des indicateurs :\n{e}")
                    widget.progress_bar.setVisible(False)
                    return

                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Erreur inattendue :\n{e}")
                    widget.progress_bar.setVisible(False)
                    return

                if indicator_df is None or indicator_df.empty:
                    QMessageBox.warning(self, "Erreur", "Aucun indicateur généré, tableau vide.")
                    widget.progress_bar.setVisible(False)
                    return

                self.indicators_by_view[key] = indicator_df
                # Patch sécurité DataFrame pour affichage sans crash
                for col in indicator_df.columns:
                    indicator_df[col] = indicator_df[col].fillna("").astype(str)
                indicator_df = indicator_df.reset_index(drop=True)
                indicator_df = indicator_df.astype(str).fillna("")
                indicator_df = indicator_df.reset_index(drop=True)
                self.display_table_for_view(indicator_df, widget.table, widget, editable_col="Commentaires")
                widget.progress_bar.setVisible(False)
                widget.btn_export.setVisible(True)
                widget.btn_graph.setVisible(True)
                widget.bottom_btn_widget.setVisible(True)
                return

            if key == ("ES-IND", "OT", "Préconisations"):
                # Recherche colonne ZP
                col_zp = None
                for col in df.columns:
                    if col.lower().strip().replace('\n', ' ').replace('\r', ' ') in ["désignation zp ouvrage"]:
                        col_zp = col
                        break
                if not col_zp:
                    QMessageBox.warning(self, "Avertissement",
                                        'Attention la colonne "Désignation ZP Ouvrage" est absente du fichier chargé.')

                grouped = df.groupby("Infrapôle")
                result = []
                trimestre_labels = ["Aujourd'hui", "T1", "T2", "T3", "T4", "T5"]
                trimestre_index = next((i for i, btn in enumerate(widget.trimestre_radios) if btn.isChecked()), 0)
                selected_trimestre = trimestre_labels[trimestre_index]
                for infrapole, data in grouped:
                    # Ajout ZP
                    if col_zp and not data[col_zp].isnull().all():
                        zp_val = data[col_zp].mode().iat[0] if not data[col_zp].mode().empty else ""
                    else:
                        zp_val = ""
                    # Bloc déjà existant...
                    if key == ("ES-IND", "OT", "Préconisations") and selected_trimestre != "Aujourd'hui":
                        year = datetime.datetime.now().year
                        t_map = {"T1": (3, 31), "T2": (6, 30), "T3": (9, 30), "T4": (12, 31), "T5": (3, 31)}
                        mois, jour = t_map[selected_trimestre]

                        if selected_trimestre == "T5":
                            date_limite = datetime.datetime(year + 1, mois, jour)
                        else:
                            date_limite = datetime.datetime(year, mois, jour)

                        data = data.copy()
                        data["Echéance_dt"] = pd.to_datetime(data["Echéance"], errors='coerce', dayfirst=True)
                        condition_echeance = data["Echéance_dt"].le(date_limite)
                    else:
                        condition_echeance = (data["Statut échéance"] == "En retard")
                    u0_total = len(data[data["Urgence"] == "U0"])
                    u0_echues = len(data[(data["Urgence"] == "U0") & condition_echeance])
                    u0_risque = len(data[(data["Urgence"] == "U0") & (
                        data["Statut"].isin(["Demande ADR", "En attente ADR", "En attente de validation"])) &
                                         condition_echeance])
                    u1_total = len(data[(data["Urgence"] == "U1") & (data["Enjeu sécurité"] == "Oui")])
                    u1_echues = len(
                        data[(data["Urgence"] == "U1") & condition_echeance & (data["Enjeu sécurité"] == "Oui")])
                    u1_risque = len(data[(data["Urgence"] == "U1") & (data["Enjeu sécurité"] == "Oui") & (
                        data["Statut"].isin(["Demande ADR", "En attente ADR", "En attente de validation"])) &
                                         condition_echeance])

                    result.append([
                        infrapole,
                        zp_val,
                        u0_total,
                        u0_echues,
                        u0_risque,
                        u1_total,
                        u1_echues,
                        u1_risque
                    ])
                indicator_df = pd.DataFrame(result, columns=[
                    "Infrapôle", "ZP",
                    "U0 Nombre total de préconisations", "U0 Préconisations échues",
                    "U0 Analyse de risque - demandées ou en cours",
                    "U1 Nombre total de préconisations", "U1 Préconisations échues",
                    "U1 Analyse de risque - demandées ou en cours"
                ])
                self.indicators_by_view[key] = indicator_df
                indicator_df = indicator_df.astype(str).fillna("")
                indicator_df = indicator_df.reset_index(drop=True)
                self.display_table_for_view(indicator_df, widget.table, widget)
                widget.progress_bar.setVisible(False)
                widget.btn_export.setVisible(True)
                widget.btn_graph.setVisible(True)
                widget.bottom_btn_widget.setVisible(True)
                return

        self.calc_loader.finished.connect(on_finish)
        self.calc_loader.start()
