"""Limite de chargement du tableau des demandes.

Défaut constaté chez le client : la limite saisie dans Configuration > Général était enregistrée en base,
mais le tableau la lisait dans config.json (où elle n'existe pas) et retombait toujours sur 1000. La tuile
« non affectées » comptait toute la base alors que le tableau était tronqué : 176 contre 110.
"""

import pytest
from conftest import definir_role

from app.utils.affichage import avertissement_limite


@pytest.fixture
def pdm(dm):
    """DataManager avec la vraie forme de parametres_app : une valeur par utilisateur et par clé."""
    dm.update_strict("DROP TABLE parametres_app")
    dm.update_strict("""CREATE TABLE parametres_app (cle TEXT, valeur TEXT, description TEXT, type_valeur TEXT,
                        id_utilisateur INTEGER, UNIQUE (cle, id_utilisateur))""")
    return dm


def _param(dm, cle, valeur, type_valeur="int", id_utilisateur=None):
    dm.update_strict("INSERT INTO parametres_app (cle, valeur, description, type_valeur, id_utilisateur) "
                     "VALUES (?, ?, 'd', ?, ?)", (cle, str(valeur), type_valeur, id_utilisateur))


def _lignes(dm, cle):
    return dm.query_strict("SELECT valeur, type_valeur, id_utilisateur FROM parametres_app WHERE cle = ?", (cle,))


# --------------------------------------------------------------------- get_parametre (était cassée : valeur par défaut)
def test_get_parametre_lit_la_valeur_de_l_utilisateur(pdm):
    _param(pdm, "mail_days", 45, id_utilisateur=1)
    assert pdm.get_parametre("mail_days", default=-1) == 45          # entier converti


def test_get_parametre_prefere_la_valeur_de_l_utilisateur_au_modele(pdm):
    _param(pdm, "mail_days", 30)                                    # ligne globale
    _param(pdm, "mail_days", 7, id_utilisateur=1)                    # surcharge de l'utilisateur
    assert pdm.get_parametre("mail_days") == 7


def test_get_parametre_repli_sur_la_ligne_globale(pdm):
    _param(pdm, "mail_days", 30)
    assert pdm.get_parametre("mail_days") == 30


def test_get_parametre_inconnu_donne_le_defaut(pdm):
    assert pdm.get_parametre("inexistant", default="x") == "x"


def test_get_parametre_texte_et_booleen(pdm):
    _param(pdm, "outlook_folder", "PIGC", type_valeur="str", id_utilisateur=1)
    _param(pdm, "actif", "true", type_valeur="bool", id_utilisateur=1)
    assert pdm.get_parametre("outlook_folder") == "PIGC"
    assert pdm.get_parametre("actif") is True


# --------------------------------------------------------------------- limite de chargement
def test_limite_par_defaut_1000(pdm):
    assert pdm.get_limite_demandes() == 1000


def test_limite_lue_dans_la_base(pdm):
    _param(pdm, "demande_limit", 3000, id_utilisateur=1)
    assert pdm.get_limite_demandes() == 3000


def test_limite_de_la_base_prioritaire_sur_config_json(pdm):
    pdm.conf["demande_limit"] = "500"
    _param(pdm, "demande_limit", 3000, id_utilisateur=1)
    assert pdm.get_limite_demandes() == 3000


def test_repli_sur_config_json_pour_les_anciennes_installations(pdm):
    pdm.conf["demande_limit"] = "2500"
    assert pdm.get_limite_demandes() == 2500


@pytest.mark.parametrize("valeur,attendu", [("abc", 1000), ("0", 1000), ("-5", 1000), ("", 1000),
                                            ("250000", 100000), ("1", 1)])
def test_limite_invalide_ou_hors_bornes(pdm, valeur, attendu):
    _param(pdm, "demande_limit", valeur, type_valeur="str", id_utilisateur=1)
    assert pdm.get_limite_demandes() == attendu


# --------------------------------------------------------------------- sauvegarde du réglage (valeur perdue en silence)
def test_sauvegarde_sans_ligne_modele_n_est_plus_perdue(pdm):
    """Sans ligne globale 'demande_limit', l'ancien INSERT ... SELECT n'insérait rien : la valeur était perdue."""
    assert pdm.update_parametres_bulk({"demande_limit": "3000", "mail_days": "60"}) is True
    assert _lignes(pdm, "demande_limit") == [("3000", "int", 1)]
    assert pdm.get_limite_demandes() == 3000
    assert pdm.get_parametre("mail_days") == 60


def test_sauvegarde_avec_ligne_modele_copie_son_type(pdm):
    _param(pdm, "demande_limit", 1000)
    pdm.update_parametres_bulk({"demande_limit": "3000"})
    assert sorted(_lignes(pdm, "demande_limit"), key=lambda r: r[2] is not None) == [
        ("1000", "int", None), ("3000", "int", 1)]
    assert pdm.get_limite_demandes() == 3000


def test_resauvegarde_remplace_sans_doublon(pdm):
    pdm.update_parametres_bulk({"demande_limit": "3000"})
    pdm.update_parametres_bulk({"demande_limit": "4000"})
    assert _lignes(pdm, "demande_limit") == [("4000", "int", 1)]


def test_sauvegarde_conserve_les_cles_textuelles_avec_ligne_modele(pdm):
    _param(pdm, "outlook_folder", "PIGC", type_valeur="str")
    pdm.update_parametres_bulk({"outlook_folder": "AUTRE", "demande_limit": "3000"})
    assert pdm.get_parametre("outlook_folder") == "AUTRE"


# --------------------------------------------------------------------- scénario du client
def _demandes_sans_responsable(dm, n):
    for i in range(n):
        dm.update_strict("INSERT INTO demandes (id_etat, date_reception) VALUES (1, ?)", (f"2025-01-{i + 1:02d}",))


def test_tableau_tronque_alors_que_la_tuile_compte_tout(pdm):
    """Reproduit « 176 sur la tuile, 110 dans le tableau » : limite atteinte, la tuile compte toute la base."""
    _demandes_sans_responsable(pdm, 6)
    _param(pdm, "demande_limit", 4, id_utilisateur=1)
    lignes = pdm.get_demandes(limit=pdm.get_limite_demandes(), inclure_archivees=True, inclure_annulees=True)
    assert len(lignes) == 4                                           # tronqué
    assert pdm.get_demandes_non_affectees() == 6                      # la tuile compte tout
    assert avertissement_limite(len(lignes), pdm.get_limite_demandes()) != ""   # l'écran doit le dire


def test_apres_augmentation_de_la_limite_tableau_et_tuile_concordent(pdm):
    _demandes_sans_responsable(pdm, 6)
    pdm.update_parametres_bulk({"demande_limit": "3000"})
    lignes = pdm.get_demandes(limit=pdm.get_limite_demandes(), inclure_archivees=True, inclure_annulees=True)
    assert len(lignes) == 6 == pdm.get_demandes_non_affectees()
    assert avertissement_limite(len(lignes), pdm.get_limite_demandes()) == ""


# --------------------------------------------------------------------- libellé d'avertissement
@pytest.mark.parametrize("chargees,limite,alerte", [(999, 1000, False), (1000, 1000, True), (3000, 3000, True),
                                                    (0, 1000, False), (5, 0, False)])
def test_avertissement_limite(chargees, limite, alerte):
    texte = avertissement_limite(chargees, limite)
    assert bool(texte) is alerte
    if alerte:
        assert str(limite) in texte and "Configuration" in texte
