"""Modification des champs depuis le tableau : règles (sans Qt) et enregistrement côté données."""

from datetime import datetime

import pytest

from conftest import definir_role
from app.data.errors import ConflitModificationError
from app.views.pass_v3 import edition_champs as r

MAIL = {"conversation_id": "AAMk123", "libelle_etat": "À étudier"}
MANUELLE = {"conversation_id": "ESPASS-0001", "libelle_etat": "Traitée"}


@pytest.mark.parametrize("champ", ["canal", "domaine", "responsable", "categorie", "sous_categorie", "nature",
                                   "impact", "urgence", "etat", "resume", "solution", "commentaire"])
def test_champs_de_gerer_modifiables(champ):
    assert r.statut_edition(champ, "texte", MAIL, "Membre MCO") == (True, "")


def test_champs_calcules_ou_issus_du_mail_non_modifiables():
    for champ, type_col in [("priorite", "priorite"), ("date_reception", "texte"), ("id_demande", "texte")]:
        ok, raison = r.statut_edition(champ, type_col, MAIL, "Administrateur")
        assert ok is False and raison
    assert r.statut_edition("pieces_jointes", "icone", MAIL, "Administrateur")[0] is None
    assert r.statut_edition("actions", "actions", MAIL, "Administrateur")[0] is None
    assert r.statut_edition("inconnu", "texte", MAIL, "Administrateur")[0] is False


def test_libelle_sujet_demandeur_seulement_demande_manuelle():
    for champ in ("libelle", "sujet", "demandeur"):
        assert r.statut_edition(champ, "texte", MAIL, "Administrateur")[0] is False
        assert r.statut_edition(champ, "texte", MANUELLE, "Administrateur")[0] is True


def test_date_traitement_seulement_si_traitee_ou_fermee():
    assert r.statut_edition("date_traitement", "texte", MAIL, "Administrateur")[0] is False
    assert r.statut_edition("date_traitement", "texte", MANUELLE, "Administrateur")[0] is True


def test_consultant_sans_droit():
    ok, raison = r.statut_edition("responsable", "texte", MAIL, "Consultant")
    assert ok is False and "droit" in raison
    assert r.statut_edition("responsable", "texte", MAIL, None)[0] is False


def test_etats_proposes_archivee_reservee_admin():
    etats = ["À étudier", "Archivée", "Traitée"]
    assert "Archivée" not in r.etats_proposes(etats, "Membre MCO")
    assert "Archivée" in r.etats_proposes(etats, "Administrateur")


def test_date_traitement_selon_etat():
    now = datetime(2026, 5, 10, 12, 0)
    assert r.donnees_date_traitement("Traitée", "2026-05-09", now) == ({"date_traitement": "2026-05-09"}, None)
    assert r.donnees_date_traitement("Fermée", "2026-05-10", now)[1] is None
    assert r.donnees_date_traitement("Traitée", "2026-06-01", now)[1]            # futur refusé
    assert r.donnees_date_traitement("Traitée", "10/05/2026", now)[1]            # format invalide
    assert r.donnees_date_traitement("À étudier", "2026-05-09", now) == ({"date_traitement": ""}, None)
    assert r.donnees_date_traitement("Archivée", "2026-05-09", now) == ({}, None)


# ---------------------------------------------------------------- enregistrement (couche données)
def _creer(dm):
    return dm.create_demande({"libelle": "L", "sujet": "S", "resume": "R", "demandeur": "d@x.fr",
                              "id_canal": 1, "id_domaine": 1, "id_categorie": 1, "id_etat": 1})


def test_modifier_un_champ_ne_touche_pas_aux_autres(dm):
    id_d = _creer(dm)
    avant = dm.get_demande_by_id(id_d)
    assert dm.update_demande(id_d, {"id_canal": 2, "commentaire": "ok"}, expected_updated_at=avant["updated_at"])
    apres = dm.get_demande_by_id(id_d)
    assert apres["id_canal"] == 2 and apres["commentaire"] == "ok"
    assert apres["resume"] == "R" and apres["id_domaine"] == 1 and apres["id_etat"] == 1


def test_version_perimee_leve_conflit_et_rien_n_est_ecrit(dm):
    id_d = _creer(dm)
    with pytest.raises(ConflitModificationError):
        dm.update_demande(id_d, {"id_canal": 2}, expected_updated_at="2000-01-01 00:00:00")
    assert dm.get_demande_by_id(id_d)["id_canal"] == 1


def test_consultant_refuse_cote_donnees(dm):
    id_d = _creer(dm)
    definir_role(dm, "Consultant")
    assert dm.update_demande(id_d, {"id_canal": 2}) is False
    assert dm.get_demande_by_id(id_d)["id_canal"] == 1


def test_categorie_et_sous_categorie_ensemble(dm):
    id_d = _creer(dm)
    assert dm.update_demande(id_d, {"id_categorie": 2, "id_sous_categorie": None})
    d = dm.get_demande_by_id(id_d)
    assert d["id_categorie"] == 2 and d["id_sous_categorie"] is None
