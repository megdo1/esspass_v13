"""Onglet « Référentiels » : l'administrateur gère lui-même les listes de valeurs
(canaux, domaines, catégories, sous-catégories, natures) et consulte les listes fixées par l'application
(états, impacts, urgences).

Les modifications sont enregistrées immédiatement en base (pas de bouton « Enregistrer »).
"""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from app.data.mixins.referentiels_admin_mixin import LIBELLE_MAX, REFERENTIELS

logger = logging.getLogger(__name__)

COULEUR_INACTIF = "#94A3B8"


class ValeurDialog(QDialog):
    """Saisie du libellé d'une valeur (et de sa catégorie pour une sous-catégorie)."""

    def __init__(self, titre, libelle="", categories=None, categorie_id=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(titre)
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.combo_categorie = None
        if categories is not None:
            self.combo_categorie = QComboBox()
            self.combo_categorie.addItem("", None)
            for cid, clib in categories:
                self.combo_categorie.addItem(clib, cid)
            idx = self.combo_categorie.findData(categorie_id)
            self.combo_categorie.setCurrentIndex(idx if idx >= 0 else 0)
            self.combo_categorie.currentIndexChanged.connect(self._maj_ok)
            form.addRow("Catégorie :", self.combo_categorie)
        self.edit = QLineEdit(libelle)
        self.edit.setMaxLength(LIBELLE_MAX)
        self.edit.setPlaceholderText("Libellé")
        self.edit.textChanged.connect(self._maj_ok)
        self.edit.returnPressed.connect(self._valider)
        form.addRow("Libellé :", self.edit)
        layout.addLayout(form)
        boutons = QHBoxLayout()
        boutons.addStretch()
        btn_annuler = QPushButton("Annuler")
        btn_annuler.clicked.connect(self.reject)
        self.btn_ok = QPushButton("Valider")
        self.btn_ok.setDefault(True)
        self.btn_ok.setStyleSheet("QPushButton { background: #1F4E9C; color: white; border: none; } "
                                  "QPushButton:hover { background: #1A4286; } "
                                  "QPushButton:disabled { background: #E2E8F0; color: #94A3B8; }")
        self.btn_ok.clicked.connect(self._valider)
        boutons.addWidget(btn_annuler)
        boutons.addWidget(self.btn_ok)
        layout.addLayout(boutons)
        self._maj_ok()
        self.edit.setFocus()
        self.edit.selectAll()

    def _maj_ok(self, *_):
        ok = bool(self.edit.text().strip())
        if self.combo_categorie is not None:
            ok = ok and self.combo_categorie.currentData() is not None
        self.btn_ok.setEnabled(ok)

    def _valider(self):
        if self.btn_ok.isEnabled():
            self.accept()

    def valeur(self):
        parent_id = self.combo_categorie.currentData() if self.combo_categorie is not None else None
        return self.edit.text(), parent_id


class ReaffectationDialog(QDialog):
    """Choix de la valeur de remplacement avant suppression d'une valeur utilisée."""

    def __init__(self, libelle, nb_demandes, choix, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Réaffecter les demandes")
        self.setMinimumWidth(480)
        layout = QVBoxLayout(self)
        info = QLabel(f"<b>{nb_demandes} demande(s)</b> utilisent « {libelle} ».<br>"
                      f"Choisissez la valeur qui la remplacera : ces demandes seront réaffectées, "
                      f"puis « {libelle} » sera supprimé.")
        info.setWordWrap(True)
        layout.addWidget(info)
        self.combo = QComboBox()
        for cid, clib in choix:
            self.combo.addItem(clib, cid)
        layout.addWidget(self.combo)
        boutons = QHBoxLayout()
        boutons.addStretch()
        btn_annuler = QPushButton("Annuler")
        btn_annuler.clicked.connect(self.reject)
        btn_ok = QPushButton("Réaffecter et supprimer")
        btn_ok.setStyleSheet("QPushButton { background: #C53030; color: white; border: none; } "
                             "QPushButton:hover { background: #9B2C2C; }")
        btn_ok.clicked.connect(self.accept)
        boutons.addWidget(btn_annuler)
        boutons.addWidget(btn_ok)
        layout.addLayout(boutons)

    def choix(self):
        return self.combo.currentData()


class SuppressionDialog(QDialog):
    """Que faire d'une valeur déjà utilisée : la désactiver, ou réaffecter ses demandes puis la supprimer.

    Fenêtre dédiée (et non QMessageBox) : sa largeur s'adapte toujours aux libellés des boutons.
    """

    DESACTIVER = "desactiver"
    REAFFECTER = "reaffecter"

    def __init__(self, message, details, peut_desactiver, peut_reaffecter, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Suppression impossible directement")
        self.setMinimumWidth(640)
        self.choix = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(12)
        titre = QLabel(message)
        titre.setWordWrap(True)
        police = QFont(); police.setPointSize(11); police.setBold(True)
        titre.setFont(police)
        layout.addWidget(titre)
        info = QLabel(details)
        info.setWordWrap(True)
        info.setStyleSheet("color: #475569;")
        layout.addWidget(info)

        boutons = QHBoxLayout()
        boutons.setSpacing(10)
        boutons.addStretch()
        self.btn_annuler = QPushButton("Annuler")
        self.btn_annuler.clicked.connect(self.reject)
        boutons.addWidget(self.btn_annuler)
        self.btn_desactiver = self.btn_reaffecter = None
        if peut_desactiver:
            self.btn_desactiver = QPushButton("🚫 Désactiver")
            self.btn_desactiver.clicked.connect(lambda: self._choisir(self.DESACTIVER))
            boutons.addWidget(self.btn_desactiver)
        if peut_reaffecter:
            self.btn_reaffecter = QPushButton("🔁 Réaffecter puis supprimer…")
            self.btn_reaffecter.setStyleSheet("QPushButton { color: #C53030; border-color: #F5C2C2; } "
                                              "QPushButton:hover { background: #FDECEC; border-color: #C53030; }")
            self.btn_reaffecter.clicked.connect(lambda: self._choisir(self.REAFFECTER))
            boutons.addWidget(self.btn_reaffecter)
        for b in (self.btn_annuler, self.btn_desactiver, self.btn_reaffecter):
            if b is not None:
                b.setMinimumWidth(b.sizeHint().width() + 24)   # jamais tronqué, quel que soit le libellé
        layout.addLayout(boutons)
        self.adjustSize()

    def _choisir(self, choix):
        self.choix = choix
        self.accept()


class ReferentielsTab(QWidget):
    """Gestion des listes de valeurs (référentiels)."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.key = None
        self.items = []
        self._init_ui()
        self.liste.setCurrentRow(0)

    # ------------------------------------------------------------------ construction
    def _init_ui(self):
        racine = QVBoxLayout(self)
        racine.setContentsMargins(15, 15, 15, 15)
        racine.setSpacing(12)

        bandeau = QLabel("ℹ️ Les modifications faites dans cet onglet sont <b>enregistrées immédiatement</b>. "
                         "Elles sont prises en compte tout de suite sur ce poste ; les autres utilisateurs les verront "
                         "au prochain démarrage de l'application. Une valeur déjà utilisée n'est jamais supprimée "
                         "sans réaffectation : elle peut être <b>désactivée</b> (elle n'est plus proposée mais reste "
                         "visible sur les demandes existantes).")
        bandeau.setWordWrap(True)
        bandeau.setStyleSheet("background: #E8EEF9; color: #143468; border-radius: 8px; padding: 10px 12px;")
        racine.addWidget(bandeau)

        corps = QHBoxLayout()
        corps.setSpacing(15)
        racine.addLayout(corps, 1)

        # --- colonne de gauche : liste des référentiels
        self.liste = QListWidget()
        self.liste.setFixedWidth(220)
        self.liste.setStyleSheet("QListWidget::item { padding: 10px 8px; }")
        for key, meta in REFERENTIELS.items():
            cadenas = "" if meta["modifiable"] else "   🔒"
            it = QListWidgetItem(f"{meta['icone']}  {meta['titre']}{cadenas}")
            it.setData(Qt.UserRole, key)
            if not meta["modifiable"]:
                it.setToolTip("Liste fixée par l'application (consultation seule)")
            self.liste.addItem(it)
        self.liste.currentRowChanged.connect(self._on_select_referentiel)
        corps.addWidget(self.liste)

        # --- colonne de droite
        droite = QVBoxLayout()
        droite.setSpacing(8)
        corps.addLayout(droite, 1)

        self.titre = QLabel()
        police = QFont(); police.setPointSize(14); police.setBold(True)
        self.titre.setFont(police)
        droite.addWidget(self.titre)
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setStyleSheet("color: #64748B;")
        droite.addWidget(self.description)
        self.avertissement = QLabel()
        self.avertissement.setWordWrap(True)
        self.avertissement.setStyleSheet("background: #FDF1E3; color: #92400E; border-radius: 8px; padding: 8px 12px;")
        droite.addWidget(self.avertissement)

        filtres = QHBoxLayout()
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText("🔎 Rechercher dans la liste…")
        self.recherche.setClearButtonEnabled(True)
        self.recherche.textChanged.connect(self._remplir_tableau)
        filtres.addWidget(self.recherche, 1)
        self.filtre_categorie = QComboBox()
        self.filtre_categorie.setMinimumWidth(220)
        self.filtre_categorie.currentIndexChanged.connect(self._remplir_tableau)
        filtres.addWidget(self.filtre_categorie)
        self.cb_inactifs = QCheckBox("Afficher les valeurs inactives")
        self.cb_inactifs.setChecked(True)
        self.cb_inactifs.stateChanged.connect(self._remplir_tableau)
        filtres.addWidget(self.cb_inactifs)
        droite.addLayout(filtres)

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._maj_boutons)
        self.table.itemDoubleClicked.connect(lambda *_: self._on_rename())
        droite.addWidget(self.table, 1)

        self.compteur = QLabel()
        self.compteur.setStyleSheet("color: #64748B; font-size: 12px;")
        droite.addWidget(self.compteur)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("➕ Ajouter")
        self.btn_add.setStyleSheet("QPushButton { background: #1F4E9C; color: white; border: none; } "
                                   "QPushButton:hover { background: #1A4286; } "
                                   "QPushButton:disabled { background: #E2E8F0; color: #94A3B8; }")
        self.btn_add.clicked.connect(self._on_add)
        self.btn_rename = QPushButton("✏️ Renommer")
        self.btn_rename.clicked.connect(self._on_rename)
        self.btn_toggle = QPushButton("🚫 Désactiver")
        self.btn_toggle.clicked.connect(self._on_toggle)
        self.btn_delete = QPushButton("🗑️ Supprimer")
        self.btn_delete.setStyleSheet("QPushButton { color: #C53030; border-color: #F5C2C2; } "
                                      "QPushButton:hover { background: #FDECEC; border-color: #C53030; } "
                                      "QPushButton:disabled { color: #94A3B8; border-color: #E2E8F0; background: #F1F5F9; }")
        self.btn_delete.clicked.connect(self._on_delete)
        for b in (self.btn_add, self.btn_rename, self.btn_toggle, self.btn_delete):
            actions.addWidget(b)
        actions.addStretch()
        droite.addLayout(actions)

        self.statut = QLabel()
        self.statut.setWordWrap(True)
        droite.addWidget(self.statut)

    # ------------------------------------------------------------------ affichage
    @property
    def meta(self):
        return REFERENTIELS[self.key]

    def _on_select_referentiel(self, row):
        if row < 0:
            return
        self.key = self.liste.item(row).data(Qt.UserRole)
        meta = self.meta
        self.titre.setText(f"{meta['icone']}  {meta['titre']}")
        self.description.setText(meta["description"])
        self.avertissement.setVisible(not meta["modifiable"])
        self.avertissement.setText("🔒 " + meta.get("raison", "") if not meta["modifiable"] else "")
        self.statut.clear()
        self.recherche.clear()
        # filtre par catégorie (sous-catégories uniquement)
        self.filtre_categorie.blockSignals(True)
        self.filtre_categorie.clear()
        self.filtre_categorie.setVisible(bool(meta.get("parent")))
        if meta.get("parent"):
            self.filtre_categorie.addItem("Toutes les catégories", None)
            for cat in self.dm.get_referentiel_items("categories"):
                self.filtre_categorie.addItem(cat["libelle"], cat["id"])
        self.filtre_categorie.blockSignals(False)
        self.table.setRowCount(0)   # ne pas reporter la sélection de la liste précédente
        self.refresh()

    def refresh(self, garder_id=None):
        """Recharge les valeurs depuis la base."""
        self.items = self.dm.get_referentiel_items(self.key, include_inactive=True)
        self._remplir_tableau(garder_id=garder_id)

    def _colonnes(self):
        meta = self.meta
        cols = [("Libellé", lambda i: ("🔒 " if i["protege"] and meta["modifiable"] else "") + i["libelle"])]
        if meta.get("parent"):
            cols.append(("Catégorie", lambda i: i["parent_libelle"] or ""))
        if meta.get("niveau"):
            cols.append(("Niveau", lambda i: str(i["niveau"])))
        cols.append(("Statut", lambda i: "✅ Actif" if i["actif"] else "⏸ Inactif"))
        if self.key == "categories":
            cols.append(("Sous-catégories", lambda i: str(i["nb_enfants"])))
        cols.append(("Demandes liées", lambda i: str(i["nb_demandes"])))
        return cols

    def _items_filtres(self):
        texte = self.recherche.text().strip().casefold()
        cat = self.filtre_categorie.currentData() if self.meta.get("parent") else None
        out = []
        for i in self.items:
            if not self.cb_inactifs.isChecked() and not i["actif"]:
                continue
            if texte and texte not in i["libelle"].casefold() and texte not in (i["parent_libelle"] or "").casefold():
                continue
            if cat is not None and i["parent_id"] != cat:
                continue
            out.append(i)
        return out

    def _remplir_tableau(self, *_, garder_id=None):
        if self.key is None:
            return
        if garder_id is None:
            sel = self._selection()
            garder_id = sel["id"] if sel else None
        visibles = self._items_filtres()
        cols = self._colonnes()
        self.table.setSortingEnabled(False)
        self.table.clear()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels([c[0] for c in cols])
        self.table.setRowCount(len(visibles))
        ligne_a_selectionner = -1
        for r, it in enumerate(visibles):
            for c, (_, getter) in enumerate(cols):
                cell = QTableWidgetItem(getter(it))
                if c == 0:
                    cell.setData(Qt.UserRole, it["id"])
                    if it["protege"] and self.meta["modifiable"]:
                        cell.setToolTip("Valeur utilisée par l'application : elle ne peut être ni renommée, "
                                        "ni désactivée, ni supprimée.")
                if c > 0 and cols[c][0] in ("Statut", "Niveau", "Sous-catégories", "Demandes liées"):
                    cell.setTextAlignment(Qt.AlignCenter)
                if not it["actif"]:
                    cell.setForeground(QColor(COULEUR_INACTIF))
                    f = cell.font(); f.setItalic(True); cell.setFont(f)
                self.table.setItem(r, c, cell)
            if it["id"] == garder_id:
                ligne_a_selectionner = r
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in range(1, len(cols)):
            header.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        if ligne_a_selectionner >= 0:
            self.table.selectRow(ligne_a_selectionner)
        nb_inactifs = sum(1 for i in self.items if not i["actif"])
        self.compteur.setText(f"{len(visibles)} valeur(s) affichée(s) sur {len(self.items)}"
                              + (f" — dont {nb_inactifs} inactive(s)" if nb_inactifs else ""))
        self._maj_boutons()

    def _selection(self):
        lignes = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not lignes:
            return None
        cell = self.table.item(lignes[0].row(), 0)
        ident = cell.data(Qt.UserRole) if cell else None
        return next((i for i in self.items if i["id"] == ident), None)

    def _maj_boutons(self):
        if self.key is None:
            return
        modifiable = self.meta["modifiable"]
        it = self._selection()
        self.btn_add.setEnabled(modifiable)
        editable = modifiable and it is not None and not it["protege"]
        self.btn_rename.setEnabled(editable)
        self.btn_delete.setEnabled(editable)
        self.btn_toggle.setEnabled(editable)
        self.btn_toggle.setText("✅ Réactiver" if (it is not None and not it["actif"]) else "🚫 Désactiver")
        if modifiable and it is not None and it["protege"]:
            self.statut.setStyleSheet("color: #92400E;")
            self.statut.setText("🔒 Cette valeur est utilisée par l'application : elle ne peut pas être modifiée.")

    # ------------------------------------------------------------------ retour utilisateur
    def _retour(self, ok, message, garder_id=None):
        if ok:
            self.statut.setStyleSheet("color: #276749; font-weight: 600;")
            self.statut.setText("✅ " + message)
        else:
            self.statut.setStyleSheet("color: #9B2C2C; font-weight: 600;")
            self.statut.setText("⚠️ " + message)
            QMessageBox.warning(self, "Action impossible", message)
        self.refresh(garder_id=garder_id)

    def _categories_actives(self):
        return [(c["id"], c["libelle"]) for c in self.dm.get_referentiel_items("categories") if c["actif"]]

    # ------------------------------------------------------------------ actions
    def _on_add(self):
        if not self.meta["modifiable"]:
            return
        meta = self.meta
        if meta.get("parent"):
            sel = self._selection()
            defaut = self.filtre_categorie.currentData() or (sel["parent_id"] if sel else None)
            dlg = ValeurDialog(f"Ajouter une valeur — {meta['titre']}", categories=self._categories_actives(),
                               categorie_id=defaut, parent=self)
        else:
            dlg = ValeurDialog(f"Ajouter une valeur — {meta['titre']}", parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        libelle, parent_id = dlg.valeur()
        ok, msg = self.dm.add_referentiel_item(self.key, libelle, parent_id)
        self._retour(ok, msg)

    def _on_rename(self):
        it = self._selection()
        if not self.meta["modifiable"] or it is None or it["protege"]:
            return
        dlg = ValeurDialog(f"Renommer — {self.meta['titre']}", libelle=it["libelle"], parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        libelle, _ = dlg.valeur()
        ok, msg = self.dm.rename_referentiel_item(self.key, it["id"], libelle)
        self._retour(ok, msg, garder_id=it["id"])

    def _on_toggle(self):
        it = self._selection()
        if it is None or it["protege"]:
            return
        if it["actif"]:
            rep = QMessageBox.question(
                self, "Désactiver",
                f"Désactiver « {it['libelle']} » ?\n\nIl ne sera plus proposé pour les nouvelles demandes. "
                f"Les {it['nb_demandes']} demande(s) existante(s) le conservent. Vous pourrez le réactiver à tout moment.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if rep != QMessageBox.Yes:
                return
        ok, msg = self.dm.set_referentiel_item_active(self.key, it["id"], not it["actif"])
        self._retour(ok, msg, garder_id=it["id"])

    def _on_delete(self):
        it = self._selection()
        if it is None or it["protege"]:
            return
        nb, enfants = it["nb_demandes"], it["nb_enfants"]
        if nb == 0 and enfants == 0:
            rep = QMessageBox.question(
                self, "Supprimer définitivement",
                f"Supprimer définitivement « {it['libelle']} » ?\n\nCette action est irréversible.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if rep == QMessageBox.Yes:
                ok, msg = self.dm.delete_referentiel_item(self.key, it["id"])
                self._retour(ok, msg)
            return

        raisons = []
        if enfants:
            raisons.append(f"contient {enfants} sous-catégorie(s)")
        if nb:
            raisons.append(f"est utilisé par {nb} demande(s)")
        details = ("Pour conserver l'historique, vous pouvez :\n"
                   "• le désactiver : il ne sera plus proposé mais reste visible sur les demandes existantes")
        peut_reaffecter = bool(self.meta.get("reaffectable")) and nb > 0 and enfants == 0
        if peut_reaffecter:
            details += "\n• réaffecter ses demandes vers une autre valeur, puis le supprimer"
        dlg = SuppressionDialog(f"« {it['libelle']} » " + " et ".join(raisons) + ".", details,
                                peut_desactiver=it["actif"], peut_reaffecter=peut_reaffecter, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        if dlg.choix == SuppressionDialog.DESACTIVER:
            ok, msg = self.dm.set_referentiel_item_active(self.key, it["id"], False)
            self._retour(ok, msg, garder_id=it["id"])
        elif dlg.choix == SuppressionDialog.REAFFECTER:
            self._reaffecter(it)

    def _reaffecter(self, it):
        choix = [(i["id"], (f"{i['parent_libelle']} › " if i["parent_libelle"] else "") + i["libelle"])
                 for i in self.items
                 if i["id"] != it["id"] and i["actif"] and (not self.meta.get("parent") or i["parent_id"] == it["parent_id"])]
        if not choix:
            QMessageBox.information(self, "Réaffectation impossible",
                                    "Aucune autre valeur active n'est disponible comme remplacement"
                                    + (" dans cette catégorie." if self.meta.get("parent") else "."))
            return
        dlg = ReaffectationDialog(it["libelle"], it["nb_demandes"], choix, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        ok, msg = self.dm.reassign_and_delete_referentiel_item(self.key, it["id"], dlg.choix())
        self._retour(ok, msg)
