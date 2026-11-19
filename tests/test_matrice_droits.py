"""Matrice des droits de l'écran Utilisateurs : cohérente avec les permissions réellement appliquées (sans Qt)."""

from app.utils.auth import PERMISSIONS, has_permission
from app.utils.matrice_droits import MATRICE_DROITS, ROLES_MATRICE, droit_accorde


def test_la_matrice_couvre_tous_les_droits_de_permissions():
    """Un nouveau droit ajouté à PERMISSIONS doit apparaître dans la matrice affichée à l'administrateur."""
    droits_matrice = {cle for _, cle in MATRICE_DROITS if cle is not None}
    assert droits_matrice == set(PERMISSIONS["Administrateur"])


def test_la_matrice_ne_reference_aucun_droit_inexistant():
    for _, cle in MATRICE_DROITS:
        assert cle is None or cle in PERMISSIONS["Consultant"]


def test_les_roles_de_la_matrice_sont_ceux_de_permissions():
    assert set(ROLES_MATRICE) == set(PERMISSIONS)


def test_chaque_cellule_reprend_has_permission():
    for _, cle in MATRICE_DROITS:
        for role in ROLES_MATRICE:
            attendu = True if cle is None else has_permission(role, cle)
            assert droit_accorde(role, cle) is attendu


def test_les_libelles_sont_uniques_et_non_vides():
    libelles = [libelle for libelle, _ in MATRICE_DROITS]
    assert all(libelles) and len(set(libelles)) == len(libelles)


def test_le_consultant_n_a_que_de_la_lecture():
    droits = {cle for _, cle in MATRICE_DROITS if cle and droit_accorde("Consultant", cle)}
    assert droits == {"rapports", "exporter"}


def test_les_droits_d_administration_sont_reserves_a_l_administrateur():
    for cle in ("gerer_listes", "gerer_utilisateurs", "gerer_collectes", "archiver"):
        assert droit_accorde("Administrateur", cle)
        assert not droit_accorde("Membre MCO", cle) and not droit_accorde("Consultant", cle)
