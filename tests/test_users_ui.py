"""Écran Utilisateurs : colonne et case « Responsable ES-PASS » (création, modification, table absente).

Nécessite PyQt5 (ignoré sinon). Affichage hors écran ; les boîtes de message sont remplacées par un enregistreur.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from conftest import definir_role  # noqa: E402


class FausseBoite:
    """Remplace QMessageBox : enregistre les appels statiques (information, warning, critical)."""
    appels = []

    @staticmethod
    def information(parent, titre, texte, *args, **kwargs):
        FausseBoite.appels.append(("information", titre, texte))

    @staticmethod
    def warning(parent, titre, texte, *args, **kwargs):
        FausseBoite.appels.append(("warning", titre, texte))

    @staticmethod
    def critical(parent, titre, texte, *args, **kwargs):
        FausseBoite.appels.append(("critical", titre, texte))


@pytest.fixture(scope="module")
def app_qt():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ecran(app_qt, dm, monkeypatch):
    from app.views import pass_users_view
    from app.views.users import actions_mixin
    FausseBoite.appels = []
    monkeypatch.setattr(actions_mixin, "QMessageBox", FausseBoite)
    monkeypatch.setattr(pass_users_view, "DataManager", lambda: dm)
    dm.is_current_user_admin = lambda: True
    dm.update_strict("INSERT INTO utilisateurs (nom, prenom, email, id_role, actif) VALUES ('Resp', 'Oui', 'oui@x.fr', 2, 1)")
    dm.update_strict("INSERT INTO utilisateurs (nom, prenom, email, id_role, actif) VALUES ('Inactif', 'Non', 'non@x.fr', 1, 0)")
    id_resp = dm.get_id_utilisateur_par_email("oui@x.fr")
    dm.definir_responsable(id_resp, True)
    fenetre = pass_users_view.GestionUtilisateursDialog()
    fenetre.id_resp = id_resp
    return fenetre


def _ligne(ecran, email):
    for i in range(ecran.tableau_utilisateurs.rowCount()):
        if ecran.tableau_utilisateurs.item(i, 3).text() == email:
            return i
    raise AssertionError(f"{email} absent du tableau")


def _sans_table(dm):
    dm.update_strict("DROP TRIGGER IF EXISTS trg_utilisateur_responsable_suppression")
    dm.update_strict("DROP TABLE utilisateur_responsable")
    dm._table_responsables_ok = False


# --------------------------------------------------------------------- liste
def test_colonne_responsable_es_pass_affichee(ecran):
    t = ecran.tableau_utilisateurs
    assert t.columnCount() == 7
    assert t.horizontalHeaderItem(6).text() == "Responsable ES-PASS"
    assert "Oui" in t.item(_ligne(ecran, "oui@x.fr"), 6).text()
    assert t.item(_ligne(ecran, "non@x.fr"), 6).text() == "—"


def test_etat_responsable_memorise_dans_la_cellule(ecran):
    t = ecran.tableau_utilisateurs
    assert t.item(_ligne(ecran, "oui@x.fr"), 6).data(Qt.UserRole) is True
    assert t.item(_ligne(ecran, "non@x.fr"), 6).data(Qt.UserRole) is False


def test_etat_actif_memorise_dans_la_cellule_statut(ecran):
    """Corrige : la boîte de modification relisait le texte « ✅ Actif » et décochait toujours « actif »."""
    t = ecran.tableau_utilisateurs
    assert t.item(_ligne(ecran, "oui@x.fr"), 5).data(Qt.UserRole) is True
    assert t.item(_ligne(ecran, "non@x.fr"), 5).data(Qt.UserRole) is False


def test_sans_table_la_colonne_indique_non_applicable(app_qt, dm, monkeypatch):
    from app.views import pass_users_view
    from app.views.users import actions_mixin
    monkeypatch.setattr(actions_mixin, "QMessageBox", FausseBoite)
    monkeypatch.setattr(pass_users_view, "DataManager", lambda: dm)
    dm.is_current_user_admin = lambda: True
    _sans_table(dm)
    fenetre = pass_users_view.GestionUtilisateursDialog()
    cellule = fenetre.tableau_utilisateurs.item(0, 6)
    assert cellule.text() == "n/a" and cellule.data(Qt.UserRole) is None
    assert "001_utilisateur_responsable.sql" in cellule.toolTip()
    assert not fenetre.check_responsable.isEnabled()
    assert "001_utilisateur_responsable.sql" in fenetre.check_responsable.toolTip()


# --------------------------------------------------------------------- création
def _remplir(ecran, email, responsable):
    ecran.input_nom.setText("Martin")
    ecran.input_prenom.setText("Léa")
    ecran.input_email.setText(email)
    ecran.combo_role_new.setCurrentIndex(1)
    ecran.check_responsable.setChecked(responsable)


def test_creation_avec_case_responsable_cochee(ecran, dm):
    _remplir(ecran, "lea@x.fr", True)
    ecran.creer_utilisateur()
    identifiant = dm.get_id_utilisateur_par_email("lea@x.fr")
    assert identifiant and "Martin Léa" in [u["nom_complet"] for u in dm.get_responsables()]
    assert any("Responsable ES-PASS : oui" in texte for _, _, texte in FausseBoite.appels)
    assert not ecran.check_responsable.isChecked()                       # formulaire réinitialisé
    assert "Oui" in ecran.tableau_utilisateurs.item(_ligne(ecran, "lea@x.fr"), 6).text()


def test_creation_sans_case_cochee_ne_cree_pas_de_responsable(ecran, dm):
    _remplir(ecran, "lea@x.fr", False)
    ecran.creer_utilisateur()
    assert dm.get_id_utilisateur_par_email("lea@x.fr")
    assert "Martin Léa" not in [u["nom_complet"] for u in dm.get_responsables()]
    assert ecran.tableau_utilisateurs.item(_ligne(ecran, "lea@x.fr"), 6).text() == "—"


def test_creation_responsable_refusee_si_pas_administrateur_previent(ecran, dm):
    """L'utilisateur est créé (droit déjà contrôlé en amont) mais l'enregistrement du statut est signalé."""
    _remplir(ecran, "lea@x.fr", True)
    original = dm.definir_responsable
    dm.definir_responsable = lambda *a, **k: (setattr(dm, "last_error", "Droits insuffisants") or False)
    ecran.creer_utilisateur()
    dm.definir_responsable = original
    assert any(genre == "warning" and "Droits insuffisants" in texte for genre, _, texte in FausseBoite.appels)


def test_reinitialisation_decoche_responsable(ecran):
    ecran.check_responsable.setChecked(True)
    ecran.reinitialiser_form()
    assert not ecran.check_responsable.isChecked()


# --------------------------------------------------------------------- modification
def test_cocher_responsable_a_la_modification(ecran, dm):
    identifiant = dm.get_id_utilisateur_par_email("non@x.fr")
    complement = ecran._appliquer_statut_responsable(identifiant, False, True)
    assert "Désormais responsable ES-PASS" in complement
    assert identifiant not in [u["id"] for u in dm.get_responsables()]        # inactif : coché mais jamais proposé
    assert dm.query_strict("SELECT COUNT(*) FROM utilisateur_responsable WHERE id_utilisateur = ?", (identifiant,)) == [(1,)]


def test_decocher_signale_les_demandes_deja_affectees(ecran, dm):
    for _ in range(2):
        dm.update_strict("INSERT INTO demandes (id_etat, id_responsable) VALUES (1, ?)", (ecran.id_resp,))
    complement = ecran._appliquer_statut_responsable(ecran.id_resp, True, False)
    assert "n'est plus responsable ES-PASS" in complement.replace("N'est", "n'est")
    assert "2 demande(s)" in complement and "le restent" in complement
    assert ecran.id_resp not in [u["id"] for u in dm.get_responsables()]


def test_decocher_sans_demande_ne_mentionne_aucun_compte(ecran):
    assert "demande(s)" not in ecran._appliquer_statut_responsable(ecran.id_resp, True, False)


def test_aucun_changement_n_ecrit_rien(ecran, dm):
    dm.definir_responsable = lambda *a, **k: pytest.fail("ne doit pas écrire")
    assert ecran._appliquer_statut_responsable(ecran.id_resp, True, True) == ""
    assert ecran._appliquer_statut_responsable(ecran.id_resp, False, False) == ""


def test_fonction_indisponible_sans_table_n_ecrit_rien(ecran, dm):
    dm.definir_responsable = lambda *a, **k: pytest.fail("ne doit pas écrire")
    assert ecran._appliquer_statut_responsable(ecran.id_resp, None, True) == ""      # état None = table absente


def test_echec_d_enregistrement_est_signale(ecran, dm):
    dm.definir_responsable = lambda *a, **k: (setattr(dm, "last_error", "disque plein") or False)
    assert ecran._appliquer_statut_responsable(ecran.id_resp, False, True) == ""
    assert any(genre == "warning" and "disque plein" in texte for genre, _, texte in FausseBoite.appels)


# --------------------------------------------------------------------- les droits restent ceux de l'administrateur
def test_un_non_administrateur_ne_peut_rien_changer(ecran, dm):
    definir_role(dm, "Membre MCO")
    dm.definir_responsable = type(dm).definir_responsable.__get__(dm)
    assert dm.definir_responsable(ecran.id_resp, False) is False
    assert dm.query_strict("SELECT COUNT(*) FROM utilisateur_responsable WHERE id_utilisateur = ?",
                           (ecran.id_resp,)) == [(1,)]


# --------------------------------------------------------------------- boîte « Modifier utilisateur » (modale : on intercepte son ouverture)
def _ouvrir_modification(ecran, monkeypatch, email, action=None):
    """Ouvre la boîte de modification sur la ligne `email`, relève l'état des cases, puis la ferme (Annuler)."""
    from PyQt5.QtWidgets import QCheckBox, QDialog
    releve = {}

    def faux_exec(dialogue):
        cases = {c.text(): c for c in dialogue.findChildren(QCheckBox)}
        releve["actif"] = cases["Utilisateur actif"]
        releve["responsable"] = next(c for t, c in cases.items() if t.startswith("Responsable ES-PASS"))
        releve["etats"] = {"actif": releve["actif"].isChecked(), "responsable": releve["responsable"].isChecked(),
                           "responsable_actif": releve["responsable"].isEnabled(),
                           "infobulle": releve["responsable"].toolTip()}
        if action:
            action(releve)
            return QDialog.Accepted
        return QDialog.Rejected

    monkeypatch.setattr(QDialog, "exec_", faux_exec)
    ecran.tableau_utilisateurs.setCurrentCell(_ligne(ecran, email), 0)
    ecran.modifier_utilisateur()
    return releve["etats"]


