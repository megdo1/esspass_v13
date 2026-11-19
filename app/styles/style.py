"""
Module de styles pour l'application PASS
Centralise tous les styles CSS utilisés dans l'interface graphique

Fichier: app/styles/style.py
"""


# ========== STYLES GLOBAUX ==========
TITLE_STYLE = """
    font-size: 16px;
    font-weight: bold;
    color: #475569;
    padding: 15px;
"""

TAB_LABEL_STYLE = """
    font-size: 14px;
    font-weight: bold;
    color: #475569;
    padding: 10px;
"""

# ========== STYLES BOUTONS ==========
BUTTON_CLOSE_STYLE = "padding: 10px 20px;"

# Bouton d'action principal (plein) et bouton destructif (contour rouge) : mêmes teintes que le reste de l'application
BUTTON_PRIMAIRE_STYLE = """
    QPushButton { background: #1F4E9C; color: #FFFFFF; border: 1px solid #1F4E9C; }
    QPushButton:hover { background: #1A4286; border-color: #1A4286; }
    QPushButton:pressed { background: #143468; }
    QPushButton:disabled { background: #E2E8F0; color: #94A3B8; border-color: #E2E8F0; }
"""

BUTTON_DANGER_STYLE = """
    QPushButton { background: #FFFFFF; color: #C53030; border: 1px solid #C53030; }
    QPushButton:hover { background: #FDECEC; border-color: #9B2C2C; color: #9B2C2C; }
    QPushButton:pressed { background: #F8CFCF; }
    QPushButton:disabled { background: #F8FAFC; color: #94A3B8; border-color: #CBD5E1; }
"""

# Cellules du tableau des utilisateurs : même marge à l'état normal et sélectionné (sans cela, le texte d'une
# ligne sélectionnée est décalé). Pas de `border` sur ::item : cela casserait le retour à la ligne.
TABLE_ITEM_STYLE = """
    QTableWidget::item { padding: 0px; }
    QTableWidget::item:selected { padding: 0px; background-color: #DBEAFE; color: #0F172A; }
"""

# Onglets : identiques à ceux de l'écran de configuration
TABS_STYLE = """
    QTabWidget::pane {
        border: 1px solid #CBD5E1;
        border-radius: 4px;
        background: white;
    }
    QTabBar::tab {
        background: #F4F6FA;
        border: 1px solid #CBD5E1;
        padding: 8px 20px;
        min-width: 170px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: white;
        border-bottom-color: white;
    }
    QTabBar::tab:hover {
        background: #E2E8F0;
    }
"""

BUTTON_MODIFIER_STYLE = """
    background: #1F4E9C;
    color: white;
    font-weight: bold;
    padding: 10px 20px;
"""

BUTTON_ACTIVER_STYLE = """
    background: #2F855A;
    color: white;
    font-weight: bold;
    padding: 10px 20px;
"""

BUTTON_DESACTIVER_STYLE = """
    background: #B45309;
    color: white;
    font-weight: bold;
    padding: 10px 20px;
"""

BUTTON_SUPPRIMER_STYLE = """
    background: #C53030;
    color: white;
    font-weight: bold;
    padding: 10px 20px;
"""

BUTTON_CREER_STYLE = """
    background: #2F855A;
    color: white;
    font-weight: bold;
    padding: 10px 20px;
"""

BUTTON_REINITIALISER_STYLE = """
    background: #64748B;
    color: white;
    font-weight: bold;
    padding: 10px 20px;
"""

BUTTON_EXPORTER_STYLE = """
    background: #B45309;
    color: white;
    font-weight: bold;
    padding: 10px 20px;
"""

# ========== STYLES TABLEAUX ==========
TABLEAU_UTILISATEURS_STYLE = """
    QTableWidget {
        background-color: white;
        gridline-color: #E2E8F0;
        font-size: 11px;
        font-weight: normal;
    }

    QTableWidget::item {
        padding: 8px;
        height: 35px;
    }

    QTableWidget::item:selected {
        background-color: #1F4E9C;
        color: white;
        font-weight: bold;
        padding: 8px;
        border: none;
    }

    QHeaderView::section {
        background-color: #475569;
        color: white;
        padding: 8px;
        border: 1px solid #334155;
        font-weight: bold;
    }

    QScrollBar:vertical {
        width: 12px;
        background-color: #F1F5F9;
    }

    QScrollBar::handle:vertical {
        background-color: #1F4E9C;
        border-radius: 6px;
    }
"""

TABLEAU_MATRICE_STYLE = """
    QTableWidget {
        background-color: white;
        gridline-color: #E2E8F0;
        font-size: 11px;
        font-weight: normal;
    }

    QTableWidget::item {
        padding: 8px;
        height: 35px;
    }

    QHeaderView::section {
        background-color: #475569;
        color: white;
        padding: 8px;
        border: 1px solid #334155;
        font-weight: bold;
    }

    QScrollBar:vertical {
        width: 12px;
        background-color: #F1F5F9;
    }

    QScrollBar::handle:vertical {
        background-color: #1F4E9C;
        border-radius: 6px;
    }
"""

