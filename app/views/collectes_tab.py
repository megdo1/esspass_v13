"""Onglet « Collectes » de la Configuration (Administrateur) : supprimer les collectes qui n'ont pas abouti.

Sert au rattrapage : tant qu'une collecte ratée reste enregistrée, la collecte suivante repart de sa date
et ne reprend pas les mails manqués. Supprimer ses métadonnées (tables `metadonnees_collecte` et
`collecte_demandes`) fait repartir la collecte de la dernière collecte restante.

Ne supprime JAMAIS les demandes, ni leurs mails ou pièces jointes. L'action est immédiate (pas de bouton
« Enregistrer »), après confirmation.
"""

import logging
from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.utils.ui_helpers import show_error, show_info, show_warning

logger = logging.getLogger(__name__)

COLONNES = ["", "N°", "Date de la collecte", "Lancée par", "Mails traités", "Nouvelles demandes",
            "Demandes liées", "État"]
COL_CASE, COL_ID, COL_DATE, COL_LANCEUR, COL_MAILS, COL_NOUVELLES, COL_LIEES, COL_ETAT = range(8)

MESSAGE_PORTEE = (
    "<b>Cette action ne supprime pas les demandes créées</b> (ni leurs mails, ni leurs pièces jointes) : "
    "elle supprime uniquement les <b>métadonnées des collectes</b> (tables <i>metadonnees_collecte</i> et "
    "<i>collecte_demandes</i>)."
)
MESSAGE_RATTRAPAGE = (
    "Usage : rattrapage après une collecte qui n'a pas abouti. Après suppression, la prochaine collecte "
    "repart de la date de la <b>dernière collecte restante</b> ; les mails déjà importés sont reconnus et "
    "ne sont pas dupliqués."
)
STYLE_BANDEAU = ("QLabel { background: #FEF3C7; color: #78350F; border: 1px solid #F59E0B; "
                 "border-radius: 6px; padding: 10px 12px; }")
STYLE_DANGER = ("QPushButton { color: #B91C1C; background: white; border: 1px solid #B91C1C; "
                "border-radius: 6px; padding: 6px 14px; } "
                "QPushButton:hover { background: #FEE2E2; } "
                "QPushButton:disabled { color: #94A3B8; border-color: #CBD5E1; background: #F8FAFC; }")
COULEUR_SANS_DEMANDE = "#B45309"