def test_boite_de_modification_prechoisit_actif_et_responsable(ecran, monkeypatch):
    etats = _ouvrir_modification(ecran, monkeypatch, "oui@x.fr")
    assert etats["actif"] is True                    # avant : toujours décochée (le texte « ✅ Actif » != « Actif »)
    assert etats["responsable"] is True and etats["responsable_actif"] is True


def test_boite_de_modification_utilisateur_inactif_non_responsable(ecran, monkeypatch):
    etats = _ouvrir_modification(ecran, monkeypatch, "non@x.fr")
    assert etats["actif"] is False and etats["responsable"] is False and etats["responsable_actif"] is True


def test_boite_de_modification_sans_table_case_grisee(app_qt, dm, monkeypatch):
    from app.views import pass_users_view
    from app.views.users import actions_mixin
    monkeypatch.setattr(actions_mixin, "QMessageBox", FausseBoite)
    monkeypatch.setattr(pass_users_view, "DataManager", lambda: dm)
    dm.is_current_user_admin = lambda: True
    _sans_table(dm)
    fenetre = pass_users_view.GestionUtilisateursDialog()
    etats = _ouvrir_modification(fenetre, monkeypatch, "j@x.fr")
    assert etats["responsable_actif"] is False and "001_utilisateur_responsable.sql" in etats["infobulle"]


