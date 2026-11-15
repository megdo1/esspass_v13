"""Indicateurs de période (StatsMixin) : règles métier de CLAUDE.md.

réalisées = Traitée + Fermée ; en cours = À étudier + En cours de traitement ;
hors calcul = Archivée, Annulée, Hors assistance, Non applicable (exclus du total, du taux et du délai).
"""

import pytest

DEBUT, FIN = "2025-01-01", "2025-01-31"


@pytest.fixture
def stats_dm(dm):
    """DataManager avec des états métier réels et un jeu de demandes connu."""
    for libelle in ("Traitée", "Fermée", "À étudier", "En cours de traitement", "Archivée", "Annulée",
                    "Hors assistance", "Non applicable"):
        dm.update_strict("INSERT INTO etats (libelle_etat) VALUES (?)", (libelle,))
    return dm


def _etat(dm, libelle):
    return dm.query_strict("SELECT id_etat FROM etats WHERE libelle_etat = ?", (libelle,))[0][0]


def _demande(dm, etat, recu, traite=None, responsable=None):
    dm.update_strict(
        "INSERT INTO demandes (id_etat, date_reception, date_traitement, id_responsable) VALUES (?, ?, ?, ?)",
        (_etat(dm, etat), recu, traite, responsable))


def _jeu_nominal(dm):
    _demande(dm, "Traitée", "2025-01-02", "2025-01-04")          # délai 2 j
    _demande(dm, "Fermée", "2025-01-10", "2025-01-11")           # délai 1 j
    _demande(dm, "À étudier", "2025-01-15")
    _demande(dm, "En cours de traitement", "2025-01-16")
    _demande(dm, "Archivée", "2025-01-17")                       # hors calcul
    _demande(dm, "Annulée", "2025-01-18")                        # hors calcul
    _demande(dm, "Traitée", "2025-02-05", "2025-02-06")          # hors période


def test_metriques_nominales(stats_dm):
    _jeu_nominal(stats_dm)
    m = stats_dm.get_metriques_periode(DEBUT, FIN)
    assert m["total"] == 4                     # Archivée/Annulée exclues
    assert m["realisees"] == 2
    assert m["a_etudier"] == 1
    assert m["en_cours_traitement"] == 1
    assert m["en_cours"] == 2
    assert m["hors_calcul"] == 2
    assert m["taux"] == 50.0
    assert m["delai_moyen"] == 1.5             # (2 + 1) / 2


def test_hors_calcul_exclus_du_taux_et_du_delai(stats_dm):
    _jeu_nominal(stats_dm)
    # une demande Archivée avec un très long délai ne doit pas fausser le délai moyen
    _demande(stats_dm, "Archivée", "2025-01-03", "2025-01-30")
    m = stats_dm.get_metriques_periode(DEBUT, FIN)
    assert m["delai_moyen"] == 1.5
    assert m["total"] == 4
    assert m["hors_calcul"] == 3


def test_delai_ignore_traitement_anterieur_a_la_reception(stats_dm):
    _jeu_nominal(stats_dm)
    _demande(stats_dm, "Traitée", "2025-01-20", "2025-01-19")    # date incohérente
    m = stats_dm.get_metriques_periode(DEBUT, FIN)
    assert m["total"] == 5 and m["realisees"] == 3
    assert m["taux"] == 60.0
    assert m["delai_moyen"] == 1.5             # la ligne incohérente est exclue du délai


def test_bornes_de_periode_incluses(stats_dm):
    _demande(stats_dm, "À étudier", "2025-01-01")
    _demande(stats_dm, "À étudier", "2025-01-31")
    _demande(stats_dm, "À étudier", "2024-12-31")
    _demande(stats_dm, "À étudier", "2025-02-01")
    assert stats_dm.get_metriques_periode(DEBUT, FIN)["total"] == 2


def test_periode_sans_demande(stats_dm):
    m = stats_dm.get_metriques_periode(DEBUT, FIN)
    assert m["total"] == 0 and m["taux"] == 0.0 and m["delai_moyen"] is None


def test_metriques_en_erreur_renvoie_none(stats_dm):
    stats_dm.update_strict("DROP TABLE etats")
    assert stats_dm.get_metriques_periode(DEBUT, FIN) is None


# --------------------------------------------------------------------- mes demandes (bug connu corrigé)
def test_mes_demandes_accepte_id_dict_ou_none(stats_dm):
    _demande(stats_dm, "À étudier", "2025-01-02", responsable=1)
    _demande(stats_dm, "En cours de traitement", "2025-01-03", responsable=1)
    _demande(stats_dm, "Traitée", "2025-01-04", "2025-01-05", responsable=1)   # non comptée
    _demande(stats_dm, "À étudier", "2025-01-06", responsable=2)               # autre responsable
    assert stats_dm.get_mes_demandes(1) == 2
    assert stats_dm.get_mes_demandes({"id": 1}) == 2
    assert stats_dm.get_mes_demandes() == 2          # utilisateur connecté simulé (id 1)


def test_mes_demandes_utilisateur_inconnu(stats_dm):
    from conftest import definir_role
    definir_role(stats_dm, None)
    assert stats_dm.get_mes_demandes() == 0


def test_dashboard_stats_cles(stats_dm):
    assert set(stats_dm.get_dashboard_stats()) == {"recentes", "non_affectees", "a_etudier", "mes_demandes"}
