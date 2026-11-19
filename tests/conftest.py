"""Fixtures : base SQLite temporaire (jamais la base de production) et DataManager branché dessus."""

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REF_TABLES = {
    "canaux": ("id_canal", "libelle_canal"),
    "domaines": ("id_domaine", "libelle_domaine"),
    "categories": ("id_categorie", "libelle_categorie"),
    "natures": ("id_nature", "libelle_nature"),
    "impacts": ("id_impact", "libelle_impact"),
    "urgences": ("id_urgence", "libelle_urgence"),
    "etats": ("id_etat", "libelle_etat"),
}


SCRIPT_RESPONSABLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                   "scripts", "sql", "001_utilisateur_responsable.sql")
SCRIPT_RESPONSABLES_RETOUR = SCRIPT_RESPONSABLES.replace(".sql", "_rollback.sql")


def executer_script(conn, chemin):
    with open(chemin, encoding="utf8") as f:
        conn.executescript(f.read())


def _creer_schema(conn, avec_table_responsables=True):
    for table, (id_col, lib_col) in REF_TABLES.items():
        conn.execute(f"CREATE TABLE {table} ({id_col} INTEGER PRIMARY KEY, {lib_col} TEXT, actif INTEGER DEFAULT 1)")
        conn.execute(f"INSERT INTO {table} ({lib_col}) VALUES ('A'), ('B')")
    conn.execute("""CREATE TABLE sous_categories (id_sous_categorie INTEGER PRIMARY KEY,
                    libelle_sous_categorie TEXT, id_categorie INTEGER, actif INTEGER DEFAULT 1)""")
    conn.execute("INSERT INTO sous_categories (libelle_sous_categorie, id_categorie) VALUES ('SC1', 1)")
    conn.execute("""CREATE TABLE utilisateurs (id_utilisateur INTEGER PRIMARY KEY, nom TEXT, prenom TEXT,
                    email TEXT, id_role INTEGER, actif INTEGER DEFAULT 1, created_at TEXT)""")
    conn.execute("CREATE TABLE roles (id_role INTEGER PRIMARY KEY, libelle_role TEXT)")
    conn.execute("INSERT INTO roles (id_role, libelle_role) VALUES (1, 'Consultant'), (2, 'Membre MCO'), (3, 'Administrateur')")
    conn.execute("INSERT INTO utilisateurs (nom, prenom, email, id_role) VALUES ('Dupont', 'Jean', 'j@x.fr', 1)")
    conn.execute("CREATE TABLE sequence_counter (prefix TEXT PRIMARY KEY, last_number INTEGER, description TEXT)")
    conn.execute("""CREATE TABLE demandes (
        id_demande INTEGER PRIMARY KEY, conversation_id TEXT, thread_key TEXT, libelle TEXT, sujet TEXT,
        resume TEXT, demandeur TEXT, date_reception TEXT, id_canal INTEGER, id_domaine INTEGER,
        id_responsable INTEGER, id_categorie INTEGER, id_sous_categorie INTEGER, id_nature INTEGER,
        id_impact INTEGER, id_urgence INTEGER, id_etat INTEGER, priorite_calculee TEXT,
        solution_suite_a_donner TEXT, commentaire TEXT, date_traitement TEXT,
        created_at TEXT, updated_at TEXT)""")
    conn.execute("CREATE TABLE pieces_jointes (id_piece INTEGER PRIMARY KEY, id_demande INTEGER)")
    conn.execute("""CREATE TABLE metadonnees_collecte (id_collecte INTEGER PRIMARY KEY,
                    id_utilisateur_lanceur INTEGER, date_collecte TEXT,
                    nb_nouvelles_demandes INTEGER, nb_emails_traites INTEGER, nb_total_demandes INTEGER)""")
    conn.execute("CREATE TABLE collecte_demandes (id_collecte INTEGER, id_demande INTEGER)")
    conn.execute("""CREATE TABLE colonnes_config (nom_colonne TEXT, libelle_affiche TEXT, champ_demande TEXT,
                    largeur_defaut INTEGER, visible INTEGER, ordre_affichage INTEGER, alignement TEXT,
                    tronquer_longueur INTEGER, type_colonne TEXT, id_utilisateur INTEGER)""")
    conn.execute("""CREATE TABLE parametres_app (cle TEXT PRIMARY KEY, valeur TEXT, description TEXT,
                    type_valeur TEXT, id_utilisateur INTEGER)""")
    if avec_table_responsables:
        executer_script(conn, SCRIPT_RESPONSABLES)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    conn = sqlite3.connect(path)
    _creer_schema(conn)
    conn.commit()
    conn.close()
    return str(path)


@pytest.fixture
def dm(db_path, monkeypatch):
    from app.data import data_manager as dm_module
    monkeypatch.setattr(dm_module, "loadConfig", lambda *a, **k: {"sqlite_path": db_path})
    manager = dm_module.DataManager()
    definir_role(manager, "Administrateur")
    return manager


def definir_role(manager, role):
    """Simule l'utilisateur connecté (pas d'Outlook dans les tests)."""
    manager.invalidate_role_cache()
    manager.get_current_user = lambda: ({"nom": "T", "prenom": "T", "role": role, "id": 1} if role else None)
