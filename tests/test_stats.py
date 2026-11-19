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


# --------------------------------------------------------------------- tuile « non affectées » = tableau filtré sur « responsable vide »
def test_non_affectees_exclut_archivees_et_annulees(stats_dm):
    _demande(stats_dm, "À étudier", "2025-01-02")                     # sans responsable : comptée
    _demande(stats_dm, "En cours de traitement", "2025-01-03")        # comptée
    _demande(stats_dm, "Traitée", "2025-01-04", "2025-01-05")         # comptée (affichée par défaut)
    _demande(stats_dm, "Hors assistance", "2025-01-06")               # comptée (affichée par défaut)
    _demande(stats_dm, "Archivée", "2025-01-07")                      # masquée par défaut : exclue
    _demande(stats_dm, "Annulée", "2025-01-08")                       # masquée par défaut : exclue
    _demande(stats_dm, "À étudier", "2025-01-09", responsable=1)      # affectée : exclue
    assert stats_dm.get_demandes_non_affectees() == 4


def test_non_affectees_compte_une_demande_sans_etat(stats_dm):
    stats_dm.update_strict("INSERT INTO demandes (id_etat, date_reception) VALUES (NULL, '2025-01-02')")
    assert stats_dm.get_demandes_non_affectees() == 1


def test_non_affectees_coherent_avec_le_tableau_par_defaut(stats_dm):
    """La tuile doit égaler le nombre de lignes sans responsable du tableau avec ses filtres par défaut."""
    _demande(stats_dm, "À étudier", "2025-01-02")
    _demande(stats_dm, "Traitée", "2025-01-03", "2025-01-04")
    _demande(stats_dm, "Archivée", "2025-01-05")
    _demande(stats_dm, "Annulée", "2025-01-06")
    _demande(stats_dm, "En cours de traitement", "2025-01-07", responsable=1)
    tableau = stats_dm.get_demandes(limit=1000, inclure_archivees=False, inclure_annulees=False,
                                    inclure_realisees=True)
    sans_responsable = [d for d in tableau if not d["responsable"]]
    assert stats_dm.get_demandes_non_affectees() == len(sans_responsable) == 2


def test_non_affectees_en_erreur_renvoie_zero(stats_dm):
    stats_dm.update_strict("DROP TABLE etats")
    assert stats_dm.get_demandes_non_affectees() == 0


# --------------------------------------------------------------------- affichage du responsable (demandes 1495/1496 du client)
def _utilisateur(dm, nom, prenom, email=None, actif=1):
    dm.update_strict("INSERT INTO utilisateurs (nom, prenom, email, id_role, actif) VALUES (?, ?, ?, 1, ?)",
                     (nom, prenom, email, actif))
    return dm.query_strict("SELECT MAX(id_utilisateur) FROM utilisateurs")[0][0]


def _responsables_affiches(dm):
    return {d["id_demande"]: d["responsable"] for d in dm.get_demandes(limit=1000, inclure_archivees=True,
                                                                         inclure_annulees=True)}


def test_responsable_sans_nom_ni_prenom_n_est_pas_affiche_comme_non_affecte(stats_dm):
    """Cas client : demande affectée à un utilisateur dont nom et prénom sont vides."""
    sans_nom = _utilisateur(stats_dm, None, None)
    _demande(stats_dm, "Traitée", "2025-01-02", "2025-01-03", responsable=sans_nom)
    affiche = list(_responsables_affiches(stats_dm).values())[0]
    assert affiche == f"(utilisateur #{sans_nom} sans nom)"      # visible, et non vide


def test_responsable_prenom_manquant_affiche_le_nom(stats_dm):
    u = _utilisateur(stats_dm, "Dupont", None)
    _demande(stats_dm, "À étudier", "2025-01-02", responsable=u)
    assert list(_responsables_affiches(stats_dm).values())[0] == "Dupont"


def test_responsable_sans_nom_affiche_l_email(stats_dm):
    u = _utilisateur(stats_dm, None, None, email="x@y.fr")
    _demande(stats_dm, "À étudier", "2025-01-02", responsable=u)
    assert list(_responsables_affiches(stats_dm).values())[0] == "x@y.fr"


def test_responsable_supprime_est_signale(stats_dm):
    _demande(stats_dm, "À étudier", "2025-01-02", responsable=999)
    assert list(_responsables_affiches(stats_dm).values())[0] == "(utilisateur #999 introuvable)"


def test_vide_uniquement_quand_aucun_responsable(stats_dm):
    u = _utilisateur(stats_dm, "Martin", "Léa")
    _demande(stats_dm, "À étudier", "2025-01-02")                           # aucun responsable
    _demande(stats_dm, "À étudier", "2025-01-03", responsable=u)
    _demande(stats_dm, "À étudier", "2025-01-04", responsable=_utilisateur(stats_dm, None, None))
    _demande(stats_dm, "À étudier", "2025-01-05", responsable=999)
    affiches = _responsables_affiches(stats_dm)
    vides = [i for i, r in affiches.items() if not r]
    assert len(vides) == 1                                                  # = ce que compte la tuile
    assert stats_dm.get_demandes_non_affectees() == len(vides)


def test_detail_demande_et_export_utilisent_le_meme_libelle(stats_dm):
    u = _utilisateur(stats_dm, None, None)
    _demande(stats_dm, "Traitée", "2025-01-02", "2025-01-03", responsable=u)
    id_d = stats_dm.query_strict("SELECT id_demande FROM demandes")[0][0]
    attendu = f"(utilisateur #{u} sans nom)"
    assert stats_dm.get_demande_by_id(id_d)["responsable"] == attendu
    assert stats_dm.get_demandes_by_ids([id_d])[0]["nom_responsable"] == attendu


def test_liste_des_utilisateurs_ne_contient_jamais_none(stats_dm):
    _utilisateur(stats_dm, None, None)
    _utilisateur(stats_dm, "Dupont", None)
    stats_dm.reload_reference_data()
    assert None not in stats_dm.liste_valeurs["utilisateurs"]
    assert "Dupont" in stats_dm.liste_valeurs["utilisateurs"]


def _collecte(dm, id_lanceur, date="2025-01-02 10:00:00"):
    dm.update_strict("INSERT INTO metadonnees_collecte (id_utilisateur_lanceur, date_collecte) VALUES (?, ?)",
                     (id_lanceur, date))


def test_dernier_lanceur_de_collecte_sans_nom_est_lisible(stats_dm):
    u = _utilisateur(stats_dm, None, None)
    _collecte(stats_dm, u)
    assert stats_dm.get_last_collecte()["lanceur"] == f"(utilisateur #{u} sans nom)"


def test_dernier_lanceur_de_collecte_nominal_et_automatique(stats_dm):
    u = _utilisateur(stats_dm, "Martin", "Léa")
    _collecte(stats_dm, u)
    assert stats_dm.get_last_collecte()["lanceur"] == "Martin Léa"
    _collecte(stats_dm, None, "2025-01-03 10:00:00")            # aucune personne : collecte automatique
    assert stats_dm.get_last_collecte()["lanceur"] == "Automatique"