def test_modification_enregistre_le_nouveau_statut_responsable(ecran, dm, monkeypatch):
    """Cocher « Responsable » dans la boîte puis valider : enregistré, et l'activité de l'utilisateur est conservée."""
    identifiant = dm.get_id_utilisateur_par_email("non@x.fr")
    dm.update_strict("UPDATE utilisateurs SET actif = 1 WHERE id_utilisateur = ?", (identifiant,))
    ecran.load_utilisateurs()
    _ouvrir_modification(ecran, monkeypatch, "non@x.fr", action=lambda r: r["responsable"].setChecked(True))
    assert dm.query_strict("SELECT COUNT(*) FROM utilisateur_responsable WHERE id_utilisateur = ?",
                           (identifiant,)) == [(1,)]
    assert dm.query_strict("SELECT actif FROM utilisateurs WHERE id_utilisateur = ?", (identifiant,)) == [(1,)]
    assert any("Désormais responsable ES-PASS" in texte for _, _, texte in FausseBoite.appels)


def test_modification_sans_toucher_n_active_ni_ne_desactive_personne(ecran, dm, monkeypatch):
    """Régression : valider sans rien changer désactivait l'utilisateur (case « actif » relue à tort décochée)."""
    _ouvrir_modification(ecran, monkeypatch, "oui@x.fr", action=lambda r: None)
    assert dm.query_strict("SELECT actif FROM utilisateurs WHERE email = 'oui@x.fr'") == [(1,)]


