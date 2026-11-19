"""Scripts de modification de la base (scripts/sql) : création de utilisateur_responsable, reprise des données, retour.

Les scripts sont exécutés tels que livrés au client, sur une base de test.
"""

import sqlite3

import pytest

from conftest import SCRIPT_RESPONSABLES, SCRIPT_RESPONSABLES_RETOUR, _creer_schema, executer_script


@pytest.fixture
def base():
    """Base SANS la table des responsables (état avant mise à jour), avec quelques utilisateurs et demandes."""
    conn = sqlite3.connect(":memory:")
    _creer_schema(conn, avec_table_responsables=False)
    conn.execute("DELETE FROM utilisateurs")
    for ident, nom, actif in [(1, "ActifAvecDemandes", 1), (2, "ActifSansDemande", 1), (3, "InactifAvecDemandes", 0),
                              (4, "ActifAvecDemandes2", 1)]:
        conn.execute("INSERT INTO utilisateurs (id_utilisateur, nom, prenom, email, id_role, actif) "
                     "VALUES (?, ?, 'P', ?, 2, ?)", (ident, nom, f"{nom}@x.fr", actif))
    for responsable in (1, 1, 3, 4, None):
        conn.execute("INSERT INTO demandes (id_etat, id_responsable) VALUES (1, ?)", (responsable,))
    conn.commit()
    yield conn
    conn.close()


def _table_existe(conn):
    return conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'utilisateur_responsable'").fetchone()[0] == 1


def _responsables(conn):
    return sorted(r[0] for r in conn.execute("SELECT id_utilisateur FROM utilisateur_responsable"))


# --------------------------------------------------------------------- script 001
def test_le_script_cree_la_table_et_le_trigger(base):
    assert not _table_existe(base)
    executer_script(base, SCRIPT_RESPONSABLES)
    assert _table_existe(base)
    colonnes = [c[1] for c in base.execute("PRAGMA table_info(utilisateur_responsable)")]
    assert colonnes == ["id_utilisateur", "date_ajout", "ajoute_par"]
    assert base.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger' "
                        "AND name = 'trg_utilisateur_responsable_suppression'").fetchone()[0] == 1


def test_initialisation_avec_les_actifs_deja_responsables_de_demandes(base):
    executer_script(base, SCRIPT_RESPONSABLES)
    # 1 et 4 : actifs avec demandes. 2 : aucune demande. 3 : a des demandes mais est inactif.
    assert _responsables(base) == [1, 4]


def test_le_script_est_rejouable_sans_doublon_ni_perte(base):
    executer_script(base, SCRIPT_RESPONSABLES)
    base.execute("INSERT INTO utilisateur_responsable (id_utilisateur, ajoute_par) VALUES (2, 1)")   # ajout via l'IHM
    base.execute("DELETE FROM utilisateur_responsable WHERE id_utilisateur = 4")                      # retrait via l'IHM
    base.commit()
    avant_date = base.execute("SELECT date_ajout FROM utilisateur_responsable WHERE id_utilisateur = 1").fetchone()
    executer_script(base, SCRIPT_RESPONSABLES)
    assert _responsables(base) == [1, 2, 4]          # 4 est réajouté par l'initialisation, 2 (ajout manuel) est conservé
    assert base.execute("SELECT date_ajout FROM utilisateur_responsable WHERE id_utilisateur = 1").fetchone() == avant_date


def test_la_date_d_ajout_est_renseignee_par_defaut(base):
    executer_script(base, SCRIPT_RESPONSABLES)
    assert all(d[0] for d in base.execute("SELECT date_ajout FROM utilisateur_responsable"))


def test_le_script_ne_modifie_aucune_table_existante(base):
    avant = {t: base.execute(f"SELECT * FROM {t}").fetchall() for t in ("utilisateurs", "demandes", "roles")}
    structure = {t: base.execute(f"PRAGMA table_info({t})").fetchall() for t in ("utilisateurs", "demandes", "roles")}
    executer_script(base, SCRIPT_RESPONSABLES)
    for t in avant:
        assert base.execute(f"SELECT * FROM {t}").fetchall() == avant[t]
        assert base.execute(f"PRAGMA table_info({t})").fetchall() == structure[t]


def test_le_trigger_retire_la_ligne_quand_l_utilisateur_est_supprime(base):
    executer_script(base, SCRIPT_RESPONSABLES)
    base.execute("DELETE FROM utilisateurs WHERE id_utilisateur = 1")
    assert _responsables(base) == [4]


def test_le_script_ne_contient_aucune_suppression_de_donnees():
    with open(SCRIPT_RESPONSABLES, encoding="utf8") as f:
        instructions = [ligne for ligne in f.read().splitlines() if not ligne.strip().startswith("--")]
    code = "\n".join(instructions).upper()
    assert "DROP " not in code and "ALTER " not in code
    assert code.count("DELETE FROM") == 1                                # uniquement dans le trigger de nettoyage


def test_l_option_tous_les_membres_mco_reste_commentee():
    with open(SCRIPT_RESPONSABLES, encoding="utf8") as f:
        lignes = f.read().splitlines()
    option = [l for l in lignes if "r.libelle_role IN" in l]
    assert option and all(l.lstrip().startswith("--") for l in option)


# --------------------------------------------------------------------- retour arrière
def test_le_retour_arriere_supprime_la_table_et_le_trigger(base):
    executer_script(base, SCRIPT_RESPONSABLES)
    executer_script(base, SCRIPT_RESPONSABLES_RETOUR)
    assert not _table_existe(base)
    assert base.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'trigger'").fetchone()[0] == 0


def test_le_retour_arriere_laisse_utilisateurs_et_demandes_intacts(base):
    executer_script(base, SCRIPT_RESPONSABLES)
    avant = {t: base.execute(f"SELECT * FROM {t}").fetchall() for t in ("utilisateurs", "demandes")}
    executer_script(base, SCRIPT_RESPONSABLES_RETOUR)
    assert {t: base.execute(f"SELECT * FROM {t}").fetchall() for t in avant} == avant


def test_le_retour_arriere_est_rejouable_et_sans_effet_sans_table(base):
    executer_script(base, SCRIPT_RESPONSABLES_RETOUR)                    # table jamais créée : aucune erreur
    executer_script(base, SCRIPT_RESPONSABLES)
    executer_script(base, SCRIPT_RESPONSABLES_RETOUR)
    executer_script(base, SCRIPT_RESPONSABLES_RETOUR)
    assert not _table_existe(base)


def test_aller_retour_aller_redonne_la_meme_liste(base):
    executer_script(base, SCRIPT_RESPONSABLES)
    premiere = _responsables(base)
    executer_script(base, SCRIPT_RESPONSABLES_RETOUR)
    executer_script(base, SCRIPT_RESPONSABLES)
    assert _responsables(base) == premiere
