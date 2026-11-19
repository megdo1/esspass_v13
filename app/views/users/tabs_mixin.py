"""Onglets du dialogue : liste, création et matrice des droits."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.styles import style
from app.utils.matrice_droits import MATRICE_DROITS, ROLES_MATRICE, droit_accorde
from app.views.users.widgets import INDIGO, PRIMAIRE, SARCELLE, SUCCES, PastilleDelegate, creer_carte, creer_tuile

TEXTE_CASE_RESPONSABLE = "Responsable ES-PASS (proposé dans les listes « Responsable » des demandes)"
INFOBULLE_TABLE_ABSENTE = ("Indisponible : la table utilisateur_responsable n'existe pas dans la base. "
                           "Exécutez le script scripts/sql/001_utilisateur_responsable.sql.")

# Colonnes du tableau (les indices sont utilisés par les actions : ne pas les réordonner)
COL_ID, COL_NOM, COL_PRENOM, COL_EMAIL, COL_ROLE, COL_STATUT, COL_RESPONSABLE = range(7)

DESCRIPTIONS_ROLES = {
    "consultant": "Lecture seule : consulte les demandes, les rapports et les exports.",
    "membre_mco": "Traite les demandes : création, modification, réponse, annulation, traitement en masse "
                  "et collecte des mails.",
    "administrateur": "Tous les droits du Membre MCO, plus l'archivage, les listes de valeurs, les utilisateurs, "
                      "les responsables ES-PASS et les collectes.",
}
BLOCS_ROLES = [
    ("Consultant", PRIMAIRE, ["Consulte les demandes, les archives et les rapports", "Exporte les données",
                              "Aucune modification possible"]),
    ("Membre MCO", SUCCES, ["Crée, duplique, modifie, traite et annule des demandes", "Traitement en masse",
                           "Lance la collecte des mails"]),
    ("Administrateur", INDIGO, ["Tous les droits du Membre MCO", "Archive les demandes",
                               "Gère les listes de valeurs, les utilisateurs, les responsables ES-PASS "
                               "et les collectes"]),
]


class TabsMixin:
    """Onglets du dialogue : liste, création et matrice des droits."""

    # ------------------------------------------------------------------ synthèse (tuiles en haut de l'écran)
    def create_zone_synthese(self, parent_layout):
        """Quatre tuiles de synthèse ; leurs valeurs sont mises à jour par `load_utilisateurs`."""
        ligne = QHBoxLayout()
        ligne.setSpacing(10)
        self.tuiles_utilisateurs = {}
        for cle, titre, couleurs in [
            ("total", "Utilisateurs", PRIMAIRE),
            ("actifs", "Utilisateurs actifs", SUCCES),
            ("admins", "Administrateurs actifs", INDIGO),
            ("responsables", "Responsables ES-PASS", SARCELLE),
        ]:
            tuile, valeur = creer_tuile(titre, couleurs)
            self.tuiles_utilisateurs[cle] = valeur
            ligne.addWidget(tuile, 1)
        parent_layout.addLayout(ligne)

    # ------------------------------------------------------------------ onglet « Liste »
    def create_tab_utilisateurs(self):
        """Crée l'onglet avec la liste des utilisateurs"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # --- barre de recherche et filtres
        barre = QHBoxLayout()
        barre.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher par nom, prénom ou e-mail…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.filtrer_utilisateurs)
        barre.addWidget(self.search_input, 1)

        self.combo_filtre_role = QComboBox()
        self.combo_filtre_role.addItem("Tous les rôles", None)
        for role in ROLES_MATRICE:
            self.combo_filtre_role.addItem(role, role)
        self.combo_filtre_statut = QComboBox()
        self.combo_filtre_statut.addItem("Tous les statuts", None)
        self.combo_filtre_statut.addItem("Actifs", True)
        self.combo_filtre_statut.addItem("Inactifs", False)
        self.combo_filtre_responsable = QComboBox()
        self.combo_filtre_responsable.addItem("Responsables : tous", None)
        self.combo_filtre_responsable.addItem("Responsables ES-PASS", True)
        self.combo_filtre_responsable.addItem("Non responsables", False)
        for combo in (self.combo_filtre_role, self.combo_filtre_statut, self.combo_filtre_responsable):
            combo.setMinimumWidth(170)
            combo.currentIndexChanged.connect(self.filtrer_utilisateurs)
            barre.addWidget(combo)
        layout.addLayout(barre)

        # --- tableau
        self.tableau_utilisateurs = QTableWidget()
        t = self.tableau_utilisateurs
        t.setColumnCount(7)
        t.setHorizontalHeaderLabels(["ID", "Nom", "Prénom", "E-mail", "Rôle", "Statut", "Responsable ES-PASS"])
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(38)
        t.setShowGrid(False)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setWordWrap(False)
        t.setStyleSheet(style.TABLE_ITEM_STYLE)
        entete = t.horizontalHeader()
        entete.setHighlightSections(False)
        entete.setStretchLastSection(False)
        for colonne, mode, largeur in [(COL_ID, QHeaderView.Fixed, 60), (COL_NOM, QHeaderView.Stretch, 0),
                                       (COL_PRENOM, QHeaderView.Stretch, 0), (COL_EMAIL, QHeaderView.Stretch, 0),
                                       (COL_ROLE, QHeaderView.Fixed, 150), (COL_STATUT, QHeaderView.Fixed, 110),
                                       (COL_RESPONSABLE, QHeaderView.Fixed, 180)]:
            entete.setSectionResizeMode(colonne, mode)
            if largeur:
                t.setColumnWidth(colonne, largeur)
        pastilles = PastilleDelegate(t)
        self._delegue_pastilles = pastilles                     # référence conservée (Qt ne prend pas la propriété)
        for colonne in (COL_ROLE, COL_STATUT, COL_RESPONSABLE):
            t.setItemDelegateForColumn(colonne, pastilles)
        t.itemSelectionChanged.connect(self._maj_boutons_actions)
        t.cellDoubleClicked.connect(lambda *_: self.modifier_utilisateur())
        layout.addWidget(t, 1)

        # --- pied : compteur et actions
        pied = QHBoxLayout()
        pied.setSpacing(8)
        self.btn_modifier = QPushButton("✏️ Modifier l'utilisateur")
        self.btn_modifier.setStyleSheet(style.BUTTON_PRIMAIRE_STYLE)
        self.btn_modifier.clicked.connect(self.modifier_utilisateur)
        self.btn_activer = QPushButton("✅ Activer")
        self.btn_activer.clicked.connect(self.activer_utilisateur)
        self.btn_desactiver = QPushButton("🚫 Désactiver")
        self.btn_desactiver.clicked.connect(self.desactiver_utilisateur)
        self.btn_supprimer = QPushButton("🗑️ Supprimer")
        self.btn_supprimer.setStyleSheet(style.BUTTON_DANGER_STYLE)
        self.btn_supprimer.clicked.connect(self.supprimer_utilisateur)
        for bouton in (self.btn_modifier, self.btn_activer, self.btn_desactiver, self.btn_supprimer):
            pied.addWidget(bouton)
        pied.addStretch()
        self.lbl_compteur_utilisateurs = QLabel("")
        self.lbl_compteur_utilisateurs.setStyleSheet("color: #64748B;")
        pied.addWidget(self.lbl_compteur_utilisateurs)
        layout.addLayout(pied)

        self._maj_boutons_actions()
        return tab

    # ------------------------------------------------------------------ onglet « Créer »
    def create_tab_creer_utilisateur(self):
        """Crée l'onglet pour créer un nouvel utilisateur"""
        tab = QWidget()
        principal = QHBoxLayout(tab)
        principal.setContentsMargins(14, 14, 14, 14)
        principal.setSpacing(14)

        # --- carte de gauche : le formulaire
        carte = creer_carte("CarteFormulaire")
        gauche = QVBoxLayout(carte)
        gauche.setContentsMargins(20, 18, 20, 18)
        gauche.setSpacing(12)

        titre = QLabel("Nouvel utilisateur")
        titre.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F2A52;")
        gauche.addWidget(titre)
        aide = QLabel("Renseignez l'identité du compte, son rôle et, si besoin, son statut de responsable ES-PASS.")
        aide.setStyleSheet("color: #64748B;")
        aide.setWordWrap(True)
        gauche.addWidget(aide)

        formulaire = QFormLayout()
        formulaire.setHorizontalSpacing(16)
        formulaire.setVerticalSpacing(12)
        formulaire.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.input_nom = QLineEdit()
        self.input_nom.setPlaceholderText("Ex : Dupont")
        self.input_nom.setMinimumHeight(34)
        formulaire.addRow("Nom", self.input_nom)

        self.input_prenom = QLineEdit()
        self.input_prenom.setPlaceholderText("Ex : Jean")
        self.input_prenom.setMinimumHeight(34)
        formulaire.addRow("Prénom", self.input_prenom)

        self.input_email = QLineEdit()
        self.input_email.setPlaceholderText("Ex : jean.dupont@sncf.fr")
        self.input_email.setMinimumHeight(34)
        formulaire.addRow("E-mail", self.input_email)

        self.combo_role_new = QComboBox()
        self.combo_role_new.addItem("Consultant", "consultant")
        self.combo_role_new.addItem("Membre MCO", "membre_mco")
        self.combo_role_new.addItem("Administrateur", "administrateur")
        self.combo_role_new.setMinimumHeight(34)
        self.combo_role_new.currentIndexChanged.connect(self._maj_description_role)
        formulaire.addRow("Rôle", self.combo_role_new)

        self.lbl_description_role = QLabel("")
        self.lbl_description_role.setWordWrap(True)
        self.lbl_description_role.setStyleSheet("color: #64748B; font-size: 12px;")
        formulaire.addRow("", self.lbl_description_role)

        self.check_actif = QCheckBox("Utilisateur actif")
        self.check_actif.setChecked(True)
        formulaire.addRow("Statut", self.check_actif)

        self.check_responsable = QCheckBox(TEXTE_CASE_RESPONSABLE)
        if not self.data_manager.table_responsables_existe():
            self.check_responsable.setEnabled(False)
            self.check_responsable.setToolTip(INFOBULLE_TABLE_ABSENTE)
        formulaire.addRow("Responsable", self.check_responsable)
        gauche.addLayout(formulaire)
        gauche.addStretch()

        boutons = QHBoxLayout()
        self.btn_creer = QPushButton("➕ Créer l'utilisateur")
        self.btn_creer.setStyleSheet(style.BUTTON_PRIMAIRE_STYLE)
        self.btn_creer.clicked.connect(self.creer_utilisateur)
        self.btn_reinitialiser = QPushButton("🔄 Réinitialiser")
        self.btn_reinitialiser.clicked.connect(self.reinitialiser_form)
        boutons.addWidget(self.btn_creer)
        boutons.addWidget(self.btn_reinitialiser)
        boutons.addStretch()
        gauche.addLayout(boutons)
        principal.addWidget(carte, 3)

        # --- colonne de droite : les trois rôles
        droite = QVBoxLayout()
        droite.setSpacing(10)
        entete = QLabel("Rôles disponibles")
        entete.setStyleSheet("font-size: 13px; font-weight: 700; color: #334155;")
        droite.addWidget(entete)
        for nom, (couleur, fond), points in BLOCS_ROLES:
            bloc = QFrame()
            bloc.setObjectName("BlocRole")
            bloc.setStyleSheet(f"""
                QFrame#BlocRole {{
                    background-color: {fond};
                    border: none;
                    border-left: 4px solid {couleur};
                    border-radius: 6px;
                }}
            """)
            interieur = QVBoxLayout(bloc)
            interieur.setContentsMargins(14, 10, 12, 10)
            interieur.setSpacing(4)
            nom_label = QLabel(nom)
            nom_label.setStyleSheet(f"color: {couleur}; font-size: 13px; font-weight: 700; background: transparent;")
            interieur.addWidget(nom_label)
            for point in points:
                ligne = QLabel("•  " + point)
                ligne.setWordWrap(True)
                ligne.setStyleSheet("color: #334155; font-size: 12px; background: transparent;")
                interieur.addWidget(ligne)
            droite.addWidget(bloc)
        droite.addStretch()
        principal.addLayout(droite, 2)

        self._maj_description_role()
        return tab

    def _maj_description_role(self, *_):
        """Affiche sous la liste des rôles la description du rôle choisi."""
        self.lbl_description_role.setText(DESCRIPTIONS_ROLES.get(self.combo_role_new.currentData(), ""))

    # ------------------------------------------------------------------ onglet « Matrice des droits »
    def create_tab_matrice_droits(self):
        """Matrice des droits par rôle, calculée à partir des permissions réellement appliquées (utils.auth)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        titre = QLabel("Droits par rôle")
        titre.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F2A52;")
        layout.addWidget(titre)
        aide = QLabel("Reflet exact des droits appliqués par l'application. "
                      "Pour qu'un utilisateur change de droits, modifiez son rôle ; il doit ensuite relancer ES-PASS.")
        aide.setStyleSheet("color: #64748B;")
        aide.setWordWrap(True)
        layout.addWidget(aide)

        matrice = QTableWidget(len(MATRICE_DROITS), 1 + len(ROLES_MATRICE))
        self.tableau_matrice = matrice
        matrice.setHorizontalHeaderLabels(["Action", *ROLES_MATRICE])
        matrice.verticalHeader().setVisible(False)
        matrice.verticalHeader().setDefaultSectionSize(34)
        matrice.setShowGrid(False)
        matrice.setAlternatingRowColors(True)
        matrice.setEditTriggers(QAbstractItemView.NoEditTriggers)
        matrice.setSelectionMode(QAbstractItemView.NoSelection)
        entete = matrice.horizontalHeader()
        entete.setHighlightSections(False)
        entete.setSectionResizeMode(0, QHeaderView.Stretch)
        for colonne in range(1, 1 + len(ROLES_MATRICE)):
            entete.setSectionResizeMode(colonne, QHeaderView.Fixed)
            matrice.setColumnWidth(colonne, 150)

        for ligne, (libelle, cle) in enumerate(MATRICE_DROITS):
            matrice.setItem(ligne, 0, QTableWidgetItem(libelle))
            for colonne, role in enumerate(ROLES_MATRICE, start=1):
                accorde = droit_accorde(role, cle)
                case = QTableWidgetItem("✓" if accorde else "—")
                case.setTextAlignment(Qt.AlignCenter)
                case.setForeground(QColor(SUCCES[0] if accorde else "#94A3B8"))
                if accorde:
                    case.setBackground(QColor(SUCCES[1]))
                    gras = case.font()
                    gras.setBold(True)
                    case.setFont(gras)
                case.setData(Qt.UserRole, accorde)
                matrice.setItem(ligne, colonne, case)
        layout.addWidget(matrice, 1)
        return tab