# --------------------------------------------------------------------- refonte de l'écran : synthèse, filtres, boutons, pastilles, matrice
def _tuiles(ecran):
    return {cle: label.text() for cle, label in ecran.tuiles_utilisateurs.items()}


def test_tuiles_de_synthese(ecran):
    # schéma de test : Dupont (actif, non responsable) + Resp (actif, responsable) + Inactif (inactif)
    assert _tuiles(ecran) == {"total": "3", "actifs": "2", "admins": "0", "responsables": "1"}


def test_tuile_responsables_non_applicable_sans_table(app_qt, dm, monkeypatch):
    from app.views import pass_users_view
    monkeypatch.setattr(pass_users_view, "DataManager", lambda: dm)
    dm.is_current_user_admin = lambda: True
    _sans_table(dm)
    fenetre = pass_users_view.GestionUtilisateursDialog()
    assert fenetre.tuiles_utilisateurs["responsables"].text() == "n/a"


def test_les_tuiles_suivent_les_modifications(ecran, dm):
    dm.update_strict("UPDATE utilisateurs SET actif = 1, id_role = 3 WHERE email = 'non@x.fr'")
    ecran.load_utilisateurs()
    assert _tuiles(ecran)["actifs"] == "3" and _tuiles(ecran)["admins"] == "1"


def _visibles(ecran):
    t = ecran.tableau_utilisateurs
    return [t.item(i, 3).text() for i in range(t.rowCount()) if not t.isRowHidden(i)]


def test_recherche_par_nom_prenom_et_email(ecran):
    for saisie, attendu in [("resp", ["oui@x.fr"]), ("oui", ["oui@x.fr"]),            # nom, prénom
                            ("non@x", ["non@x.fr"]), ("Jean Dupont", ["j@x.fr"]),     # e-mail, « prénom nom »
                            ("dupont jean", ["j@x.fr"]), ("zzz", [])]:
        ecran.search_input.setText(saisie)
        assert _visibles(ecran) == attendu, saisie
    ecran.search_input.setText("")
    assert len(_visibles(ecran)) == 3


def test_la_recherche_porte_aussi_sur_l_email(ecran):
    """Régression : la recherche lisait la colonne Prénom à la place de l'e-mail."""
    ecran.search_input.setText("@x.fr")
    assert len(_visibles(ecran)) == 3


def test_filtre_par_role(ecran):
    ecran.combo_filtre_role.setCurrentIndex(ecran.combo_filtre_role.findData("Membre MCO"))
    assert _visibles(ecran) == ["oui@x.fr"]


def test_filtre_par_statut(ecran):
    ecran.combo_filtre_statut.setCurrentIndex(ecran.combo_filtre_statut.findData(False))
    assert _visibles(ecran) == ["non@x.fr"]


def test_filtre_par_responsable(ecran):
    ecran.combo_filtre_responsable.setCurrentIndex(ecran.combo_filtre_responsable.findData(True))
    assert _visibles(ecran) == ["oui@x.fr"]
    ecran.combo_filtre_responsable.setCurrentIndex(ecran.combo_filtre_responsable.findData(False))
    assert sorted(_visibles(ecran)) == ["j@x.fr", "non@x.fr"]


