"""Lecture, création et mise à jour des demandes."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from app.data.errors import ConflitModificationError

logger = logging.getLogger(__name__)

# Valeur par défaut de `expected_updated_at` : aucune vérification de version (compatibilité)
NON_VERIFIE = object()


class DemandesMixin:
    """Lecture, création et mise à jour des demandes."""

    def generate_conversation_id(self) -> str:
        """
        Génère un conversation_id unique au format ESPASS00000001
        Utilise la table sequence_counter pour garantir l'unicité
        Thread-safe et transactionnel
        """
        try:
            with self._get_connection() as (conn, cursor):
                # TRANSACTION pour éviter les conflits
                cursor.execute("BEGIN TRANSACTION")

                # Incrémenter la séquence
                cursor.execute("""
                    UPDATE sequence_counter
                    SET last_number = last_number + 1
                    WHERE prefix = 'ESPASS'
                """)

                # Récupérer le nouveau numéro
                cursor.execute("""
                    SELECT last_number
                    FROM sequence_counter
                    WHERE prefix = 'ESPASS'
                """)

                result = cursor.fetchone()

                if result:
                    numero = result[0]
                else:
                    # Si la table n'existe pas ou pas d'entrée, l'initialiser
                    cursor.execute("""
                        INSERT INTO sequence_counter (prefix, last_number, description)
                        VALUES ('ESPASS', 1, 'Séquence pour conversation_id')
                        ON CONFLICT(prefix) DO UPDATE SET last_number = 1
                    """)
                    numero = 1

                # Valider la transaction
                conn.commit()

                # Formater avec 8 chiffres : ESPASS00000001
                conversation_id = f"ESPASS{numero:08d}"
                logger.info(f"✅ conversation_id généré : {conversation_id} (séquence: {numero})")
                return conversation_id

        except Exception as e:
            logger.error(f"❌ Erreur génération conversation_id : {e}")
            # Fallback sur timestamp en cas d'erreur critique
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            return f"ESPASS{timestamp}"

    def update_etat_multiple(self, liste_ids: List[int], id_etat: int) -> Tuple[int, int]:
        """
        Met à jour l'état de plusieurs demandes en masse
        Args:
            liste_ids: Liste des ID de demandes à modifier
            id_etat: ID du nouvel état
        Returns:
            Tuple (nombre_succes, nombre_echec)
        """
        if not liste_ids:
            return (0, 0)
        if self._refuser_si_pas_droit('gerer_masse', "modifier des demandes en masse"):
            return (0, len(liste_ids))

        succes = 0
        echec = 0

        try:
            with self._get_connection() as (conn, cursor):
                # Utiliser une transaction pour tout ou rien
                cursor.execute("BEGIN TRANSACTION")

                for id_demande in liste_ids:
                    try:
                        cursor.execute("""
                            UPDATE demandes
                            SET id_etat = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id_demande = ?
                        """, (id_etat, id_demande))
                        succes += 1
                    except Exception:
                        echec += 1

                conn.commit()
                logger.info(f"✅ Mise à jour en masse : {succes} succès, {echec} échecs")
                return (succes, echec)

        except Exception as e:
            logger.error(f"❌ Erreur mise à jour en masse : {e}")
            return (0, len(liste_ids))

    def create_demande(self, data: Dict) -> Optional[int]:
        """
        Crée une nouvelle demande en base
        Génère automatiquement le conversation_id via sequence_counter
        Args:
            data: Dictionnaire avec les champs de la demande
        Returns:
            ID de la demande créée, ou None si erreur
        """
        if self._refuser_si_pas_droit('creer_demande', "créer une demande"):
            return None

        # Générer le conversation_id automatiquement
        conversation_id = self.generate_conversation_id()

        query = """
            INSERT INTO demandes (
                conversation_id,
                libelle, sujet, resume, demandeur, date_reception,
                id_canal, id_domaine, id_responsable, id_categorie,
                id_sous_categorie, id_nature, id_impact, id_urgence,
                id_etat, solution_suite_a_donner, commentaire,
                date_traitement,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """

        try:
            with self._get_connection() as (conn, cursor):
                params = (
                    conversation_id,
                    data.get('libelle'),
                    data.get('sujet'),
                    data.get('resume'),
                    data.get('demandeur'),
                    data.get('date_reception', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    data.get('id_canal'),
                    data.get('id_domaine'),
                    data.get('id_responsable'),
                    data.get('id_categorie'),
                    data.get('id_sous_categorie'),
                    data.get('id_nature'),
                    data.get('id_impact'),
                    data.get('id_urgence'),
                    data.get('id_etat'),
                    data.get('solution_suite_a_donner'),
                    data.get('commentaire'),
                    data.get('date_traitement')
                )

                cursor.execute(query, params)
                id_demande = cursor.lastrowid
                conn.commit()

                logger.info(f"✅ Demande créée - ID: {id_demande}, conversation_id: {conversation_id}")
                return id_demande

        except Exception as e:
            logger.error(f"❌ Erreur création demande : {e}")
            return None

    def existe_email_dans_demande(self, id_demande, identifiant_mail_unique):
        """
        Retourne True si l'email (identifiant_mail_unique) existe déjà pour cette demande.
        """
        query = """
            SELECT 1
            FROM echanges_emails
            WHERE id_demande = ? AND identifiant_mail_unique = ?
            LIMIT 1
        """
        rows = self.execute_query(query, (id_demande, identifiant_mail_unique))
        return bool(rows)

    def get_echanges_by_demande(self, id_demande):
        """Récupère tous les échanges emails pour une demande"""
        query = """
            SELECT 
                id_echange,
                expediteur,
                date_reception,
                contenu,
                type_message,
                est_derniere_reponse
            FROM echanges_emails 
            WHERE id_demande = ? 
            ORDER BY date_reception ASC
        """
        return self.execute_query(query, (id_demande,))

    def get_demandes(self, limit: int = 200, offset: int = 0,
                     inclure_archivees: bool = False,
                     inclure_annulees: bool = False,
                     inclure_realisees: bool = True,
                     mes_demandes_uniquement: bool = False,
                     name: str = None) -> List[Dict]:
        """
        Récupère la liste des demandes avec pagination et filtrage

        Args:
            limit: Nombre max de demandes
            offset: Décalage pour pagination
            inclure_archivees: Afficher les demandes archivées
            inclure_annulees: Afficher les demandes annulées
            inclure_realisees: Afficher les demandes réalisées

        Returns:
            Liste de dictionnaires avec les demandes
        """
        # Construire la clause WHERE pour filtrer les états
        conditions = []

        if not inclure_archivees:
            conditions.append("e.libelle_etat != 'Archivée'")

        if not inclure_annulees:
            conditions.append("e.libelle_etat != 'Annulée'")

        if not inclure_realisees:
            conditions.append("e.libelle_etat != 'Traitée'")
        if mes_demandes_uniquement:
            id_utilisateur = self.get_id_user_by_name(name)
            if id_utilisateur:
                conditions.append("(d.id_responsable = {} )".format(id_utilisateur))

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT 
                d.id_demande, d.libelle, d.sujet, d.resume, d.demandeur,
                d.date_reception, c.libelle_canal as canal,
                dom.libelle_domaine as domaine,
                COALESCE(u.nom || ' ' || u.prenom, '') as responsable,
                cat.libelle_categorie as categorie,
                sc.libelle_sous_categorie as sous_categorie,
                n.libelle_nature as nature,
                i.libelle_impact as impact,
                urg.libelle_urgence as urgence,
                d.priorite_calculee,
                d.solution_suite_a_donner,
                e.libelle_etat as etat,
                d.date_traitement,
                d.commentaire,
                (SELECT COUNT(*) FROM pieces_jointes pj WHERE PJ.id_demande=d.id_demande) pieces_jointes
            FROM demandes d
            LEFT JOIN canaux c ON d.id_canal = c.id_canal
            LEFT JOIN domaines dom ON d.id_domaine = dom.id_domaine
            LEFT JOIN utilisateurs u ON d.id_responsable = u.id_utilisateur
            LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
            LEFT JOIN sous_categories sc ON d.id_sous_categorie = sc.id_sous_categorie
            LEFT JOIN natures n ON d.id_nature = n.id_nature
            LEFT JOIN impacts i ON d.id_impact = i.id_impact
            LEFT JOIN urgences urg ON d.id_urgence = urg.id_urgence
            LEFT JOIN etats e ON d.id_etat = e.id_etat
            {where_clause}
            ORDER BY d.priorite_calculee, d.date_reception DESC
            LIMIT ? OFFSET ?
        """

        results = self._execute_query(query, (limit, offset))

        if results:
            colonnes = [
                'id_demande', 'libelle', 'sujet', 'resume', 'demandeur', 'date_reception',
                'canal', 'domaine', 'responsable', 'categorie', 'sous_categorie', 'nature',
                'impact', 'urgence', 'priorite', 'solution', 'etat', 'date_traitement', 'commentaire', 'pieces_jointes'
            ]

            return [dict(zip(colonnes, row)) for row in results]
        return []

    def get_demandes_by_ids(self, ids: List[int]) -> List[Dict]:
        """
        Récupère plusieurs demandes en une seule requête.

        Args:
            ids: liste d'id_demande

        Returns:
            Liste de dicts {colonne: valeur} pour chaque demande trouvée.
        """
        if not ids:
            return []

        # supprimer les doublons tout en gardant un ordre prévisible
        ids_uniques = list(dict.fromkeys(ids))

        # construire les placeholders pour la clause IN
        placeholders = ",".join("?" * len(ids_uniques))

        query = f"""
            SELECT 
                id_demande,
                conversation_id,
                thread_key,
                libelle,
                sujet,
                resume,
                demandeur,
                strftime('%d/%m/%Y',date_reception) date_reception,
                (SELECT libelle_canal FROM canaux c where c.id_canal=d.id_canal) libelle_canal,
                (select libelle_domaine from domaines e where e.id_domaine=d.id_domaine) libelle_domaine,
                (select u.nom ||' '||u.prenom FROM utilisateurs u where u.id_utilisateur=d.id_responsable) nom_responsable,
                (SELECT libelle_categorie FROM categories c WHERE c.id_categorie=d.id_categorie) libelle_categorie,
                (SELECT libelle_sous_categorie FROM sous_categories c WHERE c.id_sous_categorie=d.id_sous_categorie) libelle_sous_categorie,
                (SELECT libelle_nature FROM natures n WHERE n.id_nature=d.id_nature) libelle_nature,
                (SELECT libelle_impact FROM impacts i WHERE i.id_impact=d.id_impact ) libelle_impact,
                (SELECT libelle_urgence FROM urgences u where u.id_urgence=d.id_urgence) libelle_urgence,
                (SELECT libelle_etat from etats e where e.id_etat=d.id_etat) libelle_etat,
                solution_suite_a_donner,
                commentaire,
                strftime('%d/%m/%Y',date_traitement) date_traitement,
                strftime('%d/%m/%Y %H:%M:%S',created_at) created_at ,
                strftime('%d/%m/%Y %H:%M:%S',updated_at) updated_at
            FROM demandes d
            WHERE id_demande IN ({placeholders})
        """

        rows = self._execute_query(query, tuple(ids_uniques))  # ou execute_query selon ton code
        if not rows:
            return []

        # adapter les noms de colonnes à ce que tu utilises déjà dans get_demandes / get_demande_by_id
        colonnes = [
            "id_demande",
            "conversation_id",
            "thread_key",
            "libelle",
            "sujet",
            "resume",
            "demandeur",
            "date_reception",
            "libelle_canal",
            "libelle_domaine",
            "nom_responsable",
            "libelle_categorie",
            "libelle_sous_categorie",
            "libelle_nature",
            "libelle_impact",
            "libelle_urgence",
            "libelle_etat",
            "solution_suite_a_donner",
            "commentaire",
            "date_traitement",
            "created_at",
            "updated_at",
        ]

        demandes = []
        for row in rows:
            d = {}
            for i, col in enumerate(colonnes):
                if i < len(row):
                    d[col] = row[i]
            demandes.append(d)

        return demandes

    def get_demande_by_id(self, id_demande: int) -> Optional[Dict]:
        """Récupère une demande complète par son ID"""
        query = """
            SELECT 
                d.id_demande, d.libelle, d.sujet, d.resume, d.demandeur,
                d.date_reception, d.id_canal, d.id_domaine, d.id_responsable,
                d.id_categorie, d.id_sous_categorie, d.id_nature,
                d.id_impact, d.id_urgence, d.priorite_calculee,
                d.id_etat, d.date_traitement, d.solution_suite_a_donner,
                d.commentaire,
                d.updated_at,
                c.libelle_canal, dom.libelle_domaine,
                cat.libelle_categorie, sc.libelle_sous_categorie,
                n.libelle_nature, i.libelle_impact, u.libelle_urgence,
                e.libelle_etat,
                COALESCE(usr.nom || ' ' || usr.prenom, '') as responsable,
                d.conversation_id
            FROM demandes d
            LEFT JOIN canaux c ON d.id_canal = c.id_canal
            LEFT JOIN domaines dom ON d.id_domaine = dom.id_domaine
            LEFT JOIN categories cat ON d.id_categorie = cat.id_categorie
            LEFT JOIN sous_categories sc ON d.id_sous_categorie = sc.id_sous_categorie
            LEFT JOIN natures n ON d.id_nature = n.id_nature
            LEFT JOIN impacts i ON d.id_impact = i.id_impact
            LEFT JOIN urgences u ON d.id_urgence = u.id_urgence
            LEFT JOIN etats e ON d.id_etat = e.id_etat
            LEFT JOIN utilisateurs usr ON d.id_responsable = usr.id_utilisateur
            WHERE d.id_demande = ?
        """

        results = self._execute_query(query, (id_demande,))

        if results and len(results) > 0:
            row = results[0]
            colonnes = [
                'id_demande', 'libelle', 'sujet', 'resume', 'demandeur', 'date_reception',
                'id_canal', 'id_domaine', 'id_responsable', 'id_categorie', 'id_sous_categorie',
                'id_nature', 'id_impact', 'id_urgence', 'priorite_calculee', 'id_etat',
                'date_traitement', 'solution_suite_a_donner', 'commentaire', 'updated_at',
                'libelle_canal', 'libelle_domaine', 'libelle_categorie', 'libelle_sous_categorie',
                'libelle_nature', 'libelle_impact', 'libelle_urgence', 'libelle_etat', 'responsable','conversation_id'
            ]
            return dict(zip(colonnes, row))
        return None

    def update_demandes_bulk(self, liste_ids: List[int], data: Dict) -> Tuple[int, int]:
        """
        Met à jour plusieurs demandes en une seule requête SQL (TRÈS RAPIDE)

        Args:
            liste_ids: Liste des ID de demandes à modifier
            data: Dictionnaire des champs à mettre à jour
                  Exemple: {'id_etat': 3, 'solution_suite_a_donner': 'texte', 'date_traitement': '2025-12-25 14:30:00'}

        Returns:
            Tuple (nombre_succes, nombre_echec)
        """
        if not liste_ids or not data:
            return 0, 0
        if self._refuser_si_pas_droit('gerer_masse', "modifier des demandes en masse"):
            return 0, len(liste_ids)

        try:
            with self._get_connection() as (conn, cursor):
                # Construire la clause SET dynamiquement
                champs_mapping = {
                    'resume': 'resume',
                    'id_canal': 'id_canal',
                    'id_domaine': 'id_domaine',
                    'id_responsable': 'id_responsable',
                    'id_categorie': 'id_categorie',
                    'id_souscategorie': 'id_sous_categorie',
                    'id_nature': 'id_nature',
                    'id_impact': 'id_impact',
                    'id_urgence': 'id_urgence',
                    'id_etat': 'id_etat',
                    'solution_suite_a_donner': 'solution_suite_a_donner',
                    'commentaire': 'commentaire',
                    'date_traitement': 'date_traitement',
                }

                sets = []
                params = []

                for cle_data, colonne_sql in champs_mapping.items():
                    if cle_data in data:
                        sets.append(f"{colonne_sql} = ?")
                        params.append(data[cle_data])

                if not sets:
                    return 0, 0  # Rien à modifier

                # Ajouter updatedat
                sets.append("updated_at = CURRENT_TIMESTAMP")

                # Construire les placeholders pour la clause IN
                placeholders = ','.join('?' * len(liste_ids))

                # Ajouter les IDs aux paramètres
                params.extend(liste_ids)

                # Construire et exécuter la requête
                query = f"UPDATE demandes SET {', '.join(sets)} WHERE id_demande IN ({placeholders})"

                cursor.execute(query, params)
                rows_affected = cursor.rowcount
                conn.commit()

                logger.info(f"✅ Mise à jour en masse : {rows_affected} demandes modifiées en une seule requête SQL")

                return rows_affected, len(liste_ids) - rows_affected

        except Exception as e:
            logger.error(f"❌ Erreur mise à jour en masse : {e}")
            return 0, len(liste_ids)

    def update_demande(self, id_demande: int, data: Dict, expected_updated_at=NON_VERIFIE) -> bool:
        """Met à jour une demande.

        Verrou optimiste : si `expected_updated_at` est fourni (valeur `updated_at` lue au chargement de
        la demande, éventuellement None), la mise à jour n'a lieu que si la ligne n'a pas changé depuis.
        Sinon `ConflitModificationError` est levée (modifiée par un autre poste, ou supprimée).
        Retourne False en cas d'erreur d'accès base (voir `last_error`).
        """
        if not data:
            return False
        if self._refuser_si_pas_droit('gerer', "modifier une demande"):
            return False

        champs_mapping = {
            'resume': 'resume',
            'id_canal': 'id_canal',
            'id_domaine': 'id_domaine',
            'id_responsable': 'id_responsable',
            'id_categorie': 'id_categorie',
            'id_sous_categorie': 'id_sous_categorie',
            'id_nature': 'id_nature',
            'id_impact': 'id_impact',
            'id_urgence': 'id_urgence',
            'id_etat': 'id_etat',
            'solution_suite_a_donner': 'solution_suite_a_donner',
            'commentaire': 'commentaire',
            'date_traitement': 'date_traitement',
            'libelle': 'libelle',
            'sujet': 'sujet',
            'demandeur': 'demandeur',
        }

        sets = []
        params = []

        for cle_data, colonne_sql in champs_mapping.items():
            if cle_data in data:  # on ne touche au champ que s’il est dans data
                sets.append(f"{colonne_sql} = ?")
                params.append(data[cle_data])

        if not sets:
            return False  # rien à modifier

        sets.append("updated_at = CURRENT_TIMESTAMP")
        query = f"""
            UPDATE demandes
            SET {', '.join(sets)}
            WHERE id_demande = ?
        """
        params.append(id_demande)

        if expected_updated_at is NON_VERIFIE:
            return self.execute_update(query, tuple(params))

        query += " AND updated_at IS ?"   # IS : comparaison correcte aussi quand updated_at est NULL
        params.append(expected_updated_at)
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute(query, tuple(params))
                modifiees = cursor.rowcount
                conn.commit()
                if modifiees == 0:
                    cursor.execute("SELECT 1 FROM demandes WHERE id_demande = ?", (id_demande,))
                    existe = cursor.fetchone() is not None
            self.last_error = None
        except Exception as e:
            self._record_error("UPDATE", query, e)
            return False

        if modifiees == 0:
            raise ConflitModificationError(
                "La demande a été modifiée par un autre utilisateur depuis son ouverture."
                if existe else "La demande n'existe plus (supprimée par un autre utilisateur)."
            )
        return True
