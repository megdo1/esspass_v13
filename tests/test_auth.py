from app.utils.auth import PERMISSIONS, has_permission


def test_role_inconnu_sans_droit():
    assert has_permission("Inconnu", "exporter") is False


def test_action_inconnue_refusee():
    assert has_permission("Administrateur", "action_inexistante") is False


def test_gerer_listes_reserve_a_l_administrateur():
    assert has_permission("Administrateur", "gerer_listes") is True
    assert has_permission("Membre MCO", "gerer_listes") is False
    assert has_permission("Consultant", "gerer_listes") is False


def test_consultant_lecture_seule():
    droits = {a for a, ok in PERMISSIONS["Consultant"].items() if ok}
    assert droits == {"exporter", "rapports"}


def test_roles_ont_les_memes_actions():
    assert len({frozenset(p) for p in PERMISSIONS.values()}) == 1