def test_filtres_combines_et_compteur(ecran):
    ecran.combo_filtre_statut.setCurrentIndex(ecran.combo_filtre_statut.findData(True))
    ecran.search_input.setText("resp")
    assert _visibles(ecran) == ["oui@x.fr"]
    assert ecran.lbl_compteur_utilisateurs.text() == "1 utilisateur(s) affiché(s) sur 3"


def test_boutons_desactives_sans_selection(ecran):
    for bouton in (ecran.btn_modifier, ecran.btn_activer, ecran.btn_desactiver, ecran.btn_supprimer):
        assert not bouton.isEnabled()


def test_boutons_selon_le_statut_de_la_ligne_selectionnee(ecran):
    t = ecran.tableau_utilisateurs
    t.selectRow(_ligne(ecran, "oui@x.fr"))                                   # actif
    assert ecran.btn_modifier.isEnabled() and ecran.btn_supprimer.isEnabled()
    assert ecran.btn_desactiver.isEnabled() and not ecran.btn_activer.isEnabled()
    t.selectRow(_ligne(ecran, "non@x.fr"))                                   # inactif
    assert ecran.btn_activer.isEnabled() and not ecran.btn_desactiver.isEnabled()


def test_double_clic_ouvre_la_modification(ecran, monkeypatch):
    appels = []
    monkeypatch.setattr(type(ecran), "modifier_utilisateur", lambda self: appels.append(1))
    ecran.tableau_utilisateurs.cellDoubleClicked.emit(0, 0)
    assert appels == [1]


def test_role_statut_et_responsable_sont_des_pastilles(ecran):
    from app.views.users.widgets import ROLE_PASTILLE
    t = ecran.tableau_utilisateurs
    ligne = _ligne(ecran, "oui@x.fr")
    for colonne in (4, 5, 6):
        assert t.item(ligne, colonne).data(ROLE_PASTILLE)                       # (fond, texte)
    assert t.item(_ligne(ecran, "non@x.fr"), 6).data(ROLE_PASTILLE) is None     # « — » : pas de pastille
    assert t.item(ligne, 5).text() == "Actif" and t.item(_ligne(ecran, "non@x.fr"), 5).text() == "Inactif"


def test_les_pastilles_sont_dessinees(ecran):
    """Le fond de la pastille « Actif » est réellement peint dans la cellule (délégué de dessin)."""
    from PyQt5.QtGui import QColor
    ecran.resize(1200, 700)
    ecran.show()
    t = ecran.tableau_utilisateurs
    t.clearSelection()
    ligne = _ligne(ecran, "oui@x.fr")
    zone = t.visualRect(t.model().index(ligne, 5))
    image = t.viewport().grab().toImage()
    echantillon = QColor(image.pixel(zone.center().x() - 18, zone.center().y()))
    assert echantillon.name().upper() == "#E6F4EC"
    ecran.hide()


def test_la_selection_ne_decale_plus_le_texte(ecran):
    from app.styles import style
    assert "padding: 0px" in style.TABLE_ITEM_STYLE and ":selected" in style.TABLE_ITEM_STYLE
    assert "border" not in style.TABLE_ITEM_STYLE            # un border sur ::item casserait le retour à la ligne


def test_matrice_affichee_depuis_les_permissions(ecran):
    from app.utils.auth import has_permission
    from app.utils.matrice_droits import MATRICE_DROITS, ROLES_MATRICE
    matrice = ecran.tableau_matrice
    assert matrice.rowCount() == len(MATRICE_DROITS)
    for ligne, (libelle, cle) in enumerate(MATRICE_DROITS):
        assert matrice.item(ligne, 0).text() == libelle
        for colonne, role in enumerate(ROLES_MATRICE, start=1):
            attendu = True if cle is None else has_permission(role, cle)
            assert matrice.item(ligne, colonne).data(Qt.UserRole) is attendu
            assert matrice.item(ligne, colonne).text() == ("✓" if attendu else "—")


def test_description_du_role_suit_le_choix(ecran):
    ecran.combo_role_new.setCurrentIndex(0)
    consultant = ecran.lbl_description_role.text()
    ecran.combo_role_new.setCurrentIndex(2)
    assert ecran.lbl_description_role.text() != consultant and "Tous les droits" in ecran.lbl_description_role.text()