def _date_lisible(valeur) -> str:
    try:
        return datetime.strptime(str(valeur), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(valeur or "")


def sans_demande(collecte: dict) -> bool:
    """Collecte qui n'a créé ni rattaché aucune demande (échec, ou simplement aucun nouveau mail)."""
    return not collecte.get('nb_nouvelles') and not collecte.get('nb_liees')


class CollectesTab(QWidget):
    """Liste des collectes et suppression des collectes sélectionnées (Administrateur)."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.collectes = []          # une entrée par ligne du tableau
        self._construire()
        self.charger()

    # ------------------------------------------------------------------ interface
    def _construire(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.bandeau = QLabel(MESSAGE_PORTEE + "<br>" + MESSAGE_RATTRAPAGE)
        self.bandeau.setTextFormat(Qt.RichText)
        self.bandeau.setWordWrap(True)
        self.bandeau.setStyleSheet(STYLE_BANDEAU)
        layout.addWidget(self.bandeau)

        barre = QHBoxLayout()
        self.btn_actualiser = QPushButton("🔄 Actualiser")
        self.btn_actualiser.clicked.connect(self.charger)
        self.btn_sans_demande = QPushButton("Sélectionner les collectes sans demande créée")
        self.btn_sans_demande.clicked.connect(self.selectionner_sans_demande)
        self.btn_aucune = QPushButton("Tout désélectionner")
        self.btn_aucune.clicked.connect(self.tout_deselectionner)
        for bouton in (self.btn_actualiser, self.btn_sans_demande, self.btn_aucune):
            barre.addWidget(bouton)
        barre.addStretch()
        self.btn_supprimer = QPushButton("🗑 Supprimer la sélection")
        self.btn_supprimer.setStyleSheet(STYLE_DANGER)
        self.btn_supprimer.clicked.connect(self.supprimer_selection)
        barre.addWidget(self.btn_supprimer)
        layout.addLayout(barre)

        self.table = QTableWidget(0, len(COLONNES))
        self.table.setHorizontalHeaderLabels(COLONNES)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setAlternatingRowColors(True)
        entete = self.table.horizontalHeader()
        entete.setSectionResizeMode(QHeaderView.ResizeToContents)
        entete.setSectionResizeMode(COL_LANCEUR, QHeaderView.Stretch)
        entete.setSectionResizeMode(COL_ETAT, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._maj_compteur)
        layout.addWidget(self.table, 1)

        self.lbl_compteur = QLabel("")
        layout.addWidget(self.lbl_compteur)

    # ------------------------------------------------------------------ données
    def charger(self):
        """(Re)charge la liste depuis la base ; la sélection est perdue."""
        self.collectes = self.data_manager.get_collectes_pour_admin()
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.collectes))
        for ligne, c in enumerate(self.collectes):
            case = QTableWidgetItem()
            case.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            case.setCheckState(Qt.Unchecked)
            self.table.setItem(ligne, COL_CASE, case)
            vide = sans_demande(c)
            etat = "⚠️ Sans demande créée" if vide else f"✅ {c['nb_liees'] or c['nb_nouvelles']} demande(s) créée(s)"
            valeurs = {COL_ID: c['id_collecte'], COL_DATE: _date_lisible(c['date_collecte']),
                       COL_LANCEUR: c['lanceur'], COL_MAILS: c['nb_emails_traites'],
                       COL_NOUVELLES: c['nb_nouvelles'], COL_LIEES: c['nb_liees'], COL_ETAT: etat}
            for colonne, valeur in valeurs.items():
                item = QTableWidgetItem(str(valeur))
                item.setFlags(Qt.ItemIsEnabled)
                if colonne in (COL_ID, COL_MAILS, COL_NOUVELLES, COL_LIEES):
                    item.setTextAlignment(Qt.AlignCenter)
                if vide and colonne == COL_ETAT:
                    item.setForeground(QColor(COULEUR_SANS_DEMANDE))
                self.table.setItem(ligne, colonne, item)
        self.table.blockSignals(False)
        self._maj_compteur()
        if not self.collectes and self.data_manager.last_error:
            show_error(self, "Collectes", f"Impossible de lire les collectes :\n{self.data_manager.last_error}")

    def ids_selectionnes(self):
        return [self.collectes[i]['id_collecte'] for i in range(self.table.rowCount())
                if self.table.item(i, COL_CASE).checkState() == Qt.Checked]

    def _maj_compteur(self, *_):
        n = len(self.ids_selectionnes())
        self.lbl_compteur.setText(f"{len(self.collectes)} collecte(s) affichée(s) — {n} sélectionnée(s)")
        self.btn_supprimer.setEnabled(n > 0)

    # ------------------------------------------------------------------ actions
    def selectionner_sans_demande(self):
        self.table.blockSignals(True)
        for i, c in enumerate(self.collectes):
            self.table.item(i, COL_CASE).setCheckState(Qt.Checked if sans_demande(c) else Qt.Unchecked)
        self.table.blockSignals(False)
        self._maj_compteur()

    def tout_deselectionner(self):
        self.table.blockSignals(True)
        for i in range(self.table.rowCount()):
            self.table.item(i, COL_CASE).setCheckState(Qt.Unchecked)
        self.table.blockSignals(False)
        self._maj_compteur()

    def _confirmer(self, nombre: int) -> bool:
        """Demande confirmation (méthode isolée pour pouvoir être remplacée dans les tests)."""
        boite = QMessageBox(self)
        boite.setIcon(QMessageBox.Warning)
        boite.setWindowTitle("Supprimer des collectes")
        boite.setTextFormat(Qt.RichText)
        boite.setText(f"Supprimer <b>{nombre}</b> collecte(s) ?")
        boite.setInformativeText(MESSAGE_PORTEE + "<br><br>" + MESSAGE_RATTRAPAGE)
        btn_oui = boite.addButton("Supprimer", QMessageBox.DestructiveRole)
        btn_non = boite.addButton("Annuler", QMessageBox.RejectRole)
        boite.setDefaultButton(btn_non)
        boite.exec_()
        return boite.clickedButton() is btn_oui

    def supprimer_selection(self):
        ids = self.ids_selectionnes()
        if not ids:
            show_warning(self, "Collectes", "Cochez au moins une collecte à supprimer.")
            return
        if not self._confirmer(len(ids)):
            return
        resultat = self.data_manager.supprimer_collectes(ids)
        if not resultat['ok']:
            show_error(self, "Suppression impossible", resultat['message'])
            return
        self.charger()
        derniere = (self.data_manager.get_last_collecte() or {}).get('date_collecte', '')
        show_info(self, "Collectes supprimées",
                  f"{resultat['collectes']} collecte(s) supprimée(s) ({resultat['liens']} lien(s) "
                  "demande-collecte).\n\nAucune demande n'a été supprimée.\n\n"
                  f"Dernière collecte désormais prise en compte : {derniere}.\n"
                  "La prochaine mise à jour repartira de cette date.")
