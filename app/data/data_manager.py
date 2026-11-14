"""
Module de gestion des données SQLite pour ES-PASS
Gère toutes les interactions avec la base de données
CENTRALISATION COMPLÈTE - Aucun accès SQLite direct dans les vues
"""

import sqlite3
from typing import List, Optional, Tuple
from contextlib import contextmanager
import os

import getpass
import weakref
import win32com.client

from app.data.data_config import loadConfig
from app.data.mixins.config_mixin import ConfigMixin
from app.data.mixins.referentiels_mixin import ReferentielsMixin
from app.data.mixins.referentiels_admin_mixin import ReferentielsAdminMixin
from app.data.mixins.users_mixin import UsersMixin
from app.data.mixins.demandes_mixin import DemandesMixin
from app.data.mixins.collecte_mixin import CollecteMixin
from app.data.mixins.stats_mixin import StatsMixin


def get_windows_user_info():
    """
    Récupère les informations de l'utilisateur via Outlook.
    Retourne un dict avec 'error' si Outlook n'est pas disponible.
    """
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        session = outlook.Session
        account = session.CurrentUser

        # account.AddressEntry contient les infos du user connecté
        ae = account.AddressEntry

        # Si c'est un compte Exchange/AAD, on peut accéder aux propriétés détaillées
        if ae.Type == "EX":
            exch_user = ae.GetExchangeUser()
            if exch_user:
                firstname = exch_user.FirstName or ''
                lastname = exch_user.LastName or ''
                return {
                    "username": getpass.getuser(),
                    "display_name": exch_user.Name,
                    "firstname": firstname,
                    "lastname": lastname,
                    "fullname": f"{firstname} {lastname}".strip(),
                    "email": exch_user.PrimarySmtpAddress,
                    "sid": exch_user.id,
                    "error": None
                }

        # fallback (rarement utile)
        return {
            "display_name": ae.Name,
            "firstname": None,
            "lastname": None,
            "email": ae.Address,
            "error": None
        }

    except Exception as e:
        return {
            "error": str(e),
            "error_type": "outlook_not_running"
        }


