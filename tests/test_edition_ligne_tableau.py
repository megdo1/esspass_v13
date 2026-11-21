"""Modification d'un champ depuis le tableau : rafraîchissement de la seule ligne modifiée.

Nécessite PyQt5 (ignoré sinon). Affichage hors écran, base temporaire.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QCheckBox, QTableWidget, QWidget  # noqa: E402

from app.views.pass_v3.edition_cellule_mixin import EditionCelluleMixin  # noqa: E402
from app.views.pass_v3.layout_mixin import LayoutMixin  # noqa: E402
from app.views.pass_v3.table_mixin import TableMixin  # noqa: E402

COLONNES = [  # nom, libellé, champ, largeur, visible, ordre, alignement, tronquer, type
    ("id", "ID", "id_demande", 60, 1, 1, "left", 50, "texte"),
    ("resp", "Responsable", "responsable", 120, 1, 2, "left", 50, "texte"),
    ("prio", "Priorité", "priorite", 80, 1, 3, "center", 50, "priorite"),
    ("etat", "État", "etat", 100, 1, 4, "left", 50, "etat"),
]


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


class Hote(TableMixin, EditionCelluleMixin, QWidget):
    create_actions_widget = LayoutMixin.create_actions_widget

    def __init__(self, dm):
        super().__init__()
        self.data_manager = dm
        self.user_info = {"role": "Administrateur"}
        self.table = QTableWidget()
        self.cb_archives, self.cb_annulees, self.cb_realisees = QCheckBox(), QCheckBox(), QCheckBox()
        self.open_dialogs = {}
        self.rechargements = 0

    def update_info_label(self):
        pass

    def update_corner_position(self):
        pass

    def update_selection_count(self):
        pass

    def load_demandes_table(self, ids_tri=None):
        self.rechargements += 1
        return super().load_demandes_table(ids_tri=ids_tri)


@pytest.fixture
def hote(app_qt, dm):
    import sqlite3
    conn = sqlite3.connect(dm.db_path)
    conn.executemany("INSERT INTO colonnes_config VALUES (?,?,?,?,?,?,?,?,?,NULL)", COLONNES)
    conn.execute("UPDATE etats SET libelle_etat = 'Traitée' WHERE id_etat = 2")
    conn.commit()
    conn.close()
    for i in range(3):
        dm.create_demande({"libelle": f"L{i}", "sujet": "S", "resume": "R", "demandeur": "d@x.fr",
                           "id_canal": 1, "id_domaine": 1, "id_categorie": 1, "id_etat": 1})
    h = Hote(dm)
    h.load_demandes_table()
    h.rechargements = 0
    return h


def _col(h, champ):
    return [c["champ"] for c in h.colonnes_tableau].index(champ)


def test_responsable_rafraichi_sans_recharger_tout_le_tableau(hote, dm):
    row = 1
    id_d = int(hote.table.verticalHeaderItem(row).text())
    version = dm.get_demande_by_id(id_d)["updated_at"]
    assert hote._enregistrer_champ(id_d, {"id_responsable": 1}, version, row) is True
    assert hote.table.item(row, _col(hote, "responsable")).text() == "Dupont Jean"
    assert hote.rechargements == 0
    assert hote.table.rowCount() == 3


def test_priorite_recalculee_par_la_base_et_couleur(hote, dm):
    row = 0
    id_d = int(hote.table.verticalHeaderItem(row).text())
    version = dm.get_demande_by_id(id_d)["updated_at"]
    # La base de test n'a pas les triggers de production : on en simule un qui pose la priorité
    import sqlite3
    conn = sqlite3.connect(dm.db_path)
    conn.execute("CREATE TRIGGER t_prio AFTER UPDATE OF id_impact, id_urgence ON demandes BEGIN "
                 "UPDATE demandes SET priorite_calculee = 'P1' WHERE id_demande = NEW.id_demande; END")
    conn.commit()
    conn.close()
    assert hote._enregistrer_champ(id_d, {"id_impact": 1, "id_urgence": 1}, version, row)
    item = hote.table.item(row, _col(hote, "priorite"))
    assert item.text() == "P1" and item.background().color().name().lower() == "#c53030"
    assert hote.rechargements == 0


def test_etat_qui_sort_de_la_liste_recharge_tout(hote, dm):
    row = 0
    id_d = int(hote.table.verticalHeaderItem(row).text())
    version = dm.get_demande_by_id(id_d)["updated_at"]
    # « Traitée » est masquée (case « réalisées » décochée) : la ligne doit disparaître => rechargement complet
    assert hote._enregistrer_champ(id_d, {"id_etat": 2}, version, row)
    assert hote.rechargements == 1
    assert hote.table.rowCount() == 2


def test_etat_traitee_reste_affichee_si_case_cochee(hote, dm):
    hote.cb_realisees.setChecked(True)
    row = 0
    id_d = int(hote.table.verticalHeaderItem(row).text())
    version = dm.get_demande_by_id(id_d)["updated_at"]
    assert hote._enregistrer_champ(id_d, {"id_etat": 2}, version, row)
    assert hote.rechargements == 0 and hote.table.item(row, _col(hote, "etat")).text() == "Traitée"
    assert hote.table.item(row, _col(hote, "etat")).background().color().name().lower() == "#e6f4ec"


def test_une_seule_lecture_au_double_clic(hote, dm, monkeypatch):
    lectures = []
    reel = dm.get_demande_by_id
    monkeypatch.setattr(dm, "get_demande_by_id", lambda i: lectures.append(i) or reel(i))
    monkeypatch.setattr(hote, "modifier_champ_cellule",
                        lambda row, col, demande=None: lectures.append(("modif", demande is not None)))
    hote.on_cellule_double_clic(0, _col(hote, "responsable"))
    assert lectures[1:] == [("modif", True)] and len(lectures) == 2
