"""Responsables ES-PASS : utilisateurs proposés dans les listes « Responsable » des demandes.

La liste est portée par la table `utilisateur_responsable` (script `scripts/sql/001_utilisateur_responsable.sql`) :
un utilisateur est responsable ES-PASS s'il y figure. L'administrateur la gère depuis l'écran Utilisateurs.

Compatibilité : tant que la table n'existe pas (script non appliqué), `get_responsables` retombe sur tous les
utilisateurs actifs (comportement d'avant) et `definir_responsable` refuse avec un message explicite.
"""

import logging
from typing import Dict, List, Optional

from app.data.sql_utils import sql_nom_utilisateur_ou_repere

logger = logging.getLogger(__name__)


class ResponsablesMixin:
    """Liste des responsables ES-PASS (table utilisateur_responsable)."""

    TABLE_RESPONSABLES = "utilisateur_responsable"
    SCRIPT_RESPONSABLES = "scripts/sql/001_utilisateur_responsable.sql"

    def table_responsables_existe(self) -> bool:
        """True si la table `utilisateur_responsable` existe (seul un résultat positif est mis en cache)."""
        if getattr(self, "_table_responsables_ok", False):
            return True
        lignes = self._execute_query("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                                     (self.TABLE_RESPONSABLES,))
        existe = bool(lignes)
        if existe:
            self._table_responsables_ok = True
        return existe

    def _message_table_absente(self) -> str:
        return (f"La table {self.TABLE_RESPONSABLES} n'existe pas dans la base : exécutez d'abord le script "
                f"{self.SCRIPT_RESPONSABLES}.")

    def get_responsables(self) -> List[Dict]:
        """Utilisateurs actifs proposés comme responsables d'une demande, triés par nom.

        - table présente : seuls les utilisateurs cochés « Responsable ES-PASS » ;
        - table absente  : tous les utilisateurs actifs (ancien comportement), avec un avertissement journalisé.

        Chaque entrée : id, nom, prenom, role, nom_complet (nom prénom, à défaut e-mail, sinon repère #N).
        """
        nom = sql_nom_utilisateur_ou_repere('u', 'u.id_utilisateur')
        if self.table_responsables_existe():
            jointure = f"JOIN {self.TABLE_RESPONSABLES} ur ON ur.id_utilisateur = u.id_utilisateur"
        else:
            jointure = ""
            if not getattr(self, "_avertissement_table_responsables", False):
                self._avertissement_table_responsables = True
                logger.warning("%s Liste des responsables : tous les utilisateurs actifs sont proposés.",
                               self._message_table_absente())
        query = f"""
            SELECT u.id_utilisateur, u.nom, u.prenom, r.libelle_role, {nom} AS nom_complet
            FROM utilisateurs u
            {jointure}
            LEFT JOIN roles r ON r.id_role = u.id_role
            WHERE u.actif = 1
            ORDER BY nom_complet COLLATE NOCASE
        """
        lignes = self._execute_query(query)
        return [{'id': r[0], 'nom': r[1], 'prenom': r[2], 'role': r[3], 'nom_complet': r[4]}
                for r in (lignes or [])]

    def definir_responsable(self, id_utilisateur: int, est_responsable: bool) -> bool:
        """Coche ou décoche « Responsable ES-PASS » pour un utilisateur. Réservé à l'Administrateur.

        Décocher n'enlève pas l'utilisateur des demandes qui lui sont déjà affectées. Opération idempotente.
        Retourne False (et renseigne `last_error`) en cas de refus, de table absente ou d'utilisateur inconnu.
        """
        if self._refuser_si_pas_droit('gerer_utilisateurs', "gérer les responsables ES-PASS"):
            return False
        if not self.table_responsables_existe():
            self.last_error = self._message_table_absente()
            return False
        if not est_responsable:
            return self._execute_update(f"DELETE FROM {self.TABLE_RESPONSABLES} WHERE id_utilisateur = ?",
                                        (id_utilisateur,))
        connu = self._execute_query("SELECT 1 FROM utilisateurs WHERE id_utilisateur = ?", (id_utilisateur,))
        if not connu:
            if connu is not None:
                self.last_error = f"Utilisateur #{id_utilisateur} introuvable."
            return False
        auteur = str((self.get_current_user() or {}).get('id', ''))
        return self._execute_update(
            f"INSERT OR IGNORE INTO {self.TABLE_RESPONSABLES} (id_utilisateur, ajoute_par) VALUES (?, ?)",
            (id_utilisateur, int(auteur) if auteur.isdigit() else None))

    def get_id_utilisateur_par_email(self, email: str) -> Optional[int]:
        lignes = self._execute_query("SELECT id_utilisateur FROM utilisateurs WHERE email = ?", (email,))
        return lignes[0][0] if lignes else None

    def get_nb_demandes_affectees(self, id_utilisateur: int) -> int:
        """Nombre de demandes (tous états) dont l'utilisateur est le responsable."""
        lignes = self._execute_query("SELECT COUNT(*) FROM demandes WHERE id_responsable = ?", (id_utilisateur,))
        return lignes[0][0] if lignes else 0
