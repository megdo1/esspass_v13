"""Responsables ES-PASS : table utilisateur_responsable, liste proposée dans les demandes, gestion par l'administrateur."""

import logging
import os

import pytest
from conftest import definir_role

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _utilisateur(dm, nom, prenom, email=None, id_role=2, actif=1, responsable=False):
    dm.update_strict("INSERT INTO utilisateurs (nom, prenom, email, id_role, actif) VALUES (?, ?, ?, ?, ?)",
                     (nom, prenom, email, id_role, actif))
    identifiant = dm.query_strict("SELECT MAX(id_utilisateur) FROM utilisateurs")[0][0]
    if responsable:
        assert dm.definir_responsable(identifiant, True)
    return identifiant


def _noms(dm):
    return [u["nom_complet"] for u in dm.get_responsables()]


def _sans_table(dm):
    """Simule une base où le script 001 n'a pas été appliqué."""
    dm.update_strict("DROP TRIGGER IF EXISTS trg_utilisateur_responsable_suppression")
    dm.update_strict("DROP TABLE utilisateur_responsable")
    dm._table_responsables_ok = False


# --------------------------------------------------------------------- liste proposée dans les demandes
def test_seuls_les_utilisateurs_coches_sont_proposes(dm):
    _utilisateur(dm, "Martin", "Léa", responsable=True)
    _utilisateur(dm, "Durand", "Paul")                                 # actif mais non coché
    assert _noms(dm) == ["Martin Léa"]


def test_les_non_actifs_ne_sont_pas_proposes_meme_coches(dm):
    _utilisateur(dm, "Inactif", "Jean", actif=0, responsable=True)
    _utilisateur(dm, "Actif", "Jeanne", responsable=True)
    assert _noms(dm) == ["Actif Jeanne"]


def test_liste_triee_sans_tenir_compte_de_la_casse(dm):
    for nom in ("zola", "Arnaud", "Martin"):
        _utilisateur(dm, nom, "X", responsable=True)
    assert _noms(dm) == ["Arnaud X", "Martin X", "zola X"]


