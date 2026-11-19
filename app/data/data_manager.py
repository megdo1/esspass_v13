"""
Module de gestion des données SQLite pour ES-PASS
Gère toutes les interactions avec la base de données
CENTRALISATION COMPLÈTE - Aucun accès SQLite direct dans les vues
"""

import sqlite3
from typing import List, Optional, Tuple
from contextlib import contextmanager
import logging
import os
import time

import getpass
import weakref

try:
    import win32com.client
except ImportError:      # hors Windows / pywin32 absent (tests, CI) : identité Outlook indisponible
    win32com = None

from app.data.data_config import loadConfig
from app.data.errors import ConflitModificationError, DatabaseError  # noqa: F401 (réexport)
from app.data.mixins.config_mixin import ConfigMixin
from app.data.mixins.referentiels_mixin import ReferentielsMixin
from app.data.mixins.referentiels_admin_mixin import ReferentielsAdminMixin
from app.data.mixins.users_mixin import UsersMixin
from app.data.mixins.demandes_mixin import DemandesMixin
from app.data.mixins.collecte_mixin import CollecteMixin
from app.data.mixins.stats_mixin import StatsMixin

logger = logging.getLogger(__name__)


def get_windows_user_info():
    """
    Récupère les informations de l'utilisateur via Outlook.
    Retourne un dict avec 'error' si Outlook n'est pas disponible.
    """
    try:
        if win32com is None:
            raise RuntimeError("pywin32 non installé")
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
        logger.warning("Identité Outlook indisponible : %s", e)
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
        # Dernière erreur d'accès base (None si la dernière opération a réussi).
        # Permet de distinguer « aucun résultat » d'une erreur après un appel à
        # _execute_query / _execute_update qui, eux, gardent leur contrat (None / False).
        self.last_error: Optional[str] = None
        # Compteur d'erreurs d'accès base depuis le démarrage : une vue le relève avant/après un
        # chargement pour savoir si « aucune donnée » vient en réalité d'une erreur.
        self.error_count: int = 0
        # Rôle de l'utilisateur connecté, lu une fois (voir UsersMixin._role_courant)
        self._role_cache: Optional[str] = None

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
        self._charger_donnees_reference_avec_reprises()

    # Reprises au démarrage : un verrou de la base (autre poste en écriture, antivirus, synchro...) est
    # en général passager ; sans reprise, l'application s'arrêtait au premier « database is locked ».
    TENTATIVES_DEMARRAGE = 3
    PAUSE_ENTRE_TENTATIVES = 3.0   # secondes (s'ajoute au busy_timeout de 15 s de chaque requête)

    def _charger_donnees_reference_avec_reprises(self) -> None:
        for tentative in range(1, self.TENTATIVES_DEMARRAGE + 1):
            for cache in (self.liste_valeurs, self.id_mapping, self.sous_categories_by_categorie,
                          self.sous_categories_id_mapping, self.sous_categories_ids_by_categorie):
                cache.clear()          # un échec partiel ne doit pas laisser des listes à moitié remplies
            try:
                self._load_reference_data()
                return
            except DatabaseError:
                if tentative == self.TENTATIVES_DEMARRAGE:
                    raise
                logger.warning("Chargement des listes impossible (tentative %d/%d), nouvel essai dans %.0f s",
                               tentative, self.TENTATIVES_DEMARRAGE, self.PAUSE_ENTRE_TENTATIVES)
                time.sleep(self.PAUSE_ENTRE_TENTATIVES)

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
        except Exception:
            if conn:
                conn.rollback()
            raise
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

    def _record_error(self, kind: str, query: str, exc: Exception) -> None:
        """Journalise une erreur d'accès base et mémorise le message dans `last_error`."""
        self.last_error = f"{kind} : {exc}"
        self.error_count += 1
        logger.error("Erreur SQL (%s) : %s | requête : %s", kind, exc, " ".join(query.split())[:500],
                     exc_info=True)

    def _execute_query(self, query: str, params: tuple = ()) -> Optional[List[Tuple]]:
        """
        Exécute une requête SQL SELECT et retourne les résultats
        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête (tuple)
        Returns:
            Liste de tuples avec les résultats, ou None en cas d'erreur
            (dans ce cas `self.last_error` contient le message ; il vaut None après un succès)
        """
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(query, params)
                results = cursor.fetchall()
            self.last_error = None
            return results
        except Exception as e:
            self._record_error("SELECT", query, e)
            return None

    def query_strict(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Comme `_execute_query` mais lève `DatabaseError` au lieu de renvoyer None."""
        results = self._execute_query(query, params)
        if results is None:
            raise DatabaseError(self.last_error or "Erreur d'accès à la base de données")
        return results

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
            True si succès, False sinon (`self.last_error` contient alors le message)
        """
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(query, params)
                conn.commit()
            self.last_error = None
            return True
        except Exception as e:
            self._record_error("UPDATE", query, e)
            return False

    def update_strict(self, query: str, params: tuple = ()) -> None:
        """Comme `_execute_update` mais lève `DatabaseError` en cas d'échec."""
        if not self._execute_update(query, params):
            raise DatabaseError(self.last_error or "Erreur d'accès à la base de données")

    def _execute_many(self, query: str, params: tuple = ()) -> bool:
        """
        Exécute une requête SQL en lot (executemany)
        Args:
            query: Requête SQL à exécuter
            params: Liste de tuples de paramètres
        Returns:
            True si succès, False sinon (`self.last_error` contient alors le message)
        """
        try:
            with self._get_connection() as (conn, cursor):
                cursor.executemany(query, params)
                conn.commit()
            self.last_error = None
            return True
        except Exception as e:
            self._record_error("executemany", query, e)
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