# ========== STYLES GROUP BOX ==========
GROUP_BOX_BLEU_STYLE = """
    QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
    QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #1F4E9C; }
"""

GROUP_BOX_GRIS_STYLE = """
    QGroupBox { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; margin-top: 0px; padding-top: 30px; font-weight: bold; }
    QGroupBox::title { subcontrol-origin: padding; subcontrol-position: top left; padding: 9px 14px 0 14px; color: #475569; }
"""

# ========== STYLES LABELS ==========
LABEL_CONSULTANT_STYLE = """
    font-size: 12px;
    color: #143468;
    font-weight: bold;
"""

LABEL_MCO_STYLE = """
    font-size: 12px;
    color: #1C4532;
    font-weight: bold;
"""

LABEL_ADMIN_STYLE = """
    font-size: 12px;
    color: #7F1D1D;
    font-weight: bold;
"""

LABEL_DESCRIPTION_STYLE = """
    font-size: 11px;
    color: #555;
    margin-top: 5px;
    line-height: 1.5;
"""

# ========== STYLES INPUTS ==========
INPUT_STYLE = "min-height: 35px;"

CHECKBOX_STYLE = "padding: 5px;"

COMBO_BOX_STYLE = "min-height: 35px;"

# ========== STYLES CHECKBOX TABLE ==========
CHECKBOX_TABLE_STYLE = """
    QCheckBox {
        margin: 0px;
        padding: 0px;
    }

    QCheckBox::indicator {
        width: 18px;
        height: 18px;
    }

    QCheckBox::indicator:checked {
        background-color: #2F855A;
        border: 1px solid #22543D;
        border-radius: 3px;
    }
"""

# ========== COULEURS ==========
COLOR_CONSULTANT = "#1F4E9C"
COLOR_MCO = "#22543D"
COLOR_ADMIN = "#822727"

COLOR_CONSULTANT_LIGHT = "#143468"
COLOR_MCO_LIGHT = "#1C4532"
COLOR_ADMIN_LIGHT = "#7F1D1D"

# ========== COULEURS TABLEAUX UTILISATEURS PAR RÔLE ==========
COLOR_ROLE_CONSULTANT_BG = "#E3F4F2"  # Bleu très clair
COLOR_ROLE_MCO_BG = "#E6F4EC"          # Vert très clair
COLOR_ROLE_ADMIN_BG = "#FDECEC"        # Rouge très clair

COLOR_ROLE_CONSULTANT_TEXT = "#1F4E9C"
COLOR_ROLE_MCO_TEXT = "#22543D"
COLOR_ROLE_ADMIN_TEXT = "#822727"

# ========== COULEURS STATUT ==========
COLOR_STATUT_ACTIF_BG = "#C6E5D3"      # Vert clair
COLOR_STATUT_ACTIF_TEXT = "#1C4532"    # Vert foncé

COLOR_STATUT_INACTIF_BG = "#F8CFCF"    # Rouge clair
COLOR_STATUT_INACTIF_TEXT = "#7F1D1D"  # Rouge foncé

# ========== COULEURS MATRICE ==========
COLOR_MATRICE_ALLOWED = "#C6E5D3"  # Vert clair pour les permissions accordées
COLOR_MATRICE_DENIED = "#F8CFCF"   # Rouge clair pour les permissions refusées

# ========== TAILLES COLONNES ==========
COLUMN_WIDTHS_UTILISATEURS = {
    "id": 50,
    "nom": 200,
    "email": 250,
    "role": 150,
    "statut": 100,
}

COLUMN_WIDTHS_MATRICE = {
    "action": 300,
    "consultant": 150,
    "mco": 150,
    "admin": 150,
}

# ========== FONTS ==========
from PyQt5.QtGui import QFont

FONT_BOLD_11 = QFont("Arial", 11, QFont.Bold)
FONT_BOLD_12 = QFont("Arial", 12, QFont.Bold)
FONT_BOLD_14 = QFont("Arial", 14, QFont.Bold)
FONT_NORMAL_11 = QFont("Arial", 11)

# ========== DONNÉES MATRICE ==========
MATRICE_ACTIONS = [
    ("Consulter les demandes", "✅", "✅", "✅"),
    ("Consulter les rapports", "✅", "✅", "✅"),
    ("Exporter les rapports", "✅", "✅", "✅"),
    ("Consulter les archives", "✅", "✅", "✅"),
    ("Créer une demande", "❌", "✅", "✅"),
    ("Mettre à jour une demande", "❌", "✅", "✅"),
    ("Formuler une réponse", "❌", "✅", "✅"),
    ("Annuler une demande", "❌", "✅", "✅"),
    ("Lancer une collecte", "❌", "✅", "✅"),
    ("Archiver une demande", "❌", "❌", "✅"),
    ("Gérer les listes de valeurs", "❌", "❌", "✅"),
    ("Habiliter des utilisateurs", "❌", "❌", "✅"),
    ("Gérer les traitements automatiques", "❌", "❌", "✅"),
]
