"""Composants graphiques de l'écran Utilisateurs : pastilles, tuiles de synthèse, cartes.

Même charte que l'écran Demandes (palette de `styles/style.css`) : tuiles teintées, pastilles arrondies,
tableaux clairs. Aucune logique métier ici.
"""

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QStyle, QStyledItemDelegate, QStyleOptionViewItem,
)

# Rôle Qt sous lequel une cellule mémorise ses couleurs de pastille : (fond, texte)
ROLE_PASTILLE = Qt.UserRole + 1

# Palette (voir en-tête de styles/style.css) : (texte, fond doux)
PRIMAIRE = ("#1F4E9C", "#E8EEF9")
SUCCES = ("#2F855A", "#E6F4EC")
DANGER = ("#C53030", "#FDECEC")
SARCELLE = ("#0F766E", "#E3F4F2")
INDIGO = ("#4C51BF", "#EEF0FD")
ARDOISE = ("#475569", "#EEF2F6")

PASTILLE_ROLE = {
    "Consultant": PRIMAIRE,
    "Membre MCO": SUCCES,
    "Administrateur": INDIGO,
}


def couleurs_pastille(couleurs):
    """(texte, fond doux) -> valeur à stocker dans la cellule : (fond, texte)."""
    texte, fond = couleurs
    return fond, texte


class PastilleDelegate(QStyledItemDelegate):
    """Dessine le texte d'une cellule dans une pastille arrondie (couleurs lues dans ROLE_PASTILLE).

    Une cellule sans couleurs mémorisées est affichée normalement. Le fond de ligne (alternance, sélection) reste
    celui du thème.
    """

    HAUTEUR = 22

    def paint(self, painter, option, index):
        couleurs = index.data(ROLE_PASTILLE)
        if not couleurs:
            super().paint(painter, option, index)
            return
        fond, texte_couleur = couleurs
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        texte = opt.text
        opt.text = ""
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)   # fond de ligne uniquement

        police = QFont(opt.font)
        police.setBold(True)
        police.setPointSize(max(police.pointSize() - 1, 8))
        largeur = min(QFontMetrics(police).horizontalAdvance(texte) + 24, max(option.rect.width() - 12, 24))
        zone = QRect(0, 0, largeur, self.HAUTEUR)
        zone.moveCenter(option.rect.center())

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(fond))
        painter.drawRoundedRect(zone, self.HAUTEUR / 2, self.HAUTEUR / 2)
        painter.setFont(police)
        painter.setPen(QColor(texte_couleur))
        painter.drawText(zone, Qt.AlignCenter, texte)
        painter.restore()


def creer_tuile(titre, couleurs, valeur="0"):
    """Tuile de synthèse (même aspect que les tuiles de l'écran Demandes). Retourne (cadre, label_valeur)."""
    texte, fond = couleurs
    cadre = QFrame()
    cadre.setObjectName("TuileUtilisateurs")
    cadre.setFixedHeight(62)
    cadre.setStyleSheet(f"""
        QFrame#TuileUtilisateurs {{
            background-color: {fond};
            border: 1px solid {texte};
            border-radius: 10px;
        }}
    """)
    mise_en_page = QHBoxLayout(cadre)
    mise_en_page.setContentsMargins(12, 4, 12, 4)
    mise_en_page.setSpacing(10)

    label_valeur = QLabel(str(valeur))
    label_valeur.setStyleSheet(f"color: {texte}; font-size: 28px; font-weight: bold; background: transparent;")
    label_valeur.setAlignment(Qt.AlignCenter)
    label_valeur.setMinimumWidth(56)

    label_titre = QLabel(titre)
    label_titre.setStyleSheet(f"color: {texte}; font-size: 12px; font-weight: bold; background: transparent;")
    label_titre.setWordWrap(True)

    mise_en_page.addWidget(label_valeur)
    mise_en_page.addWidget(label_titre, 1)
    return cadre, label_valeur


def creer_carte(nom_objet="CarteUtilisateurs"):
    """Cadre blanc à bordure fine et angles arrondis, comme les cartes des autres écrans."""
    carte = QFrame()
    carte.setObjectName(nom_objet)
    carte.setStyleSheet(f"""
        QFrame#{nom_objet} {{
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 10px;
        }}
    """)
    return carte
