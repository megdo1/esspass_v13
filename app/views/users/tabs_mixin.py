"""Onglets du dialogue : liste, création et matrice des droits."""

from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QComboBox, QLineEdit, QCheckBox, QGroupBox, QFormLayout, QAbstractItemView, QWidget, QScrollArea
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from app.styles import style


class TabsMixin:
    """Onglets du dialogue : liste, création et matrice des droits."""

    def create_tab_utilisateurs(self):
        """Crée l'onglet avec la liste des utilisateurs"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Rechercher :"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nom ou email de l'utilisateur...")
        self.search_input.textChanged.connect(self.filtrer_utilisateurs)
        search_layout.addWidget(self.search_input)

        layout.addLayout(search_layout)

        self.tableau_utilisateurs = QTableWidget()
        self.tableau_utilisateurs.setColumnCount(6)
        self.tableau_utilisateurs.setHorizontalHeaderLabels([
            "ID", "Nom","Prénom", "Email", "Rôle Actuel", "Statut"
        ])

        self.tableau_utilisateurs.horizontalHeader().setStretchLastSection(True)
        self.tableau_utilisateurs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableau_utilisateurs.setSelectionMode(QAbstractItemView.SingleSelection)

        self.tableau_utilisateurs.setColumnWidth(0, 50)
        self.tableau_utilisateurs.setColumnWidth(1, 150)
        self.tableau_utilisateurs.setColumnWidth(2, 150)
        self.tableau_utilisateurs.setColumnWidth(3, 250)
        self.tableau_utilisateurs.setColumnWidth(4, 200)
        self.tableau_utilisateurs.setColumnWidth(5, 100)

        self.tableau_utilisateurs.setStyleSheet(style.TABLEAU_UTILISATEURS_STYLE)

        layout.addWidget(self.tableau_utilisateurs)

        action_layout = QHBoxLayout()

        btn_modifier = QPushButton("✏️ Modifier utilisateur")
        btn_modifier.setStyleSheet(style.BUTTON_MODIFIER_STYLE)
        btn_modifier.clicked.connect(self.modifier_utilisateur)
        action_layout.addWidget(btn_modifier)

        btn_activer = QPushButton("✅ Activer")
        btn_activer.setStyleSheet(style.BUTTON_ACTIVER_STYLE)
        btn_activer.clicked.connect(self.activer_utilisateur)
        action_layout.addWidget(btn_activer)

        btn_desactiver = QPushButton("🚫 Désactiver")
        btn_desactiver.setStyleSheet(style.BUTTON_DESACTIVER_STYLE)
        btn_desactiver.clicked.connect(self.desactiver_utilisateur)
        action_layout.addWidget(btn_desactiver)

        btn_supprimer = QPushButton("🗑️ Supprimer")
        btn_supprimer.setStyleSheet(style.BUTTON_SUPPRIMER_STYLE)
        btn_supprimer.clicked.connect(self.supprimer_utilisateur)
        action_layout.addWidget(btn_supprimer)

        action_layout.addStretch()

        layout.addLayout(action_layout)

        return tab

    def create_tab_creer_utilisateur(self):
        """Crée l'onglet pour créer un nouvel utilisateur"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)

        info_label = QLabel("📝 Créer un nouvel utilisateur")
        info_label.setStyleSheet(style.TAB_LABEL_STYLE)
        main_layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)

        # ========== Groupe : Informations utilisateur ==========
        form_group = QGroupBox("📋 Informations de l'utilisateur")
        form_group.setStyleSheet(style.GROUP_BOX_BLEU_STYLE)

        form_layout = QFormLayout()

        self.input_nom = QLineEdit()
        self.input_nom.setPlaceholderText("Ex: Dupont")
        self.input_nom.setMinimumHeight(35)
        form_layout.addRow("👤 Nom :", self.input_nom)
        
        self.input_prenom = QLineEdit()
        self.input_prenom.setPlaceholderText("Ex: jean")
        self.input_prenom.setMinimumHeight(35)
        form_layout.addRow("👤 Prénom:", self.input_prenom)

        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("Ex: jean.dupont@sncf.fr")
        self.input_email.setMinimumHeight(35)
        form_layout.addRow("✉️ Email :", self.input_email)

        self.combo_role_new = QComboBox()
        self.combo_role_new.addItem("🔵 Consultant", "consultant")
        self.combo_role_new.addItem("🟢 Membre MCO", "membre_mco")
        self.combo_role_new.addItem("🔴 Administrateur", "administrateur")
        self.combo_role_new.setMinimumHeight(35)

        model = self.combo_role_new.model()
        model.item(0).setForeground(QColor(style.COLOR_CONSULTANT))
        model.item(0).setFont(style.FONT_BOLD_11)
        model.item(1).setForeground(QColor(style.COLOR_MCO))
        model.item(1).setFont(style.FONT_BOLD_11)
        model.item(2).setForeground(QColor(style.COLOR_ADMIN))
        model.item(2).setFont(style.FONT_BOLD_11)

        form_layout.addRow("🎯 Rôle :", self.combo_role_new)

        self.check_actif = QCheckBox("Utilisateur actif")
        self.check_actif.setChecked(True)
        self.check_actif.setStyleSheet(style.CHECKBOX_STYLE)
        form_layout.addRow("✅ Statut :", self.check_actif)

        form_group.setLayout(form_layout)
        content_layout.addWidget(form_group)

        # ========== Groupe : Description des rôles ==========
        roles_group = QGroupBox("🔐 Description des rôles")
        roles_group.setStyleSheet(style.GROUP_BOX_GRIS_STYLE)

        roles_layout = QVBoxLayout()

        # ===== CONSULTANT =====
        consultant_widget = QWidget()
        consultant_layout = QVBoxLayout(consultant_widget)
        consultant_layout.setContentsMargins(0, 0, 0, 0)
        consultant_layout.setSpacing(5)

        consultant_title = QLabel("🔵 Consultant")
        consultant_title.setStyleSheet(style.LABEL_CONSULTANT_STYLE)
        consultant_layout.addWidget(consultant_title)

        consultant_label = QLabel(
            "• Accès en lecture seule aux données\n"
            "• Peut consulter les rapports et analyses\n"
            "• Pas de droit de modification"
        )
        consultant_label.setStyleSheet(style.LABEL_DESCRIPTION_STYLE)
        consultant_layout.addWidget(consultant_label)

        roles_layout.addWidget(consultant_widget)

        # ===== MEMBRE MCO =====
        mco_widget = QWidget()
        mco_layout = QVBoxLayout(mco_widget)
        mco_layout.setContentsMargins(0, 0, 0, 0)
        mco_layout.setSpacing(5)

        mco_title = QLabel("🟢 Membre MCO")
        mco_title.setStyleSheet(style.LABEL_MCO_STYLE)
        mco_layout.addWidget(mco_title)

        mco_label = QLabel(
            "• Accès complet en lecture/écriture\n"
            "• Peut créer, modifier et gérer les données\n"
            "• Accès limité à son équipe ou domaine"
        )
        mco_label.setStyleSheet(style.LABEL_DESCRIPTION_STYLE)
        mco_layout.addWidget(mco_label)

        roles_layout.addWidget(mco_widget)

        # ===== ADMINISTRATEUR =====
        admin_widget = QWidget()
        admin_layout = QVBoxLayout(admin_widget)
        admin_layout.setContentsMargins(0, 0, 0, 0)
        admin_layout.setSpacing(5)

        admin_title = QLabel("🔴 Administrateur")
        admin_title.setStyleSheet(style.LABEL_ADMIN_STYLE)
        admin_layout.addWidget(admin_title)

        admin_label = QLabel(
            "• Accès complet à toutes les fonctionnalités\n"
            "• Gestion complète des utilisateurs et rôles\n"
            "• Accès à tous les rapports et paramétrages"
        )
        admin_label.setStyleSheet(style.LABEL_DESCRIPTION_STYLE)
        admin_layout.addWidget(admin_label)

        roles_layout.addWidget(admin_widget)
        roles_layout.addStretch()

        roles_group.setLayout(roles_layout)
        content_layout.addWidget(roles_group)

        content_layout.addStretch()

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        # ========== Boutons d'action ==========
        button_layout = QHBoxLayout()

        btn_creer = QPushButton("➕ Créer l'utilisateur")
        btn_creer.setStyleSheet(style.BUTTON_CREER_STYLE)
        btn_creer.clicked.connect(self.creer_utilisateur)
        button_layout.addWidget(btn_creer)

        btn_reinitialiser = QPushButton("🔄 Réinitialiser")
        btn_reinitialiser.setStyleSheet(style.BUTTON_REINITIALISER_STYLE)
        btn_reinitialiser.clicked.connect(self.reinitialiser_form)
        button_layout.addWidget(btn_reinitialiser)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        return tab

    def create_tab_matrice_droits(self):
        """Crée l'onglet avec la matrice des droits"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        title = QLabel("🔐 MATRICE DES DROITS")
        title.setStyleSheet(style.TAB_LABEL_STYLE)
        layout.addWidget(title)

        matrice = QTableWidget()
        matrice.setColumnCount(4)
        matrice.setHorizontalHeaderLabels(["Action", "Consultant", "Membre MCO", "Administrateur"])

        matrice.setRowCount(len(style.MATRICE_ACTIONS))

        for row, (action, consultant, mco, admin) in enumerate(style.MATRICE_ACTIONS):
            item_action = QTableWidgetItem(action)
            item_action.setFont(style.FONT_BOLD_11)
            matrice.setItem(row, 0, item_action)

            item_c = QTableWidgetItem(consultant)
            item_c.setTextAlignment(Qt.AlignCenter)
            item_c.setBackground(
                QColor(style.COLOR_MATRICE_ALLOWED) if consultant == "✅" else QColor(style.COLOR_MATRICE_DENIED))
            matrice.setItem(row, 1, item_c)

            item_m = QTableWidgetItem(mco)
            item_m.setTextAlignment(Qt.AlignCenter)
            item_m.setBackground(
                QColor(style.COLOR_MATRICE_ALLOWED) if mco == "✅" else QColor(style.COLOR_MATRICE_DENIED))
            matrice.setItem(row, 2, item_m)

            item_a = QTableWidgetItem(admin)
            item_a.setTextAlignment(Qt.AlignCenter)
            item_a.setBackground(
                QColor(style.COLOR_MATRICE_ALLOWED) if admin == "✅" else QColor(style.COLOR_MATRICE_DENIED))
            matrice.setItem(row, 3, item_a)

        matrice.setColumnWidth(0, 300)
        for col in [1, 2, 3]:
            matrice.setColumnWidth(col, 150)

        matrice.setStyleSheet(style.TABLEAU_MATRICE_STYLE)

        layout.addWidget(matrice)

        return tab
