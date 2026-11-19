"""Administration des collectes : liste et suppression des MÉTADONNÉES de collectes (Administrateur).

Règles : seul l'Administrateur peut lister/supprimer ; les demandes, mails et pièces jointes ne sont jamais
touchés ; les deux tables (metadonnees_collecte, collecte_demandes) sont nettoyées dans une transaction.
"""

import pytest
from conftest import definir_role


def _collecte(dm, date, nouvelles=0, mails=0, lanceur=None):
    dm.update_strict(
        "INSERT INTO metadonnees_collecte (id_utilisateur_lanceur, date_collecte, nb_nouvelles_demandes, "
        "nb_emails_traites, nb_total_demandes) VALUES (?, ?, ?, ?, 0)", (lanceur, date, nouvelles, mails))
    return dm.query_strict("SELECT MAX(id_collecte) FROM metadonnees_collecte")[0][0]


def _demande_liee(dm, id_collecte):
    dm.update_strict("INSERT INTO demandes (libelle, id_etat) VALUES ('d', 1)")
    id_demande = dm.query_strict("SELECT MAX(id_demande) FROM demandes")[0][0]
    dm.update_strict("INSERT INTO collecte_demandes (id_collecte, id_demande) VALUES (?, ?)",
                     (id_collecte, id_demande))
    return id_demande


@pytest.fixture
def jeu(dm):
    """3 collectes : 1 réussie (2 demandes), 1 ratée (0 demande, 5 mails traités), 1 ratée plus récente."""
    c1 = _collecte(dm, "2025-01-01 08:00:00", nouvelles=2, mails=2, lanceur=1)
    d1, d2 = _demande_liee(dm, c1), _demande_liee(dm, c1)
    c2 = _collecte(dm, "2025-01-02 08:00:00", nouvelles=0, mails=5, lanceur=1)
    c3 = _collecte(dm, "2025-01-03 08:00:00", nouvelles=0, mails=1)
    return {"c1": c1, "c2": c2, "c3": c3, "demandes": [d1, d2]}


def _nb(dm, table):
    return dm.query_strict(f"SELECT COUNT(*) FROM {table}")[0][0]


# --------------------------------------------------------------------- liste
def test_liste_triee_de_la_plus_recente_et_avec_statistiques(dm, jeu):
    liste = dm.get_collectes_pour_admin()
    assert [c["id_collecte"] for c in liste] == [jeu["c3"], jeu["c2"], jeu["c1"]]
    reussie = liste[2]
    assert (reussie["nb_nouvelles"], reussie["nb_liees"], reussie["nb_emails_traites"]) == (2, 2, 2)
    assert reussie["lanceur"] == "Dupont Jean"
    ratee = liste[1]
    assert (ratee["nb_nouvelles"], ratee["nb_liees"], ratee["nb_emails_traites"]) == (0, 0, 5)
    assert liste[0]["lanceur"] == "Automatique"                       # aucun lanceur enregistré


def test_liste_respecte_la_limite(dm, jeu):
    assert len(dm.get_collectes_pour_admin(limit=2)) == 2


def test_liste_vide_sans_collecte(dm):
    assert dm.get_collectes_pour_admin() == []


@pytest.mark.parametrize("role", ["Consultant", "Membre MCO", None])
def test_liste_reservee_a_l_administrateur(dm, jeu, role):
    definir_role(dm, role)
    assert dm.get_collectes_pour_admin() == []
    assert "Droits insuffisants" in dm.last_error


# --------------------------------------------------------------------- suppression
def test_suppression_ne_touche_que_les_metadonnees(dm, jeu):
    demandes_avant = _nb(dm, "demandes")
    res = dm.supprimer_collectes([jeu["c1"], jeu["c2"]])
    assert res["ok"] is True
    assert (res["collectes"], res["liens"]) == (2, 2)
    # métadonnées supprimées
    assert [c["id_collecte"] for c in dm.get_collectes_pour_admin()] == [jeu["c3"]]
    assert _nb(dm, "collecte_demandes") == 0
    # AUCUNE demande supprimée
    assert _nb(dm, "demandes") == demandes_avant == 2
    for id_demande in jeu["demandes"]:
        assert dm.get_demande_by_id(id_demande) is not None


