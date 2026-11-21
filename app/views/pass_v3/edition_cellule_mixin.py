"""Modification des champs d'une demande directement depuis le tableau (double-clic sur la cellule).

Le double-clic ouvre le dialogue du champ cliqué : les champs modifiables sont ceux de « Gérer la demande »
(règles dans `edition_champs.py`). Sur un champ calculé ou issu du mail, une info-bulle donne la raison. Le détail
d'une demande s'ouvre par le bouton 👁. L'enregistrement utilise `update_demande` avec le verrou optimiste
(`updated_at` lu à l'ouverture) ; le droit est revérifié côté données.
"""

import logging

from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QDialog, QToolTip

from app.data.errors import ConflitModificationError
from app.utils.ui_helpers import show_error, show_warning
from app.views.pass_v3 import edition_champs as regles

logger = logging.getLogger(__name__)


class EditionCelluleMixin:
    """Édition d'un champ par double-clic sur sa cellule (voir le docstring du module)."""

    def _init_edition_cellule(self):
        """À appeler une fois, après la création du tableau."""
        self.table.cellDoubleClicked.connect(self.on_cellule_double_clic)

    def _role_courant(self):
        return (getattr(self, 'user_info', None) or {}).get('role')

    def on_cellule_double_clic(self, row, col):
        if row < 0 or self.table.verticalHeaderItem(row) is None:
            return
        colonnes = getattr(self, 'colonnes_tableau', None) or []
        if col >= len(colonnes):
            return
        config = colonnes[col]
        id_demande = int(self.table.verticalHeaderItem(row).text())
        demande = self.data_manager.get_demande_by_id(id_demande)
        if not demande:
            show_error(self, "Demande introuvable", f"La demande #{id_demande} n'existe plus. Actualisez le tableau.")
            return
        modifiable, raison = regles.statut_edition(config['champ'], config['type'], demande, self._role_courant())
        if modifiable is None:      # case à cocher, pièces jointes, boutons : rien à éditer
            return
        if not modifiable:
            QToolTip.showText(QCursor.pos(), raison, self.table)
            return
        self.modifier_champ_cellule(row, col)

    def modifier_champ_cellule(self, row, col):
        # Import local : le dialogue n'est utile qu'au moment de la modification
        from app.views.pass_v3.edition_champ_dialog import EditionChampDialog

        if self.table.verticalHeaderItem(row) is None:
            return
        config = self.colonnes_tableau[col]
        champ = config['champ']
        id_demande = int(self.table.verticalHeaderItem(row).text())
        demande = self.data_manager.get_demande_by_id(id_demande)
        if not demande:
            show_error(self, "Demande introuvable", f"La demande #{id_demande} n'existe plus. Actualisez le tableau.")
            return
        role = self._role_courant()
        modifiable, raison = regles.statut_edition(champ, config['type'], demande, role)
        if not modifiable:
            show_warning(self, "Modification impossible", raison or "Ce champ n'est pas modifiable.")
            return

        dialog = EditionChampDialog(champ, config['libelle'], demande, self.data_manager, role, self)
        if dialog.exec_() != QDialog.Accepted or not dialog.donnees:
            return
        self._enregistrer_champ(id_demande, dialog.donnees, demande.get('updated_at'))

    def _enregistrer_champ(self, id_demande, donnees, version):
        try:
            ok = self.data_manager.update_demande(id_demande, donnees, expected_updated_at=version)
        except ConflitModificationError as e:
            show_warning(self, "Demande modifiée par un autre utilisateur",
                         f"{e}\n\nVotre modification n'a PAS été enregistrée. Le tableau va être actualisé ; "
                         "refaites-la si nécessaire.")
            self._recharger_tableau_en_place()
            return False
        if not ok:
            show_error(self, "Modification impossible",
                       "La modification n'a pas été enregistrée.\n\n" + (self.data_manager.last_error or ""))
            return False
        logger.info("Demande #%s modifiée depuis le tableau : %s", id_demande, ", ".join(sorted(donnees)))
        self._recharger_tableau_en_place()
        return True

    def _recharger_tableau_en_place(self):
        """Recharge en gardant l'ordre affiché, la position de défilement et la ligne courante.
        (La priorité, calculée par la base, peut changer ; les filtres et cases cochées sont restaurés.)"""
        ids_ordre = []
        for r in range(self.table.rowCount()):
            entete = self.table.verticalHeaderItem(r)
            if entete is not None:
                try:
                    ids_ordre.append(int(entete.text()))
                except ValueError:
                    pass
        defilement = self.table.verticalScrollBar().value()
        self.load_demandes_table(ids_tri=ids_ordre or None)
        self.table.verticalScrollBar().setValue(defilement)
