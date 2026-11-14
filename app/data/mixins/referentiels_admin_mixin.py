"""Administration des listes de valeurs (référentiels) : ajout, renommage, (dés)activation, suppression.

Règles de sécurité des données :
- seul un Administrateur peut modifier les listes ;
- une valeur utilisée par des demandes n'est jamais supprimée sans réaffectation : on la désactive
  (elle disparaît des listes de saisie mais reste affichée sur les demandes existantes) ;
- les valeurs référencées en dur par l'application (états, impacts/urgences, canal CRP, domaines OA/OT,
  natures Anomalie/Evolution) sont protégées ;
- les noms de tables/colonnes viennent exclusivement de la table REFERENTIELS ci-dessous (jamais de l'utilisateur).
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LIBELLE_MAX = 100

REFERENTIELS = {
    "canaux": {
        "titre": "Canaux", "icone": "📡", "table": "canaux", "id": "id_canal", "libelle": "libelle_canal",
        "fk": "id_canal", "modifiable": True, "reaffectable": True,
        "description": "Origine de la demande (appel, messagerie, animation...).",
    },
    "domaines": {
        "titre": "Domaines", "icone": "🏢", "table": "domaines", "id": "id_domaine", "libelle": "libelle_domaine",
        "fk": "id_domaine", "modifiable": True, "reaffectable": True,
        "description": "Périmètre métier concerné par la demande.",
    },
    "categories": {
        "titre": "Catégories", "icone": "🏷️", "table": "categories", "id": "id_categorie",
        "libelle": "libelle_categorie", "fk": "id_categorie", "modifiable": True, "reaffectable": False,
        "description": "Classement principal des demandes. Chaque catégorie regroupe des sous-catégories.",
    },
    "sous_categories": {
        "titre": "Sous-catégories", "icone": "🗂️", "table": "sous_categories", "id": "id_sous_categorie",
        "libelle": "libelle_sous_categorie", "fk": "id_sous_categorie", "modifiable": True, "reaffectable": True,
        "parent": "categories", "parent_fk": "id_categorie",
        "description": "Classement détaillé, rattaché à une catégorie.",
    },
    "natures": {
        "titre": "Natures", "icone": "🔖", "table": "natures", "id": "id_nature", "libelle": "libelle_nature",
        "fk": "id_nature", "modifiable": True, "reaffectable": True,
        "description": "Nature de la demande (anomalie, évolution, information...).",
    },
    "etats": {
        "titre": "États", "icone": "🚦", "table": "etats", "id": "id_etat", "libelle": "libelle_etat",
        "fk": "id_etat", "modifiable": False, "reaffectable": False,
        "raison": "Les états pilotent le cycle de vie des demandes, les statistiques et les rapports : "
                  "ils sont fixés par l'application.",
        "description": "Cycle de vie d'une demande.",
    },
    "impacts": {
        "titre": "Impacts", "icone": "💥", "table": "impacts", "id": "id_impact", "libelle": "libelle_impact",
        "fk": "id_impact", "modifiable": False, "reaffectable": False, "niveau": True,
        "raison": "Impact et urgence déterminent automatiquement la priorité (P1 à P4) : "
                  "leurs libellés sont utilisés par ce calcul et ne peuvent pas être modifiés.",
        "description": "Gravité de l'incident (entre dans le calcul de la priorité).",
    },
    "urgences": {
        "titre": "Urgences", "icone": "⏱️", "table": "urgences", "id": "id_urgence", "libelle": "libelle_urgence",
        "fk": "id_urgence", "modifiable": False, "reaffectable": False, "niveau": True,
        "raison": "Impact et urgence déterminent automatiquement la priorité (P1 à P4) : "
                  "leurs libellés sont utilisés par ce calcul et ne peuvent pas être modifiés.",
        "description": "Délai attendu de traitement (entre dans le calcul de la priorité).",
    },
}

# Valeurs référencées en dur par l'application : ni renommées, ni désactivées, ni supprimées.
VALEURS_PROTEGEES = {
    "canaux": {"CRP"},                    # canal des demandes créées par la collecte de mails
    "domaines": {"OA", "OT"},             # utilisés par les indicateurs OA / OT
    "natures": {"Anomalie", "Evolution"},  # utilisées par les rapports
}


class ReferentielsAdminMixin:
    """Ajout, renommage, désactivation et suppression des valeurs des listes de référence."""

    # ------------------------------------------------------------------ utilitaires
    @staticmethod
    def referentiel_meta(key: str) -> Dict:
        if key not in REFERENTIELS:
            raise ValueError(f"Liste inconnue : {key}")
        return REFERENTIELS[key]

    @staticmethod
    def est_valeur_protegee(key: str, libelle: str) -> bool:
        return (libelle or "") in VALEURS_PROTEGEES.get(key, set())

    @staticmethod
    def nettoyer_libelle(libelle: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Retourne (libellé nettoyé, message d'erreur)."""
        clean = " ".join((libelle or "").split())
        if not clean:
            return None, "Le libellé est obligatoire."
        if len(clean) > LIBELLE_MAX:
            return None, f"Le libellé est trop long ({len(clean)} caractères, maximum {LIBELLE_MAX})."
        if re.search(r"[\x00-\x1f\x7f]", clean):
            return None, "Le libellé contient des caractères non autorisés."
        return clean, None

    def _droits_referentiels(self) -> Optional[str]:
        """Retourne un message d'erreur si l'utilisateur n'a pas le droit de modifier les listes."""
        if not self.is_current_user_admin():
            return "Droits insuffisants : seul un Administrateur peut modifier les listes de valeurs."
        return None

    def _libelles_existants(self, cursor, key: str, exclude_id: Optional[int] = None) -> List[Tuple[int, str, Optional[str]]]:
        """Libellés déjà présents dans la portée d'unicité : toute la table (sous-catégories incluses)."""
        meta = REFERENTIELS[key]
        if meta.get("parent"):
            cursor.execute(
                f"SELECT t.{meta['id']}, t.{meta['libelle']}, p.{REFERENTIELS[meta['parent']]['libelle']} "
                f"FROM {meta['table']} t JOIN {REFERENTIELS[meta['parent']]['table']} p "
                f"ON p.{REFERENTIELS[meta['parent']]['id']} = t.{meta['parent_fk']}")
        else:
            cursor.execute(f"SELECT {meta['id']}, {meta['libelle']}, NULL FROM {meta['table']}")
        return [r for r in cursor.fetchall() if exclude_id is None or r[0] != exclude_id]

    def _doublon(self, cursor, key: str, libelle: str, exclude_id: Optional[int] = None) -> Optional[str]:
        cible = libelle.casefold()
        for _id, lib, parent in self._libelles_existants(cursor, key, exclude_id):
            if (lib or "").casefold() == cible:
                where = f" (catégorie « {parent} »)" if parent else ""
                return f"« {lib} » existe déjà{where}."
        return None

    def _rafraichir_listes(self):
        """Recharge les listes en mémoire de toutes les instances de DataManager du processus."""
        try:
            type(self).refresh_reference_data_all()
        except Exception:
            logger.exception("Rafraîchissement des listes de référence impossible")

    # ------------------------------------------------------------------ lecture
    def get_referentiel_items(self, key: str, include_inactive: bool = True) -> List[Dict]:
        """Valeurs d'une liste avec leur statut, leur nombre de demandes liées et leur éventuelle catégorie."""
        meta = self.referentiel_meta(key)
        cols = [f"t.{meta['id']}", f"t.{meta['libelle']}", "COALESCE(t.actif, 1)",
                f"(SELECT COUNT(*) FROM demandes d WHERE d.{meta['fk']} = t.{meta['id']})"]
        joins = ""
        if meta.get("parent"):
            p = REFERENTIELS[meta["parent"]]
            cols += [f"t.{meta['parent_fk']}", f"p.{p['libelle']}"]
            joins = f" JOIN {p['table']} p ON p.{p['id']} = t.{meta['parent_fk']}"
        else:
            cols += ["NULL", "NULL"]
        if meta.get("niveau"):
            cols.append("t.niveau")
        else:
            cols.append("NULL")
        if key == "categories":
            cols.append("(SELECT COUNT(*) FROM sous_categories sc WHERE sc.id_categorie = t.id_categorie)")
        else:
            cols.append("0")
        where = "" if include_inactive else " WHERE COALESCE(t.actif, 1) = 1"
        order = "p." + REFERENTIELS[meta["parent"]]["libelle"] + ", " if meta.get("parent") else ""
        query = (f"SELECT {', '.join(cols)} FROM {meta['table']} t{joins}{where} "
                 f"ORDER BY {order}t.{meta['libelle']} COLLATE NOCASE")
        rows = self._execute_query(query) or []
        return [{
            "id": r[0], "libelle": r[1], "actif": bool(r[2]), "nb_demandes": r[3],
            "parent_id": r[4], "parent_libelle": r[5], "niveau": r[6], "nb_enfants": r[7],
            "protege": (not meta["modifiable"]) or self.est_valeur_protegee(key, r[1]),
        } for r in rows]

    def get_reference_label(self, key: str, item_id) -> Optional[str]:
        """Libellé d'une valeur (active ou non), None si introuvable."""
        if not item_id or key not in REFERENTIELS:
            return None
        meta = REFERENTIELS[key]
        rows = self._execute_query(f"SELECT {meta['libelle']} FROM {meta['table']} WHERE {meta['id']} = ?", (item_id,))
        return rows[0][0] if rows else None

    # ------------------------------------------------------------------ rechargement du cache
    def reload_reference_data(self):
        """Recharge les listes en mémoire (après une modification)."""
        for d in (self.liste_valeurs, self.id_mapping, self.sous_categories_by_categorie,
                  self.sous_categories_id_mapping, self.sous_categories_ids_by_categorie):
            d.clear()
        self._load_reference_data()

    @classmethod
    def refresh_reference_data_all(cls):
        for dm in list(cls._instances):
            dm.reload_reference_data()

    # ------------------------------------------------------------------ écriture
    def add_referentiel_item(self, key: str, libelle: str, parent_id: Optional[int] = None) -> Tuple[bool, str]:
        meta = self.referentiel_meta(key)
        if not meta["modifiable"]:
            return False, meta.get("raison", "Cette liste n'est pas modifiable.")
        err = self._droits_referentiels()
        if err:
            return False, err
        clean, err = self.nettoyer_libelle(libelle)
        if err:
            return False, err
        try:
            with self._get_connection() as (conn, cursor):
                if meta.get("parent"):
                    p = REFERENTIELS[meta["parent"]]
                    cursor.execute(f"SELECT COALESCE(actif, 1) FROM {p['table']} WHERE {p['id']} = ?", (parent_id,))
                    row = cursor.fetchone()
                    if not row:
                        return False, "Choisissez la catégorie de rattachement."
                    if not row[0]:
                        return False, "La catégorie choisie est désactivée : réactivez-la d'abord."
                doublon = self._doublon(cursor, key, clean)
                if doublon:
                    return False, doublon
                if meta.get("parent"):
                    cursor.execute(f"INSERT INTO {meta['table']} ({meta['libelle']}, {meta['parent_fk']}, actif) "
                                   f"VALUES (?, ?, 1)", (clean, parent_id))
                else:
                    cursor.execute(f"INSERT INTO {meta['table']} ({meta['libelle']}, actif) VALUES (?, 1)", (clean,))
                conn.commit()
        except Exception as e:
            logger.exception("Ajout impossible dans %s", key)
            return False, f"Erreur technique : {e}"
        self._rafraichir_listes()
        return True, f"« {clean} » a été ajouté."

    def rename_referentiel_item(self, key: str, item_id: int, new_libelle: str) -> Tuple[bool, str]:
        meta = self.referentiel_meta(key)
        if not meta["modifiable"]:
            return False, meta.get("raison", "Cette liste n'est pas modifiable.")
        err = self._droits_referentiels()
        if err:
            return False, err
        clean, err = self.nettoyer_libelle(new_libelle)
        if err:
            return False, err
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(f"SELECT {meta['libelle']} FROM {meta['table']} WHERE {meta['id']} = ?", (item_id,))
                row = cursor.fetchone()
                if not row:
                    return False, "Cette valeur n'existe plus (actualisez la liste)."
                ancien = row[0]
                if self.est_valeur_protegee(key, ancien):
                    return False, f"« {ancien} » est utilisé par l'application : il ne peut pas être renommé."
                if clean == ancien:
                    return False, "Le libellé n'a pas changé."
                doublon = self._doublon(cursor, key, clean, exclude_id=item_id)
                if doublon:
                    return False, doublon
                cursor.execute(f"UPDATE {meta['table']} SET {meta['libelle']} = ? WHERE {meta['id']} = ?",
                               (clean, item_id))
                conn.commit()
        except Exception as e:
            logger.exception("Renommage impossible dans %s", key)
            return False, f"Erreur technique : {e}"
        self._rafraichir_listes()
        return True, f"« {ancien} » est devenu « {clean} » (les demandes existantes affichent le nouveau libellé)."

    def set_referentiel_item_active(self, key: str, item_id: int, actif: bool) -> Tuple[bool, str]:
        meta = self.referentiel_meta(key)
        if not meta["modifiable"]:
            return False, meta.get("raison", "Cette liste n'est pas modifiable.")
        err = self._droits_referentiels()
        if err:
            return False, err
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(f"SELECT {meta['libelle']} FROM {meta['table']} WHERE {meta['id']} = ?", (item_id,))
                row = cursor.fetchone()
                if not row:
                    return False, "Cette valeur n'existe plus (actualisez la liste)."
                libelle = row[0]
                if not actif and self.est_valeur_protegee(key, libelle):
                    return False, f"« {libelle} » est utilisé par l'application : il ne peut pas être désactivé."
                if actif and meta.get("parent"):
                    p = REFERENTIELS[meta["parent"]]
                    cursor.execute(f"SELECT COALESCE(p.actif, 1) FROM {meta['table']} t JOIN {p['table']} p "
                                   f"ON p.{p['id']} = t.{meta['parent_fk']} WHERE t.{meta['id']} = ?", (item_id,))
                    if not cursor.fetchone()[0]:
                        return False, "Sa catégorie est désactivée : réactivez d'abord la catégorie."
                cursor.execute(f"UPDATE {meta['table']} SET actif = ? WHERE {meta['id']} = ?", (1 if actif else 0, item_id))
                conn.commit()
        except Exception as e:
            logger.exception("Changement de statut impossible dans %s", key)
            return False, f"Erreur technique : {e}"
        self._rafraichir_listes()
        if actif:
            return True, f"« {libelle} » est de nouveau proposé dans les listes."
        return True, f"« {libelle} » n'est plus proposé pour les nouvelles saisies (les demandes existantes le conservent)."

    def delete_referentiel_item(self, key: str, item_id: int) -> Tuple[bool, str]:
        """Suppression définitive : uniquement si la valeur n'est utilisée par aucune demande."""
        meta = self.referentiel_meta(key)
        if not meta["modifiable"]:
            return False, meta.get("raison", "Cette liste n'est pas modifiable.")
        err = self._droits_referentiels()
        if err:
            return False, err
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(f"SELECT {meta['libelle']} FROM {meta['table']} WHERE {meta['id']} = ?", (item_id,))
                row = cursor.fetchone()
                if not row:
                    return False, "Cette valeur n'existe plus (actualisez la liste)."
                libelle = row[0]
                if self.est_valeur_protegee(key, libelle):
                    return False, f"« {libelle} » est utilisé par l'application : il ne peut pas être supprimé."
                cursor.execute(f"SELECT COUNT(*) FROM demandes WHERE {meta['fk']} = ?", (item_id,))
                nb = cursor.fetchone()[0]
                if nb:
                    return False, (f"« {libelle} » est utilisé par {nb} demande(s) : suppression impossible. "
                                   f"Désactivez-le ou réaffectez ces demandes.")
                if key == "categories":
                    cursor.execute("SELECT COUNT(*) FROM sous_categories WHERE id_categorie = ?", (item_id,))
                    nb_sc = cursor.fetchone()[0]
                    if nb_sc:
                        return False, (f"La catégorie « {libelle} » contient {nb_sc} sous-catégorie(s) : "
                                       f"supprimez-les d'abord (ou désactivez la catégorie).")
                cursor.execute(f"DELETE FROM {meta['table']} WHERE {meta['id']} = ?", (item_id,))
                conn.commit()
        except Exception as e:
            logger.exception("Suppression impossible dans %s", key)
            return False, f"Erreur technique : {e}"
        self._rafraichir_listes()
        return True, f"« {libelle} » a été supprimé."

    def reassign_and_delete_referentiel_item(self, key: str, old_id: int, new_id: int) -> Tuple[bool, str]:
        """Réaffecte toutes les demandes d'une valeur vers une autre, puis supprime l'ancienne (transaction unique)."""
        meta = self.referentiel_meta(key)
        if not meta["modifiable"] or not meta.get("reaffectable"):
            return False, "La réaffectation n'est pas disponible pour cette liste."
        err = self._droits_referentiels()
        if err:
            return False, err
        if old_id == new_id:
            return False, "Choisissez une valeur de remplacement différente."
        try:
            with self._get_connection() as (conn, cursor):
                extra = f", {meta['parent_fk']}" if meta.get("parent") else ""
                cursor.execute(f"SELECT {meta['libelle']}, COALESCE(actif, 1){extra} FROM {meta['table']} "
                               f"WHERE {meta['id']} = ?", (old_id,))
                old = cursor.fetchone()
                cursor.execute(f"SELECT {meta['libelle']}, COALESCE(actif, 1){extra} FROM {meta['table']} "
                               f"WHERE {meta['id']} = ?", (new_id,))
                new = cursor.fetchone()
                if not old or not new:
                    return False, "Une des valeurs n'existe plus (actualisez la liste)."
                if self.est_valeur_protegee(key, old[0]):
                    return False, f"« {old[0]} » est utilisé par l'application : il ne peut pas être supprimé."
                if not new[1]:
                    return False, "La valeur de remplacement est désactivée."
                if meta.get("parent") and old[2] != new[2]:
                    return False, "La valeur de remplacement doit appartenir à la même catégorie."
                cursor.execute(f"UPDATE demandes SET {meta['fk']} = ? WHERE {meta['fk']} = ?", (new_id, old_id))
                nb = cursor.rowcount
                cursor.execute(f"DELETE FROM {meta['table']} WHERE {meta['id']} = ?", (old_id,))
                conn.commit()
        except Exception as e:
            logger.exception("Réaffectation impossible dans %s", key)
            return False, f"Erreur technique : {e}"
        self._rafraichir_listes()
        return True, f"{nb} demande(s) réaffectée(s) à « {new[0]} », puis « {old[0]} » a été supprimé."
