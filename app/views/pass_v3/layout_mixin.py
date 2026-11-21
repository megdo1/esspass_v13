"""Construction de l'interface : zones, tableau de bord, libellés d'information."""

from PyQt5.QtWidgets import QWidget, QFrame
from PyQt5.QtWidgets import QTableWidget, QCheckBox, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt
from app.utils.affichage import avertissement_limite


class LayoutMixin:
    """Construction de l'interface : zones, tableau de bord, libellés d'information."""

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(12, 10, 12, 10)

        # Blocs d'information compacts en haut, la liste des demandes occupe tout le reste
        self.create_zone_informations(main_layout)
        self.create_zone_dashboard(main_layout)
        self.create_zone_actions(main_layout)
        self.create_zone_demandes(main_layout)

    def setup_corner_label(self):
        """Crée un label 'ID' dans le coin supérieur gauche du tableau"""
        self.corner_widget = QLabel("ID", self.table)
        self.corner_widget.setAlignment(Qt.AlignCenter)
        self.corner_widget.setStyleSheet("""
            QLabel {
                background-color: #F1F5F9;
                color: #334155;
                font-weight: bold;
                border: none;
                border-bottom: 1px solid #CBD5E1;
                border-right: 1px solid #E2E8F0;
                padding: 5px;
            }
        """)
        self.update_corner_position()

    def update_corner_position(self):
        """Met à jour la position du label corner"""
        if hasattr(self, 'corner_widget'):
            width = self.table.verticalHeader().width()
            height = self.table.horizontalHeader().height()
            self.corner_widget.setGeometry(0, 0, width, height)
            self.corner_widget.raise_()  # Mettre au premier plan

    def create_zone_informations(self, parent_layout):
        """Bloc unique : utilisateur connecté et dernière collecte, sur deux lignes compactes."""
        card = QFrame()
        card.setObjectName("InfoCard")
        card.setStyleSheet("QFrame#InfoCard { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(5)

        def ligne(titre, labels):
            row = QHBoxLayout()
            row.setSpacing(8)
            caption = QLabel(titre)
            caption.setFixedWidth(120)
            caption.setStyleSheet("font-size: 12px; font-weight: bold; color: #0F2A52; background: transparent;")
            row.addWidget(caption)
            for label in labels:
                label.setStyleSheet("font-size: 12px; padding: 3px 10px; color: #475569; "
                                    "background: #F1F5F9; border-radius: 6px;")
                row.addWidget(label)
            row.addStretch()
            layout.addLayout(row)

        # Libellés conservés dans l'ordre : update_display_info les met à jour par référence
        self.info_user_labels = [
            QLabel(f"👨‍💼 Utilisateur : {self.user_info['prenom']} {self.user_info['nom']}"),
            QLabel(f"🔑 Rôle : {self.user_info['role']}"),
            QLabel(f"📅 Connecté le : {self.user_info['date_connexion']}"),
        ]
        self.info_collecte_labels = [
            QLabel(f"🕐 Dernière collecte : {self.collecte_info['date_collecte']}"),
            QLabel(f"👤 Lancé par : {self.collecte_info['lanceur']}"),
            QLabel(f"📬 Nouvelles demandes : {self.collecte_info['nb_nouvelles']}"),
            QLabel(f"📋 Total demandes : {self.collecte_info['nb_total']}"),
        ]
        ligne("👤 Utilisateur", self.info_user_labels)
        ligne("📊 Collecte", self.info_collecte_labels)
        parent_layout.addWidget(card)

    def create_zone_dashboard(self, parent_layout):
        """Quatre tuiles de statistiques compactes, sur une seule rangée."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        stats = [
            ("🆕 Demandes récentes\n(moins de 24h)", str(self.dashboard_stats['recentes']), "#1F4E9C", "#E8EEF9"),
            ("⚠️ Demandes non affectées", str(self.dashboard_stats['non_affectees']), "#B45309", "#FDF1E3"),
            ("📝 Demandes à étudier", str(self.dashboard_stats['a_etudier']), "#4C51BF", "#EEF0FD"),
            ("👤 Mes demandes en cours", str(self.dashboard_stats['mes_demandes']), "#2F855A", "#E6F4EC")
        ]

        # Valeurs conservées par référence : update_dashboard les met à jour
        self.kpi_value_labels = []
        for titre, valeur, couleur_texte, couleur_fond in stats:
            card = QFrame()
            card.setObjectName("KpiTile")
            card.setFixedHeight(62)
            card.setStyleSheet(f"""
                QFrame#KpiTile {{
                    background-color: {couleur_fond};
                    border: 1px solid {couleur_texte};
                    border-radius: 10px;
                }}
            """)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 4, 12, 4)
            card_layout.setSpacing(10)

            label_valeur = QLabel(valeur)
            label_valeur.setStyleSheet(f"""
                color: {couleur_texte};
                font-size: 28px;
                font-weight: bold;
                background-color: transparent;
            """)
            label_valeur.setAlignment(Qt.AlignCenter)
            label_valeur.setMinimumWidth(56)

            label_titre = QLabel(titre)
            label_titre.setStyleSheet(f"""
                color: {couleur_texte};
                font-size: 12px;
                font-weight: bold;
                background-color: transparent;
            """)
            label_titre.setWordWrap(True)

            card_layout.addWidget(label_valeur)
            card_layout.addWidget(label_titre, 1)
            self.kpi_value_labels.append(label_valeur)
            layout.addWidget(card, 1)

        parent_layout.addLayout(layout)

    def create_zone_actions(self, parent_layout):
        group = QFrame()
        group.setObjectName("ActionsCard")
        group.setStyleSheet("QFrame#ActionsCard { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }")

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(8)
        # Boutons avec leurs couleurs et couleurs hover
        buttons = [
            ("➕ Nouvelle demande", "#1F4E9C", "#1A4286"),  # Primaire
            ("✅ Traiter (masse)", "#2F855A", "#276749"),  # Succès
            ("⚙️ Gérer (masse)", "#B45309", "#92400E"),  # Alerte
            ("🚫 Annuler (masse)", "#C53030", "#9B2C2C"),  # Danger
            ("📦 Archiver (masse)", "#475569", "#334155"),  # Ardoise
            ("📊 Rapports", "#4C51BF", "#434190"),  # Indigo
            ("💾 Exporter", "#0F766E", "#115E59")  # Sarcelle
        ]

        for text, color, hover_color in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: #FFFFFF;
                    color: {color};
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    border: 1.5px solid {color};
                }}
                QPushButton:hover {{
                    background: {color};
                    color: white;
                }}
                QPushButton:pressed {{
                    background: {hover_color};
                    color: white;
                    border-color: {hover_color};
                }}
            """)
            btn.setMinimumWidth(110)

            if text == "➕ Nouvelle demande":
                self.btn_nouvelle_demande = btn
                btn.clicked.connect(self.nouvelle_demande)

            if text == "🚫 Annuler (masse)":
                self.btn_annuler_masse = btn
                btn.clicked.connect(self.annuler_masse)

            if text == "📦 Archiver (masse)":
                self.btn_archiver_masse = btn
                btn.clicked.connect(self.archiver_masse)

            if text == "✅ Traiter (masse)":
                self.btn_traiter_masse = btn
                btn.clicked.connect(self.traiter_masse)

            if text == "⚙️ Gérer (masse)":
                self.btn_gerer_masse = btn
                btn.clicked.connect(self.gerer_masse)

            if text == "💾 Exporter":
                self.btn_exporter = btn
                btn.clicked.connect(self.exporter_demandes)

            if text == "📊 Rapports":
                self.btn_rapports = btn
                btn.clicked.connect(self.generer_rapports)

            layout.addWidget(btn)

        layout.addStretch()

        self.btn_update = QPushButton("🗂️ Collecte depuis la LD")
        self.btn_update.setStyleSheet("""
            QPushButton {
                    background: #1F4E9C;
                    color: white;
                    font-weight: bold;
                    padding: 6px 14px;
                    border-radius: 6px;
                    font-size: 12px;
                    border: none;
                }
                QPushButton:hover {
                    background: #1A4286;
                }
            """)
        self.btn_update.clicked.connect(self.refresh_data)
        layout.addWidget(self.btn_update)

        self.btn_refresh = QPushButton("🔄 Mettre à jour les demandes")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                    background: #0F766E;
                    color: white;
                    font-weight: bold;
                    padding: 6px 14px;
                    border-radius: 6px;
                    font-size: 12px;
                    border: none;
                }
                QPushButton:hover {
                    background: #115E59;
                }
            """)
        self.btn_refresh.clicked.connect(self.auto_refresh_data)
        layout.addWidget(self.btn_refresh)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def create_zone_demandes(self, parent_layout):
        """Zone 5 : Liste des demandes avec filtres (occupe tout l'espace restant)."""
        group = QFrame()
        group.setObjectName("DemandesCard")
        group.setStyleSheet("QFrame#DemandesCard { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }")

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)
        titre = QLabel("📋 Liste des demandes")
        titre.setStyleSheet("font-size: 13px; font-weight: bold; color: #0F2A52; background: transparent;")
        filter_layout.addWidget(titre)
        astuce = QLabel("double-clic sur une ligne : détail")
        astuce.setStyleSheet("font-size: 11px; color: #94A3B8; background: transparent;")
        filter_layout.addWidget(astuce)
        filter_layout.addSpacing(10)
        filter_layout.addWidget(QLabel("Filtres :"))

        # Créer les checkbox avec état par défaut
        self.cb_archives = QCheckBox("Afficher les demandes archivées")
        self.cb_archives.setChecked(False)  # Décochée par défaut
        self.cb_archives.stateChanged.connect(self.appliquer_filtres)

        self.cb_annulees = QCheckBox("Afficher les demandes annulées")
        self.cb_annulees.setChecked(False)  # Décochée par défaut
        self.cb_annulees.stateChanged.connect(self.appliquer_filtres)

        self.cb_realisees = QCheckBox("Afficher les demandes Traitée")
        self.cb_realisees.setChecked(True)  # Cochée par défaut
        self.cb_realisees.stateChanged.connect(self.appliquer_filtres)

        for cb in [self.cb_archives, self.cb_annulees, self.cb_realisees]:
            cb.setStyleSheet("font-size: 12px; color: #475569;")
            filter_layout.addWidget(cb)

        filter_layout.addStretch()

        # Message avec nombre de demandes affichées (sur la ligne d'en-tête, à droite)
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.info_label.setStyleSheet("color: #64748B; font-size: 11px; background: transparent;")
        filter_layout.addWidget(self.info_label)
        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        from PyQt5.QtWidgets import QAbstractItemView
        # Empêcher toute édition des cellules
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # (optionnel) empêcher l’utilisateur d’insérer/supprimer des lignes via le clavier
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Double-clic sur une cellule : modifier le champ dans le tableau (mêmes champs que « Gérer »)
        self._init_edition_cellule()

        self.load_demandes_table()
        layout.addWidget(self.table, 1)
        self.update_info_label()

        group.setLayout(layout)
        parent_layout.addWidget(group, 1)

        header = self.table.horizontalHeader()

        # ===== INITIALISATION DU SYSTÈME DE FILTRAGE =====
        # Stocker les labels de base pour restauration après filtre
        # ✅ RÉCUPÉRER LA CONFIG DES COLONNES DEPUIS LA BD
        colonnes_config = self.data_manager.get_colonnes_config(visible_only=True)

        # Extraire les libellés pour le header
        colonnes_labels = [col['libelle'] for col in colonnes_config]
        self.header_labels = colonnes_labels

        # Dictionnaire pour stocker les filtres actifs par colonne
        self.mots_cles = {i: [] for i in range(self.table.columnCount())}

        # Dictionnaire pour stocker l'état des checkboxes par colonne
        self.etat_coches_col = {}

        # Colonne actuellement en cours de filtrage
        self.colonne_active = None

        # ========== AJOUT : DICTIONNAIRE POUR LE TRI ==========
        self.ordre_tri = {i: None for i in range(self.table.columnCount())}
        # ✅ CLIC GAUCHE : pour cocher/décocher les checkboxes
        header.sectionClicked.connect(self.on_header_clicked_combined)
        #  ✅ CLIC DROIT : pour afficher le menu contextuel
        header.setSectionsClickable(True)
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.afficherMenuEntete)

    def update_info_label(self):
        """Met à jour le label d'information avec les filtres actifs"""
        # Vérification de sécurité
        if not hasattr(self, 'info_label') or self.info_label is None:
            return  # Sortir si le label n'existe pas encore

        nb_affiches = self.table.rowCount()
        total = self.data_manager.get_total_demandes()

        filtres_actifs = []
        if not self.cb_archives.isChecked():
            filtres_actifs.append("archivées masquées")
        if not self.cb_annulees.isChecked():
            filtres_actifs.append("annulées masquées")
        if not self.cb_realisees.isChecked():
            filtres_actifs.append("Traitées masquées")

        if filtres_actifs:
            filtres_text = " (" + ", ".join(filtres_actifs) + ")"
        else:
            filtres_text = " (tous les états affichés)"

        info_text = f"Affichage de {nb_affiches} demandes sur {total} au total{filtres_text}"
        info_text += avertissement_limite(getattr(self, 'nb_demandes_chargees', 0),
                                          getattr(self, 'limite_chargement', 0))
        self.info_label.setText(info_text)

    def create_actions_widget(self, row_idx):
        """Crée le widget des boutons d'actions"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)  # ← Parent direct
        actions_layout.setAlignment(Qt.AlignCenter)
        actions_layout.setContentsMargins(0, 0, 0, 0)  # ← MARGES À ZÉRO
        actions_layout.setSpacing(4)

        # Bouton Dupliquer
        btn_dup = QPushButton("📋")
        btn_dup.setToolTip("Dupliquer")
        btn_dup.setFixedSize(28, 24)
        btn_dup.setStyleSheet("""
            QPushButton {
                background: #EEF0FD;
                color: #4C51BF;
                font-weight: bold;
                border-radius: 6px;
                font-size: 14px;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #4C51BF;
                color: white;
            }
        """)
        btn_dup.clicked.connect(lambda: self.dupliquer_demande(row_idx))
        actions_layout.addWidget(btn_dup)

        # Bouton Voir plus
        btn_voir = QPushButton("👁")
        btn_voir.setToolTip("Voir plus")
        btn_voir.setFixedSize(28, 24)
        btn_voir.setStyleSheet("""
            QPushButton {
                background: #E8EEF9;
                color: #1F4E9C;
                font-weight: bold;
                border-radius: 6px;
                font-size: 14px;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #1F4E9C;
                color: white;
            }
        """)
        btn_voir.clicked.connect(lambda: self.voir_plus_demande(row_idx))
        actions_layout.addWidget(btn_voir)

        # Gérer unit_buttons
        if not hasattr(self, 'unit_buttons'):
            self.unit_buttons = {}
        if 'dupliquer' not in self.unit_buttons:
            self.unit_buttons['dupliquer'] = []
        if 'voirplus' not in self.unit_buttons:
            self.unit_buttons['voirplus'] = []

        self.unit_buttons['dupliquer'].append(btn_dup)
        self.unit_buttons['voirplus'].append(btn_voir)

        return actions_widget

    def update_dashboard(self):
        """Met à jour les valeurs des tuiles de statistiques."""
        valeurs = [self.dashboard_stats['recentes'], self.dashboard_stats['non_affectees'],
                   self.dashboard_stats['a_etudier'], self.dashboard_stats['mes_demandes']]
        for label, valeur in zip(self.kpi_value_labels, valeurs):
            label.setText(str(valeur))

    def update_display_info(self):
        """Met à jour UNIQUEMENT le texte des labels sans recréer les widgets"""
        user = self.info_user_labels
        user[0].setText(f"👨‍💼 Utilisateur : {self.user_info['prenom']} {self.user_info['nom']}")
        user[1].setText(f"🔑 Rôle : {self.user_info['role']}")
        user[2].setText(f"📅 Connecté le : {self.user_info['date_connexion']}")

        collecte = self.info_collecte_labels
        collecte[0].setText(f"🕐 Dernière collecte : {self.collecte_info['date_collecte']}")
        collecte[1].setText(f"👤 Lancé par : {self.collecte_info['lanceur']}")
        collecte[2].setText(f"📬 Nouvelles demandes : {self.collecte_info['nb_nouvelles']}")
        collecte[3].setText(f"📋 Total demandes : {self.collecte_info['nb_total']}")

        self.update_dashboard()