class DataManager(ConfigMixin, ReferentielsMixin, ReferentielsAdminMixin, UsersMixin, DemandesMixin, CollecteMixin, StatsMixin):
    """
    Gestionnaire centralisé pour tous les accès à la base de données SQLite
    """

    # Instances vivantes : permet de rafraîchir leurs listes de valeurs après une modification des référentiels
    _instances = weakref.WeakSet()

    def __init__(self):
        """
        Initialise le gestionnaire de données
        Args:
            db_path: Chemin vers la base de données SQLite
        """
        self.conf = loadConfig()
        self.db_path = self.conf.get("sqlite_path", "")
        # ✅ AJOUT : Cache permanent utilisateur
        self._userwindows = None

        # Vérifier que le chemin est défini
        if not self.db_path:
            raise Exception("Aucun chemin de base de données n'est configuré dans config.json")

        # Vérifier que le fichier existe
        if not os.path.exists(self.db_path):
            raise Exception(
                f"Base de données introuvable : {self.db_path}\n"
                f"Vérifiez que le disque réseau est mappé et accessible."
            )

        # Tester la connexion réelle

        self.liste_valeurs = {}
        self.id_mapping = {}
        self.sous_categories_by_categorie = {}
        self.sous_categories_id_mapping = {}
        self.sous_categories_ids_by_categorie = {}
        DataManager._instances.add(self)
        self._load_reference_data()

    @contextmanager
    def _get_connection(self):
        """
        Context manager pour gérer les connexions à la base de données
        Garantit que les connexions sont toujours fermées correctement
        
        Yields:
            tuple: (connection, cursor)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Base sur partage réseau : WAL interdit, synchronous=FULL pour
            # éviter toute corruption en cas de coupure réseau / plantage poste.
            conn.execute('PRAGMA busy_timeout=15000;')   # 15 s (latence SMB)
            conn.execute('PRAGMA journal_mode=DELETE;')
            conn.execute('PRAGMA synchronous=FULL;')
            conn.execute('PRAGMA cache_size=-16000;')    # 16 Mo
            conn.execute('PRAGMA temp_store=MEMORY;')
            yield conn, cursor
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def _get_windows_user(self) -> dict:
        """Utilisateur Windows/Outlook, mis en cache s'il a été résolu sans erreur."""
        if self._userwindows:
            return self._userwindows
        info = get_windows_user_info()
        if not info.get("error"):
            self._userwindows = info
        return info

    def _verify_database(self):
        """Vérifie que la base de données existe"""
        if not os.path.exists(self.db_path):
            print(f"⚠️ ATTENTION : Base de données introuvable : {self.db_path}")
            return False
        print(f"✅ Base de données trouvée : {self.db_path}")
        return True


    def _execute_query(self, query: str, params: tuple = ()) -> Optional[List[Tuple]]:
        """
        Exécute une requête SQL SELECT et retourne les résultats
        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (tuple)
        Returns:
            Liste de tuples avec les résultats, ou None en cas d'erreur
        """
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(query, params)
                results = cursor.fetchall()
                return results
        except Exception as e:
            print(f"❌ Erreur SQL (SELECT) : {e}")
            print(f"   Requête : {query}")
            return None

    def execute_query(self, query: str, params: tuple = ()) -> Optional[List[Tuple]]:
        """
        Méthode publique pour exécuter une requête SQL SELECT
        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (tuple)
        Returns:
            Liste de tuples avec les résultats, ou None en cas d'erreur
        """
        return self._execute_query(query, params)

    def _execute_update(self, query: str, params: tuple = ()) -> bool:
        """
        Exécute une requête SQL UPDATE/INSERT/DELETE
        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (tuple)
        Returns:
            True si succès, False sinon
        """
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Erreur SQL (UPDATE) : {e}")
            print(f"   Requête : {query}")
            return False

    def _execute_many(self, query: str, params: tuple = ()) -> bool:
        """
        Exécute une requête SQL UPDATE/INSERT/DELETE
        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (tuple)
        Returns:
            True si succès, False sinon
        """
        try:
            with self._get_connection() as (conn, cursor):
                cursor.executemany(query, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ Erreur SQL (executemany) : {e}")
            print(f"   Requête : {query}")
            return False

    def execute_many(self, query: str, params: tuple = ()) -> bool:
        return self._execute_many(query, params)

    def execute_update(self, query: str, params: tuple = ()) -> bool:
        """
        Méthode publique pour exécuter une requête SQL UPDATE/INSERT/DELETE
        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (tuple)
        Returns:
            True si succès, False sinon
        """
        return self._execute_update(query, params)


    # ----------------------------------
    # ========================================================================
    # GESTION DES UTILISATEURS
    # ========================================================================


    # ========================================================================
    # GESTION DES COLLECTES
    # ========================================================================


    # ========================================================================
    # GESTION DES STATISTIQUES
    # ========================================================================


    # ========================================================================
    # GESTION DES DEMANDES
    # ========================================================================


    # ========================================================================
    # GESTION DES LISTES DE VALEURS
    # ========================================================================


    # ========================================================================
    # GESTION DES RÔLES
    # ========================================================================


        # ========================================================================
        # GESTION DES UTILISATEURS - SÉCURITÉ ET DROITS
        # ========================================================================


# Test du module
if __name__ == "__main__":
    dm = DataManager()
    print("\n" + "=" * 80)
    print("TEST DU MODULE DATA_MANAGER")
    print("=" * 80)
    print("\n1️⃣ UTILISATEUR :")
    user_id = dm.creer_utilisateur("testnom")
    print(f"  ID nouvel utilisateur : {user_id}")
    print("=" * 80)