def test_suppression_d_une_collecte_sans_demande_laisse_les_autres(dm, jeu):
    res = dm.supprimer_collectes([jeu["c2"]])
    assert (res["ok"], res["collectes"], res["liens"]) == (True, 1, 0)
    assert _nb(dm, "metadonnees_collecte") == 2
    assert _nb(dm, "collecte_demandes") == 2                         # liens de c1 intacts


def test_identifiants_en_double_ou_en_texte_acceptes(dm, jeu):
    res = dm.supprimer_collectes([str(jeu["c3"]), jeu["c3"]])
    assert res["ok"] and res["collectes"] == 1


def test_identifiant_inexistant_ne_supprime_rien(dm, jeu):
    res = dm.supprimer_collectes([99999])
    assert res["ok"] and res["collectes"] == 0
    assert _nb(dm, "metadonnees_collecte") == 3


@pytest.mark.parametrize("ids", [[], None, ["abc"], [None]])
def test_selection_vide_ou_invalide_refusee(dm, jeu, ids):
    res = dm.supprimer_collectes(ids if ids is not None else [])
    assert res["ok"] is False and res["message"]
    assert _nb(dm, "metadonnees_collecte") == 3


def test_selection_trop_large_refusee(dm, jeu):
    res = dm.supprimer_collectes(range(1, dm.MAX_COLLECTES_PAR_SUPPRESSION + 2))
    assert res["ok"] is False and "trop large" in res["message"]
    assert _nb(dm, "metadonnees_collecte") == 3


@pytest.mark.parametrize("role", ["Consultant", "Membre MCO", None])
def test_suppression_reservee_a_l_administrateur(dm, jeu, role):
    definir_role(dm, role)
    res = dm.supprimer_collectes([jeu["c1"], jeu["c2"], jeu["c3"]])
    assert res["ok"] is False and "Droits insuffisants" in res["message"]
    assert _nb(dm, "metadonnees_collecte") == 3 and _nb(dm, "collecte_demandes") == 2


def test_suppression_atomique_en_cas_d_erreur(dm, jeu):
    """Si la seconde suppression échoue, la première (liens) est annulée : pas d'état à moitié nettoyé."""
    dm.update_strict("ALTER TABLE metadonnees_collecte RENAME TO metadonnees_collecte_hs")
    res = dm.supprimer_collectes([jeu["c1"]])
    assert res["ok"] is False and "Suppression impossible" in res["message"]
    assert dm.last_error                                              # lu avant toute autre requête
    assert _nb(dm, "collecte_demandes") == 2                          # liens toujours là (rollback)


# --------------------------------------------------------------------- effet de rattrapage
def test_apres_suppression_la_derniere_collecte_recule(dm, jeu):
    """La prochaine collecte repart de la date de la dernière collecte restante (cœur du rattrapage)."""
    assert dm.get_last_collecte()["date_collecte"].startswith("03/01/2025")
    dm.supprimer_collectes([jeu["c2"], jeu["c3"]])
    assert dm.get_last_collecte()["date_collecte"].startswith("01/01/2025")


# --------------------------------------------------------------------- droits
def test_seul_l_administrateur_a_le_droit_gerer_collectes():
    from app.utils.auth import PERMISSIONS, has_permission
    assert has_permission("Administrateur", "gerer_collectes") is True
    assert has_permission("Membre MCO", "gerer_collectes") is False
    assert has_permission("Consultant", "gerer_collectes") is False
    assert all("gerer_collectes" in droits for droits in PERMISSIONS.values())
