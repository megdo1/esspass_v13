"""Widgets réutilisables : combo sans molette, popup de filtre des tableaux."""

from PyQt5.QtWidgets import QComboBox
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QLineEdit, QCheckBox, QVBoxLayout, QHBoxLayout, QScrollArea, QPushButton, QDialog
from PyQt5 import QtCore


class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event):
        event.ignore()  # empêche le changement de valeur avec la molette


class PopupFiltre(QDialog):
    def __init__(self, uniques, etat_coches, parent=None):
        super().__init__(parent)
        self.uniques = uniques  # toutes les valeurs de la colonne
        self.etat_coches = etat_coches  # dict valeur -> bool
        self.filtered = uniques.copy()  # valeurs visibles après recherche
        self.setWindowFlags(QtCore.Qt.Popup)
        self.setMinimumWidth(300)

        self.layout = QVBoxLayout(self)
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("Recherche…")
        self.recherche.textChanged.connect(self.updateCheckboxes)
        self.layout.addWidget(self.recherche)

        self.checkbox_selectall = QCheckBox("Tout sélectionner")
        self.checkbox_selectall.setChecked(all(self.etat_coches.get(val, True) for val in self.uniques))
        self.checkbox_selectall.stateChanged.connect(self.selectAllChanged)
        self.layout.addWidget(self.checkbox_selectall)

        # ScrollArea pour les cases à cocher
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(50)
        self.scroll.setMaximumHeight(250)
        self.scroll_content = QtWidgets.QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)

        # Boutons Valider /Annuler
        btnbox = QHBoxLayout()
        self.ok_btn = QPushButton("Valider ")
        self.cancel_btn = QPushButton("Annuler")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        btnbox.addWidget(self.ok_btn)
        btnbox.addWidget(self.cancel_btn)
        self.layout.addLayout(btnbox)

        self.checkboxes = []
        self.updateCheckboxes()


    def updateCheckboxes(self):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            w = child.widget()
            if w is not None:
                w.deleteLater()
        self.checkboxes.clear()

        filtre = self.recherche.text().lower().strip()

        # coché puis non coché
        filtered_coches = [
            v for v in self.uniques
            if self.etat_coches.get(v, False) and filtre in v.lower()
        ]
        filtered_nonc = [
            v for v in self.uniques
            if not self.etat_coches.get(v, False) and filtre in v.lower()
        ]
        self.filtered = filtered_coches + filtered_nonc

        all_checked = all(self.etat_coches.get(val, False) for val in self.uniques)
        self.checkbox_selectall.blockSignals(True)
        if filtre:
            self.checkbox_selectall.setChecked(False)
        else:
            self.checkbox_selectall.setChecked(all_checked)
        self.checkbox_selectall.blockSignals(False)

        for valeur in self.filtered:
            # cb = QCheckBox(valeur)
            label = "Vide" if not valeur else valeur
            cb = QCheckBox(label)
            cb.blockSignals(True)
            cb.setChecked(self.etat_coches.get(valeur, False))
            cb.blockSignals(False)
            cb.stateChanged.connect(lambda etat, v=valeur: self.on_checkbox(v, etat))
            self.scroll_layout.addWidget(cb)
            self.checkboxes.append(cb)

        self.scroll_layout.addStretch()
        self.scroll_content.setMinimumWidth(220)

    def selectAllChanged(self, etat):
        coche = (etat == QtCore.Qt.Checked)
        # 1) les valeurs visibles suivent la case "Tout sélectionner"
        for valeur in self.filtered:
            self.etat_coches[valeur] = coche

        # 2) les valeurs non visibles sont à l’inverse: on les exclut
        for valeur in self.uniques:
            if valeur not in self.filtered:
                # si on coche "Tout sélectionner" sur le filtre,
                # on veut que celles qui ne matchent pas le filtre soient décochées
                self.etat_coches[valeur] = False

        # 3) mise à jour visuelle des cases affichées uniquement
        for cb in self.checkboxes:
            cb.blockSignals(True)
            cb.setChecked(coche)
            cb.blockSignals(False)

    def on_checkbox(self, valeur, etat):
        self.etat_coches[valeur] = (etat == QtCore.Qt.Checked)


def ensure_combo_has_value(combo, value_id, label):
    """Garde sélectionnée la valeur d'une demande existante absente de la liste (valeur désactivée depuis,
    ou sous-catégorie d'une autre catégorie). Sans cela, l'enregistrement de la demande l'effacerait."""
    if value_id and label and combo.findData(value_id) < 0:
        combo.addItem(f"{label} (hors liste)", value_id)
        combo.setCurrentIndex(combo.count() - 1)
