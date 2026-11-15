"""Tests de DataManager sur une base temporaire : gestion d'erreurs, verrou optimiste, référentiels, config."""

import sqlite3

import pytest

from conftest import definir_role
from app.data.errors import ConflitModificationError, DatabaseError


def _creer_demande(dm, **extra):
    data = {"libelle": "L", "sujet": "S", "resume": "R", "demandeur": "d@x.fr",
            "id_canal": 1, "id_domaine": 1, "id_categorie": 1, "id_etat": 1}
    data.update(extra)
    return dm.create_demande(data)


# --------------------------------------------------------------------- erreurs vs résultat vide
def test_select_vide_n_est_pas_une_erreur(dm):
    assert dm._execute_query("SELECT * FROM demandes") == []
    assert dm.last_error is None
    assert dm.query_strict("SELECT * FROM demandes") == []


def test_select_en_erreur_renvoie_none_et_renseigne_last_error(dm):
    assert dm._execute_query("SELECT * FROM table_inconnue") is None
    assert "table_inconnue" in dm.last_error


def test_query_strict_leve_database_error(dm):
    with pytest.raises(DatabaseError):
        dm.query_strict("SELECT * FROM table_inconnue")


def test_update_strict_leve_database_error(dm):
    with pytest.raises(DatabaseError):
        dm.update_strict("UPDATE table_inconnue SET a = 1")


def test_last_error_remis_a_none_apres_succes(dm):
    dm._execute_query("SELECT * FROM table_inconnue")
    assert dm.last_error
    dm._execute_query("SELECT 1")
    assert dm.last_error is None


# --------------------------------------------------------------------- verrou optimiste
def test_update_sans_verification_reste_compatible(dm):
    id_d = _creer_demande(dm)
    assert dm.update_demande(id_d, {"resume": "nouveau"}) is True
    assert dm.get_demande_by_id(id_d)["resume"] == "nouveau"


def test_update_avec_version_correcte(dm):
    id_d = _creer_demande(dm)
    version = dm.get_demande_by_id(id_d)["updated_at"]
    assert dm.update_demande(id_d, {"resume": "ok"}, expected_updated_at=version) is True


def test_update_avec_version_perimee_leve_conflit(dm):
    id_d = _creer_demande(dm)
    version = dm.get_demande_by_id(id_d)["updated_at"]
    # un autre poste modifie la demande entre-temps
    dm.update_strict("UPDATE demandes SET updated_at = '2099-01-01 00:00:00', resume = 'autre poste' "
                     "WHERE id_demande = ?", (id_d,))
    with pytest.raises(ConflitModificationError, match="modifiée"):
        dm.update_demande(id_d, {"resume": "écrasement"}, expected_updated_at=version)
    assert dm.get_demande_by_id(id_d)["resume"] == "autre poste"   # rien n'a été écrasé


def test_update_demande_supprimee_leve_conflit(dm):
    id_d = _creer_demande(dm)
    version = dm.get_demande_by_id(id_d)["updated_at"]
    dm.update_strict("DELETE FROM demandes WHERE id_demande = ?", (id_d,))
    with pytest.raises(ConflitModificationError, match="n'existe plus"):
        dm.update_demande(id_d, {"resume": "x"}, expected_updated_at=version)


def test_update_version_none_cible_les_lignes_sans_updated_at(dm):
    id_d = _creer_demande(dm)
    dm.update_strict("UPDATE demandes SET updated_at = NULL WHERE id_demande = ?", (id_d,))
    assert dm.update_demande(id_d, {"resume": "ok"}, expected_updated_at=None) is True


# --------------------------------------------------------------------- référentiels
def test_chargement_initial_des_listes(dm):
    assert dm.liste_valeurs["canaux"] == ["A", "B"]
    assert dm.sous_categories_by_categorie


def test_chargement_initial_echoue_si_base_en_erreur(db_path, monkeypatch):
    conn = sqlite3.connect(db_path)
    conn.execute("DROP TABLE urgences")
    conn.commit()
    conn.close()
    from app.data import data_manager as dm_module
    monkeypatch.setattr(dm_module, "loadConfig", lambda *a, **k: {"sqlite_path": db_path})
    with pytest.raises(DatabaseError):
        dm_module.DataManager()


def test_rechargement_en_erreur_conserve_les_anciennes_listes(dm):
    dm.update_strict("ALTER TABLE canaux RENAME TO canaux_hs")      # panne simulée
    assert dm.reload_reference_data() is False
    assert dm.liste_valeurs["canaux"] == ["A", "B"]                 # pas de listes vides silencieuses


# --------------------------------------------------------------------- config (bug self.conn)
def test_set_parametre_en_erreur_renvoie_false_sans_attribute_error(dm):
    dm.update_strict("DROP TABLE parametres_app")
    assert dm.set_parametre("cle", "valeur") is False


def test_reset_colonnes_en_erreur_renvoie_false_sans_attribute_error(dm):
    dm.update_strict("DROP TABLE colonnes_config")
    assert dm.reset_colonnes_default() is False


def test_reset_colonnes_nominal(dm):
    dm.update_strict("INSERT INTO colonnes_config (nom_colonne, visible) VALUES ('a', 0)")
    assert dm.reset_colonnes_default() is True
    assert dm.query_strict("SELECT visible FROM colonnes_config") == [(1,)]


