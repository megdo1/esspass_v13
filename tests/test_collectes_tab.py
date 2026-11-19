"""Onglet « Collectes » de la Configuration : affichage, sélection, suppression, visibilité selon le rôle.

Nécessite PyQt5 (ignoré sinon, par exemple dans la CI qui n'installe pas Qt). Affichage hors écran.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from conftest import definir_role  # noqa: E402
from test_collectes_admin import _collecte, _demande_liee, _nb  # noqa: E402


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def jeu(dm):
    c1 = _collecte(dm, "2025-01-01 08:00:00", nouvelles=2, mails=2, lanceur=1)
    _demande_liee(dm, c1)
    _demande_liee(dm, c1)
    c2 = _collecte(dm, "2025-01-02 08:00:00", nouvelles=0, mails=5, lanceur=1)
    c3 = _collecte(dm, "2025-01-03 08:00:00", nouvelles=0, mails=1)
    return {"c1": c1, "c2": c2, "c3": c3}


@pytest.fixture
def onglet(app_qt, dm, jeu, monkeypatch):
    from app.views import collectes_tab
    messages = {"info": [], "warning": [], "error": []}
    monkeypatch.setattr(collectes_tab, "show_info", lambda parent, titre, texte: messages["info"].append(texte))
    monkeypatch.setattr(collectes_tab, "show_warning", lambda parent, titre, texte: messages["warning"].append(texte))
    monkeypatch.setattr(collectes_tab, "show_error", lambda parent, titre, texte: messages["error"].append(texte))
    tab = collectes_tab.CollectesTab(dm)
    tab.messages = messages
    return tab


def _coche(tab, ligne, coche=True):
    tab.table.item(ligne, 0).setCheckState(Qt.Checked if coche else Qt.Unchecked)


# --------------------------------------------------------------------- affichage
def test_message_precise_que_les_demandes_ne_sont_pas_supprimees(onglet):
    texte = onglet.bandeau.text()
    assert "ne supprime pas les demandes" in texte
    assert "métadonnées" in texte and "metadonnees_collecte" in texte and "collecte_demandes" in texte


def test_liste_affichee_de_la_plus_recente_a_la_plus_ancienne(onglet, jeu):
    assert onglet.table.rowCount() == 3
    ids = [int(onglet.table.item(i, 1).text()) for i in range(3)]
    assert ids == [jeu["c3"], jeu["c2"], jeu["c1"]]
    assert onglet.table.item(0, 2).text() == "03/01/2025 08:00"
    assert "Sans demande" in onglet.table.item(0, 7).text()
    assert "2 demande(s)" in onglet.table.item(2, 7).text()


def test_rien_n_est_coche_au_depart_et_suppression_desactivee(onglet):
    assert onglet.ids_selectionnes() == []
    assert not onglet.btn_supprimer.isEnabled()
    assert "0 sélectionnée" in onglet.lbl_compteur.text()


# --------------------------------------------------------------------- sélection
def test_selection_des_collectes_sans_demande(onglet, jeu):
    onglet.selectionner_sans_demande()
    assert sorted(onglet.ids_selectionnes()) == sorted([jeu["c2"], jeu["c3"]])   # pas la collecte réussie
    assert onglet.btn_supprimer.isEnabled()
    assert "2 sélectionnée" in onglet.lbl_compteur.text()


def test_tout_deselectionner(onglet):
    onglet.selectionner_sans_demande()
    onglet.tout_deselectionner()
    assert onglet.ids_selectionnes() == []
    assert not onglet.btn_supprimer.isEnabled()


def test_cocher_une_case_active_la_suppression(onglet, jeu):
    _coche(onglet, 1)
    assert onglet.ids_selectionnes() == [jeu["c2"]]
    assert onglet.btn_supprimer.isEnabled()


# --------------------------------------------------------------------- suppression
def test_suppression_confirmee(onglet, dm, jeu):
    onglet._confirmer = lambda nombre: True
    onglet.selectionner_sans_demande()
    onglet.supprimer_selection()
    assert [c["id_collecte"] for c in dm.get_collectes_pour_admin()] == [jeu["c1"]]
    assert onglet.table.rowCount() == 1                                  # liste rechargée
    assert _nb(dm, "demandes") == 2                                      # aucune demande supprimée
    message = onglet.messages["info"][0]
    assert "Aucune demande n'a été supprimée" in message
    assert "2 collecte(s) supprimée(s)" in message
    assert "01/01/2025" in message                                       # nouvelle date de départ de la collecte


def test_suppression_annulee_par_l_utilisateur(onglet, dm):
    onglet._confirmer = lambda nombre: False
    onglet.selectionner_sans_demande()
    onglet.supprimer_selection()
    assert _nb(dm, "metadonnees_collecte") == 3
    assert onglet.messages["info"] == []


def test_confirmation_recoit_le_nombre_de_collectes(onglet):
    recu = []
    onglet._confirmer = lambda nombre: recu.append(nombre) or False
    onglet.selectionner_sans_demande()
    onglet.supprimer_selection()
    assert recu == [2]


def test_suppression_sans_selection_previent_sans_rien_faire(onglet, dm):
    onglet._confirmer = lambda nombre: pytest.fail("ne doit pas demander confirmation")
    onglet.supprimer_selection()
    assert onglet.messages["warning"] and _nb(dm, "metadonnees_collecte") == 3


def test_erreur_de_base_affichee_et_rien_supprime(onglet, dm):
    onglet._confirmer = lambda nombre: True
    onglet.selectionner_sans_demande()
    dm.update_strict("ALTER TABLE metadonnees_collecte RENAME TO metadonnees_collecte_hs")
    onglet.supprimer_selection()
    assert onglet.messages["error"] and "impossible" in onglet.messages["error"][0].lower()
    assert onglet.messages["info"] == []


# --------------------------------------------------------------------- visibilité de l'onglet selon le rôle
def _titres_onglets(app_qt, dm, monkeypatch):
    from app.views import pass_parametrage_view as vue
    monkeypatch.setattr(vue, "DataManager", lambda: dm)
    dm.is_current_user_actif = lambda: True
    dialogue = vue.ParametrageDialog()
    return [dialogue.tabs.tabText(i) for i in range(dialogue.tabs.count())], dialogue


def test_onglet_collectes_visible_pour_l_administrateur(app_qt, dm, jeu, monkeypatch):
    definir_role(dm, "Administrateur")
    titres, dialogue = _titres_onglets(app_qt, dm, monkeypatch)
    assert any("Collectes" in t for t in titres)
    # comme l'onglet Référentiels, il agit immédiatement : « Enregistrer / Annuler » masqués
    index = next(i for i, t in enumerate(titres) if "Collectes" in t)
    dialogue.tabs.setCurrentIndex(index)
    assert dialogue.btn_save.isHidden() and dialogue.btn_cancel.isHidden()
    dialogue.tabs.setCurrentIndex(0)
    assert not dialogue.btn_save.isHidden()


@pytest.mark.parametrize("role", ["Membre MCO", "Consultant"])
def test_onglet_collectes_absent_pour_les_autres_profils(app_qt, dm, jeu, monkeypatch, role):
    definir_role(dm, role)
    titres, _ = _titres_onglets(app_qt, dm, monkeypatch)
    assert not any("Collectes" in t for t in titres)
