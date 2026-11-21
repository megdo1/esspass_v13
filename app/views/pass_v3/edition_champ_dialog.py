"""Petit dialogue de modification d'un seul champ d'une demande (ouvert par le double-clic sur une cellule du tableau).

Mêmes listes et mêmes règles que « Gérer la demande » : états filtrés selon le rôle, valeur désactivée gardée
sélectionnée, sous-catégories de la catégorie choisie (par identifiant), date de traitement liée à l'état.
"""

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (QDateEdit, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
                             QTextEdit, QVBoxLayout)

from app.utils.ui_helpers import show_warning
from app.views.pass_v3 import edition_champs as regles
from app.views.pass_v3.widgets import NoScrollComboBox, ensure_combo_has_value


class EditionChampDialog(QDialog):
    def __init__(self, champ, libelle_colonne, demande, data_manager, role, parent=None):
        super().__init__(parent)
        self.champ = champ
        self.spec = regles.SPECS[champ]
        self.demande = demande
        self.dm = data_manager
        self.role = role
        self.donnees = {}
        self.setWindowTitle(f"Demande #{demande.get('id_demande')} — {libelle_colonne}")
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        titre = (demande.get('libelle') or demande.get('sujet') or '').strip()
        if titre:
            info = QLabel(titre if len(titre) <= 80 else titre[:77] + "…")
            info.setStyleSheet("color: #64748B;")
            layout.addWidget(info)
        self.form = QFormLayout()
        layout.addLayout(self.form)
        self._construire(libelle_colonne)

        boutons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        boutons.button(QDialogButtonBox.Ok).setText("Enregistrer")
        boutons.button(QDialogButtonBox.Cancel).setText("Annuler")
        boutons.accepted.connect(self._valider)
        boutons.rejected.connect(self.reject)
        layout.addWidget(boutons)

    # ------------------------------------------------------------------ construction
    def _construire(self, libelle):
        t = self.spec['type']
        if t == 'liste':
            self.combo = self._combo_reference(self.spec['ref'], self.spec['cle'])
            self.form.addRow(f"{libelle} :", self.combo)
        elif t == 'etat':
            self.combo = self._combo_reference('etats', 'id_etat', obligatoire=True)
            self.combo.currentTextChanged.connect(self._maj_date_visible)
            self.form.addRow("État :", self.combo)
            self.label_date = QLabel("Date de traitement :")
            self.date = self._champ_date()
            self.form.addRow(self.label_date, self.date)
            self._maj_date_visible()
        elif t == 'responsable':
            self.combo = NoScrollComboBox()
            self.combo.addItem("", None)
            for r in self.dm.get_responsables():
                self.combo.addItem(r['nom_complet'], r['id'])
            actuel = self.demande.get('id_responsable')
            self._selectionner(self.combo, actuel)
            ensure_combo_has_value(self.combo, actuel, self.demande.get('responsable') or f"utilisateur #{actuel}")
            self.form.addRow("Responsable :", self.combo)
        elif t == 'categorie':
            self.combo = self._combo_reference('categories', 'id_categorie')
            self.combo_sc = NoScrollComboBox()
            self.combo.currentTextChanged.connect(self._recharger_sous_categories)
            self.form.addRow("Catégorie :", self.combo)
            self.form.addRow("Sous-catégorie :", self.combo_sc)
            self._recharger_sous_categories()
        elif t == 'sous_categorie':
            self.combo = NoScrollComboBox()
            self.combo.addItem("", None)
            categorie = self.demande.get('libelle_categorie') or ''
            self._remplir_sous_categories(self.combo, categorie)
            actuel = self.demande.get('id_sous_categorie')
            self._selectionner(self.combo, actuel)
            ensure_combo_has_value(self.combo, actuel, self.dm.get_reference_label('sous_categories', actuel))
            self.form.addRow(f"Sous-catégorie ({categorie or 'sans catégorie'}) :", self.combo)
        elif t == 'date':
            self.date = self._champ_date()
            self.form.addRow("Date de traitement :", self.date)
        elif t == 'texte_long':
            self.texte = QTextEdit(str(self.demande.get(self.spec['cle']) or ''))
            self.texte.setMinimumHeight(140)
            self.form.addRow(f"{libelle} :", self.texte)
        else:  # texte_court
            self.texte = QLineEdit(str(self.demande.get(self.spec['cle']) or ''))
            self.form.addRow(f"{libelle} :", self.texte)

    def _combo_reference(self, ref, cle, obligatoire=False):
        combo = NoScrollComboBox()
        if not obligatoire:
            combo.addItem("", None)
        libelles = self.dm.get_liste_valeurs(ref)
        if ref == 'etats':
            libelles = regles.etats_proposes(libelles, self.role)
        for libelle in libelles:
            combo.addItem(libelle, self.dm.id_mapping[ref].get(libelle))
        actuel = self.demande.get(cle)
        self._selectionner(combo, actuel)
        ensure_combo_has_value(combo, actuel, self.dm.get_reference_label(ref, actuel))
        if ref == 'etats' and actuel and combo.findData(actuel) < 0:
            # État actuel non proposé (ex. « Archivée » pour un non-administrateur) : ne pas le changer en silence
            combo.addItem(self.demande.get('libelle_etat') or f"état #{actuel}", actuel)
            combo.setCurrentIndex(combo.count() - 1)
        return combo

    @staticmethod
    def _selectionner(combo, valeur_id):
        if valeur_id:
            index = combo.findData(valeur_id)
            if index >= 0:
                combo.setCurrentIndex(index)

    def _remplir_sous_categories(self, combo, categorie):
        for libelle in self.dm.sous_categories_by_categorie.get(categorie, []):
            id_sc = self.dm.sous_categories_ids_by_categorie.get(categorie, {}).get(libelle)
            combo.addItem(libelle, id_sc)

    def _recharger_sous_categories(self):
        """Changer de catégorie vide la sous-catégorie (comme dans Gérer) ; au départ on garde l'actuelle."""
        premiere_fois = not hasattr(self, '_sc_initialisee')
        self._sc_initialisee = True
        self.combo_sc.clear()
        self.combo_sc.addItem("", None)
        self._remplir_sous_categories(self.combo_sc, self.combo.currentText())
        if premiere_fois:
            actuel = self.demande.get('id_sous_categorie')
            self._selectionner(self.combo_sc, actuel)
            ensure_combo_has_value(self.combo_sc, actuel, self.dm.get_reference_label('sous_categories', actuel))

    def _champ_date(self):
        champ = QDateEdit()
        champ.setCalendarPopup(True)
        champ.setDisplayFormat("yyyy-MM-dd")
        actuelle = QDate.fromString(str(self.demande.get('date_traitement') or '')[:10], "yyyy-MM-dd")
        champ.setDate(actuelle if actuelle.isValid() else QDate.currentDate())
        return champ

    def _maj_date_visible(self):
        visible = self.combo.currentText() in regles.ETATS_AVEC_DATE
        self.label_date.setVisible(visible)
        self.date.setVisible(visible)

    # ------------------------------------------------------------------ validation
    def _valider(self):
        t, cle = self.spec['type'], self.spec['cle']
        if t in ('liste', 'responsable', 'sous_categorie'):
            donnees = {cle: self.combo.currentData()}
        elif t == 'categorie':
            donnees = {cle: self.combo.currentData(), 'id_sous_categorie': self.combo_sc.currentData()}
        elif t == 'etat':
            etat = self.combo.currentText()
            donnees = {cle: self.combo.currentData()}
            extra, erreur = regles.donnees_date_traitement(
                etat, self.date.date().toString("yyyy-MM-dd"))
            if erreur:
                show_warning(self, "Date de traitement invalide", erreur)
                return
            donnees.update(extra)
        elif t == 'date':
            etat = self.demande.get('libelle_etat')
            extra, erreur = regles.donnees_date_traitement(etat, self.date.date().toString("yyyy-MM-dd"))
            if erreur:
                show_warning(self, "Date de traitement invalide", erreur)
                return
            donnees = extra
        elif t == 'texte_long':
            donnees = {cle: self.texte.toPlainText()}
        else:
            donnees = {cle: self.texte.text().strip()}
        self.donnees = donnees
        self.accept()