def test_contenu_d_une_entree(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa", id_role=3, responsable=True)
    entree = dm.get_responsables()[0]
    assert entree == {"id": identifiant, "nom": "Martin", "prenom": "Léa", "role": "Administrateur",
                      "nom_complet": "Martin Léa"}


def test_un_responsable_sans_role_est_propose(dm):
    """Contrairement à l'ancienne liste (JOIN roles), un compte sans rôle peut être responsable."""
    _utilisateur(dm, "Martin", "Léa", id_role=None, responsable=True)
    assert _noms(dm) == ["Martin Léa"]
    assert dm.get_responsables()[0]["role"] is None


def test_responsable_sans_nom_est_lisible(dm):
    """Plus de « None None » : e-mail à défaut de nom, repère numéroté à défaut d'e-mail."""
    sans_nom = _utilisateur(dm, None, None, email="x@y.fr", responsable=True)
    anonyme = _utilisateur(dm, None, None, responsable=True)
    noms = _noms(dm)
    assert "x@y.fr" in noms and f"(utilisateur #{anonyme} sans nom)" in noms
    assert not any("None" in n for n in noms)
    assert sans_nom != anonyme


def test_liste_vide_quand_personne_n_est_coche(dm):
    dm.update_strict("DELETE FROM utilisateur_responsable")
    assert dm.get_responsables() == []


# --------------------------------------------------------------------- compatibilité : script non appliqué
def test_sans_table_tous_les_actifs_sont_proposes(dm):
    _utilisateur(dm, "Martin", "Léa")
    _utilisateur(dm, "Inactif", "Jean", actif=0)
    _sans_table(dm)
    noms = _noms(dm)
    assert "Martin Léa" in noms and "Dupont Jean" in noms and "Inactif Jean" not in noms


def test_sans_table_un_avertissement_unique_est_journalise(dm, caplog):
    _sans_table(dm)
    with caplog.at_level(logging.WARNING):
        dm.get_responsables()
        dm.get_responsables()
    avertissements = [r for r in caplog.records if "utilisateur_responsable" in r.getMessage()]
    assert len(avertissements) == 1
    assert "001_utilisateur_responsable.sql" in avertissements[0].getMessage()


def test_table_existe_detectee_puis_mise_en_cache(dm):
    assert dm.table_responsables_existe() is True
    dm.update_strict("DROP TRIGGER trg_utilisateur_responsable_suppression")
    dm.update_strict("DROP TABLE utilisateur_responsable")
    assert dm.table_responsables_existe() is True                      # résultat positif mis en cache
    dm._table_responsables_ok = False
    assert dm.table_responsables_existe() is False


# --------------------------------------------------------------------- cocher / décocher
def test_cocher_puis_decocher(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa")
    assert dm.definir_responsable(identifiant, True) is True
    assert "Martin Léa" in _noms(dm)
    assert dm.definir_responsable(identifiant, False) is True
    assert "Martin Léa" not in _noms(dm)


def test_cocher_deux_fois_ne_cree_pas_de_doublon_et_garde_la_date(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa", responsable=True)
    dm.update_strict("UPDATE utilisateur_responsable SET date_ajout = '2020-01-01 00:00:00' WHERE id_utilisateur = ?",
                     (identifiant,))
    assert dm.definir_responsable(identifiant, True) is True
    lignes = dm.query_strict("SELECT date_ajout FROM utilisateur_responsable WHERE id_utilisateur = ?", (identifiant,))
    assert lignes == [("2020-01-01 00:00:00",)]


def test_decocher_un_non_responsable_est_sans_effet(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa")
    assert dm.definir_responsable(identifiant, False) is True


def test_l_auteur_du_changement_est_enregistre(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa")
    dm.get_current_user = lambda: {"role": "Administrateur", "id": 1}
    dm.definir_responsable(identifiant, True)
    assert dm.query_strict("SELECT ajoute_par FROM utilisateur_responsable WHERE id_utilisateur = ?",
                           (identifiant,)) == [(1,)]


def test_utilisateur_inconnu_refuse(dm):
    assert dm.definir_responsable(99999, True) is False
    assert "introuvable" in dm.last_error
    assert dm.query_strict("SELECT COUNT(*) FROM utilisateur_responsable WHERE id_utilisateur = 99999") == [(0,)]


def test_cocher_sans_table_explique_quoi_faire(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa")
    _sans_table(dm)
    assert dm.definir_responsable(identifiant, True) is False
    assert "001_utilisateur_responsable.sql" in dm.last_error


@pytest.mark.parametrize("role", ["Consultant", "Membre MCO", None])
def test_seul_l_administrateur_gere_les_responsables(dm, role):
    identifiant = _utilisateur(dm, "Martin", "Léa")
    definir_role(dm, role)
    assert dm.definir_responsable(identifiant, True) is False
    assert "Droits insuffisants" in dm.last_error
    definir_role(dm, "Administrateur")
    assert "Martin Léa" not in _noms(dm)                                 # rien n'a été enregistré


# --------------------------------------------------------------------- écran Utilisateurs
def test_liste_des_utilisateurs_indique_qui_est_responsable(dm):
    oui = _utilisateur(dm, "Oui", "A", responsable=True)
    non = _utilisateur(dm, "Non", "B")
    par_id = {u["id_utilisateur"]: u["est_responsable"] for u in dm.get_all_users_with_roles()}
    assert par_id[oui] == 1 and par_id[non] == 0


def test_liste_des_utilisateurs_sans_table_donne_none(dm):
    _sans_table(dm)
    assert all(u["est_responsable"] is None for u in dm.get_all_users_with_roles())


def test_supprimer_un_utilisateur_retire_son_statut_de_responsable(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa", responsable=True)
    dm.update_strict("DROP TRIGGER trg_utilisateur_responsable_suppression")   # sans le trigger du script
    assert dm.delete_user(identifiant) is True
    assert dm.query_strict("SELECT COUNT(*) FROM utilisateur_responsable WHERE id_utilisateur = ?",
                           (identifiant,)) == [(0,)]


def test_get_nb_demandes_affectees(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa", responsable=True)
    for _ in range(3):
        dm.update_strict("INSERT INTO demandes (id_etat, id_responsable) VALUES (1, ?)", (identifiant,))
    assert dm.get_nb_demandes_affectees(identifiant) == 3
    assert dm.get_nb_demandes_affectees(99999) == 0


def test_get_id_utilisateur_par_email(dm):
    identifiant = _utilisateur(dm, "Martin", "Léa", email="lea@x.fr")
    assert dm.get_id_utilisateur_par_email("lea@x.fr") == identifiant
    assert dm.get_id_utilisateur_par_email("inconnu@x.fr") is None


# --------------------------------------------------------------------- l'ancienne liste n'est plus filtrée
def test_get_all_users_renvoie_tous_les_actifs_avec_role(dm):
    _utilisateur(dm, "Martin", "Léa")                                   # non responsable : toujours listé ici
    _utilisateur(dm, "Inactif", "Jean", actif=0)
    noms = [u["nom"] for u in dm.get_all_users()]
    assert "Martin" in noms and "Inactif" not in noms


# --------------------------------------------------------------------- les dialogues utilisent la nouvelle liste
@pytest.mark.parametrize("fichier", ["app/views/pass_v3/demande_dialogs.py", "app/views/pass_v3/traitement_dialogs.py"])
def test_les_dialogues_de_demandes_utilisent_get_responsables(fichier):
    with open(os.path.join(RACINE, fichier), encoding="utf8") as f:
        source = f.read()
    assert "get_responsables()" in source
    assert "get_all_users()" not in source