# --------------------------------------------------------------------- droits côté données
def test_consultant_ne_peut_pas_modifier_une_demande(dm):
    id_d = _creer_demande(dm)
    definir_role(dm, "Consultant")
    assert dm.update_demande(id_d, {"resume": "pirate"}) is False
    assert "Droits insuffisants" in dm.last_error
    assert dm.get_demande_by_id(id_d)["resume"] == "R"


def test_consultant_ne_peut_pas_creer_ni_modifier_en_masse(dm):
    id_d = _creer_demande(dm)
    definir_role(dm, "Consultant")
    assert _creer_demande(dm) is None
    assert dm.update_demandes_bulk([id_d], {"resume": "x"}) == (0, 1)
    assert dm.update_etat_multiple([id_d], 2) == (0, 1)
    assert dm.get_demande_by_id(id_d)["id_etat"] == 1


def test_utilisateur_inconnu_refuse(dm):
    id_d = _creer_demande(dm)
    definir_role(dm, None)
    assert dm.update_demande(id_d, {"resume": "x"}) is False


def test_membre_mco_peut_modifier(dm):
    id_d = _creer_demande(dm)
    definir_role(dm, "Membre MCO")
    assert dm.update_demande(id_d, {"resume": "ok"}) is True


# --------------------------------------------------------------------- droits : utilisateurs, collecte, paramètres globaux
def test_seul_administrateur_gere_les_utilisateurs(dm):
    for role in ("Consultant", "Membre MCO"):
        definir_role(dm, role)
        assert dm.create_user_with_role("N", "P", "n@x.fr", 2, True) is False
        assert dm.update_user_role(1, 3) is False
        assert dm.deactivate_user(1) is False
        assert dm.delete_user(1) is False
        assert "Droits insuffisants" in dm.last_error
    assert dm.query_strict("SELECT COUNT(*) FROM utilisateurs") == [(1,)]
    assert dm.query_strict("SELECT actif FROM utilisateurs WHERE id_utilisateur = 1") == [(1,)]


def test_administrateur_peut_creer_un_utilisateur(dm):
    assert dm.create_user_with_role("Martin", "Léa", "l@x.fr", 2, True) is True
    assert dm.query_strict("SELECT COUNT(*) FROM utilisateurs") == [(2,)]


def test_consultant_ne_peut_pas_lancer_de_collecte(dm):
    definir_role(dm, "Consultant")
    assert dm.creer_collecte(1) is None
    assert dm.query_strict("SELECT COUNT(*) FROM metadonnees_collecte") == [(0,)]


def test_membre_mco_peut_lancer_une_collecte(dm):
    definir_role(dm, "Membre MCO")
    assert dm.creer_collecte(1) is not None


def test_parametre_global_reserve_a_l_administrateur(dm):
    definir_role(dm, "Membre MCO")
    assert dm.set_parametre("cle", "v") is False
    definir_role(dm, "Administrateur")
    assert dm.set_parametre("cle", "v") is True


# --------------------------------------------------------------------- compteur d'erreurs (affichage d'une erreur au lieu de « aucune donnée »)
def test_error_count_incremente_seulement_en_cas_d_erreur(dm):
    avant = dm.error_count
    dm._execute_query("SELECT 1")
    assert dm.error_count == avant
    dm._execute_query("SELECT * FROM table_inconnue")
    dm._execute_update("UPDATE table_inconnue SET a = 1")
    assert dm.error_count == avant + 2


def test_get_demandes_vide_sans_erreur_vs_avec_erreur(dm):
    avant = dm.error_count
    assert dm.get_demandes() == [] and dm.error_count == avant        # vraiment aucune demande
    dm.update_strict("DROP TABLE etats")
    avant = dm.error_count
    assert dm.get_demandes() == [] and dm.error_count > avant         # erreur détectable par la vue


# --------------------------------------------------------------------- cache du rôle (une lecture par session)
def _compter_lectures_role(dm, role="Membre MCO"):
    appels = []

    def lecture():
        appels.append(1)
        return {"nom": "T", "prenom": "T", "role": role, "id": 1}

    dm.invalidate_role_cache()
    dm.get_current_user = lecture
    return appels


def test_role_lu_une_seule_fois_pour_plusieurs_ecritures(dm):
    appels = _compter_lectures_role(dm)
    id_d = _creer_demande(dm)
    for i in range(5):
        assert dm.update_demande(id_d, {"resume": f"v{i}"}) is True
    assert len(appels) == 1


def test_changement_de_role_applique_apres_invalidation_seulement(dm):
    appels = _compter_lectures_role(dm, "Membre MCO")
    id_d = _creer_demande(dm)
    assert dm.update_demande(id_d, {"resume": "ok"}) is True
    dm.get_current_user = lambda: {"role": "Consultant", "id": 1}       # rôle changé en base
    assert dm.update_demande(id_d, {"resume": "encore"}) is True        # cache : ancien rôle (redémarrage requis)
    dm.invalidate_role_cache()                                          # = redémarrage de l'application
    assert dm.update_demande(id_d, {"resume": "refusé"}) is False


def test_echec_de_lecture_du_role_n_est_pas_mis_en_cache(dm):
    id_d = _creer_demande(dm)
    dm.invalidate_role_cache()
    dm.get_current_user = lambda: None                                  # Outlook fermé
    assert dm.update_demande(id_d, {"resume": "x"}) is False
    dm.get_current_user = lambda: {"role": "Membre MCO", "id": 1}       # Outlook de retour
    assert dm.update_demande(id_d, {"resume": "x"}) is True
