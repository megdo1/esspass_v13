"""Collecte Outlook : rattachement des mails, pièces jointes, statistiques de collecte."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from app.data.sql_utils import sql_nom_utilisateur_ou_repere

logger = logging.getLogger(__name__)


class CollecteMixin:
    """Collecte Outlook : rattachement des mails, pièces jointes, statistiques de collecte."""

    def creer_collecte(self, id_utilisateur_lanceur: int) -> Optional[int]:
        """
        Crée une nouvelle entrée de collecte dans la table metadonnees_collecte
        
        Args:
            id_utilisateur_lanceur: ID de l'utilisateur qui lance la collecte
        
        Returns:
            int: L'ID de la collecte créée, ou None en cas d'erreur
        """
        if self._refuser_si_pas_droit('mettre_a_jour', "lancer une collecte de mails"):
            return None

        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute("""
                    INSERT INTO metadonnees_collecte (id_utilisateur_lanceur, date_collecte)
                    VALUES (?, ?)
                """, (id_utilisateur_lanceur, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

                id_collecte = cursor.lastrowid
                conn.commit()

                logger.info(f"📦 Nouvelle collecte : ID {id_collecte}")
                return id_collecte

        except Exception as e:
            logger.error(f"❌ Erreur lors de la création de la collecte : {e}")
            return None

    def get_last_collecte(self) -> Dict[str, any]:
        """Récupère les informations de la dernière collecte"""
        query = f"""
            SELECT 
                mc.date_collecte,
                {sql_nom_utilisateur_ou_repere('u', 'mc.id_utilisateur_lanceur')} as lanceur,
                mc.nb_nouvelles_demandes,
                mc.nb_total_demandes
            FROM metadonnees_collecte mc
            LEFT JOIN utilisateurs u ON mc.id_utilisateur_lanceur = u.id_utilisateur
            ORDER BY mc.date_collecte DESC
            LIMIT 1
        """

        results = self._execute_query(query)

        if results and len(results) > 0:
            row = results[0]
            try:
                date_str = row[0]
                date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                date_formatee = date_obj.strftime("%d/%m/%Y à %H:%M")
            except Exception:
                date_formatee = str(row[0])

            return {
                'date_collecte': date_formatee,
                'lanceur': row[1] or 'Automatique',
                'nb_nouvelles': row[2] or 0,
                'nb_total': row[3] or 0,
                'date_time': datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S"),
            }
        else:
            total = self.get_total_demandes()
            nbJours = self.get_nb_jours()
            result = datetime.now() - timedelta(days=nbJours)
            return {
                'date_collecte': 'Aucune collecte',
                'date_time': result,
                'lanceur': 'N/A',
                'nb_nouvelles': 0,
                'nb_total': total
            }

    def get_pieces_jointes_by_demande(self, id_demande,id_utilisateur: int = None):
        """
        Récupère toutes les PJ d'une demande avec chemin reconstruit pour l'utilisateur

        Args:
            id_demande: ID de la demande
            id_utilisateur: ID de l'utilisateur (si None, utilise l'utilisateur connecté)

        Returns:
            list: Liste de tuples (id, id_demande, chemin_complet, chemin_original, taille, date)
        """
        # Si pas d'ID fourni, récupérer l'utilisateur connecté
        if id_utilisateur is None:
            user_info = self.get_current_user()
            id_utilisateur = user_info.get("id", -1)

        # 🔧 REQUÊTE SQL AVEC RECONSTRUCTION DU CHEMIN
        query = """
            SELECT  pj.id_piece_jointe,
                pj.id_demande,
                (SELECT valeur 
                 FROM parametres_app pa 
                 WHERE pa.id_utilisateur = ? AND pa.cle = 'pj_path'
                ) || '/' || pj.chemin_fichier as chemin_complet,
                pj.nom_fichier,
                pj.taille_fichier,
                pj.date_ajout
            FROM pieces_jointes pj
            WHERE pj.id_demande = ?
            AND content_id IS NULL
            ORDER BY pj.date_ajout DESC
        """

        return self.execute_query(query, (id_utilisateur, id_demande))

    def get_demande_id_by_conversation_id(self, conversation_id: str) -> Optional[int]:
        """
        Récupère l'ID d'une demande par son conversation_id
        
        Args:
            conversation_id: L'identifiant de conversation (ex: 'ESPASS00000001')
        
        Returns:
            int: ID de la demande, ou None si non trouvée
        """
        try:
            query = "SELECT id_demande FROM demandes WHERE conversation_id = ?"
            result = self._execute_query(query, (conversation_id,))

            if result and len(result) > 0:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"❌ Erreur recherche demande par conversation_id : {e}")
            return None

    def get_demande_id_by_thread_key(self, thread_key: str, days_limit: int = 2) -> Optional[int]:
        """
        Recherche l'ID d'une demande récente par thread_key
        
        Args:
            thread_key: La clé de thread générée (hash du sujet/demandeur/destinataire)
            days_limit: Limite en jours pour considérer une demande comme récente (2 par défaut)
        
        Returns:
            int: ID de la demande la plus récente, ou None si non trouvée
        """
        try:
            query = """
                SELECT id_demande FROM demandes 
                WHERE thread_key = ? 
                AND datetime(date_reception) > datetime('now', ?)
                ORDER BY date_reception DESC
                LIMIT 1
            """

            # Construire le modificateur de date (ex: '-2 days')
            time_modifier = f'-{days_limit} days'

            result = self._execute_query(query, (thread_key, time_modifier))

            if result and len(result) > 0:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"❌ Erreur recherche demande par thread_key : {e}")
            return None

    def get_demande_by_message_ids(self, message_ids: List[str]) -> Optional[int]:
        """
        Recherche l'ID d'une demande associée à une liste de message IDs (références email)
        
        Args:
            message_ids: Liste des message IDs à rechercher
        
        Returns:
            int: ID de la première demande trouvée, ou None si aucune correspondance
        """
        if not message_ids:
            return None

        try:
            # Créer les placeholders pour la clause IN
            placeholders = ','.join('?' * len(message_ids))

            query = f"""
                SELECT DISTINCT d.id_demande 
                FROM demandes d
                JOIN echanges_emails e ON d.id_demande = e.id_demande
                WHERE e.message_id IN ({placeholders})
                LIMIT 1
            """

            result = self._execute_query(query, tuple(message_ids))

            if result and len(result) > 0:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"❌ Erreur recherche demande par message IDs : {e}")
            return None

    def _ajouter_email_a_demande(self,
                                 id_demande: int,
                                 conversation_id: str,
                                 identifiant_mail_unique: str,
                                 message_id: str,
                                 in_reply_to: str,
                                 email_references_str: str,
                                 expediteur: str,
                                 date_reception: str,
                                 contenu: str,
                                 type_message: str = 'REPONSE',
                                 est_derniere_reponse: int = 0,
                                 update_demande: bool = True) -> bool:
        """
        Méthode privée générique pour ajouter un email à une demande
        
        Args:
            id_demande: ID de la demande
            conversation_id: ID de conversation
            identifiant_mail_unique: Identifiant unique du mail
            message_id: Message-ID de l'email
            in_reply_to: Message-ID de l'email auquel on répond
            email_references_str: Références email
            expediteur: Expéditeur
            date_reception: Date de réception
            contenu: Contenu
            type_message: Type ('DEMANDE' ou 'REPONSE')
            est_derniere_reponse: 1 si dernière réponse, 0 sinon
            update_demande: True pour mettre à jour updated_at de la demande
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute("""
                    INSERT INTO echanges_emails (
                        id_demande, conversation_id, identifiant_mail_unique,
                        message_id, in_reply_to, email_references,
                        expediteur, date_reception, contenu, type_message, est_derniere_reponse
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    id_demande, conversation_id, identifiant_mail_unique,
                    message_id, in_reply_to, email_references_str,
                    expediteur, date_reception, contenu, type_message, est_derniere_reponse
                ))

                if update_demande:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        "UPDATE demandes SET updated_at = ? WHERE id_demande = ?",
                        (now, id_demande)
                    )

                conn.commit()
                logger.info(f"♻️ Réponse ajoutée à la demande #{id_demande}")
                return True

        except Exception as e:
            logger.error(f"❌ Erreur ajout email à demande : {e}")
            return False

    def ajouter_reponse_a_demande(self,
                                  id_demande: int,
                                  conversation_id: str,
                                  identifiant_mail_unique: str,
                                  message_id: str,
                                  in_reply_to: str,
                                  email_references_str: str,
                                  expediteur: str,
                                  date_reception: str,
                                  contenu: str) -> bool:
        """
        Méthode publique pour ajouter une réponse à une demande existante
        """
        return self._ajouter_email_a_demande(
            id_demande=id_demande,
            conversation_id=conversation_id,
            identifiant_mail_unique=identifiant_mail_unique,
            message_id=message_id,
            in_reply_to=in_reply_to,
            email_references_str=email_references_str,
            expediteur=expediteur,
            date_reception=date_reception,
            contenu=contenu,
            type_message='REPONSE',
            est_derniere_reponse=0,
            update_demande=True
        )

    def creer_demande_avec_email_initial(self,
                                         conversation_id: str,
                                         thread_key: str,
                                         sujet: str,
                                         resumer: str,
                                         resumer_txt : str,
                                         demandeur: str,
                                         date_reception: str,
                                         id_canal: int,
                                         id_etat: int,
                                         identifiant_mail_unique: str,
                                         message_id: str,
                                         in_reply_to: str,
                                         email_references_str: str) -> Optional[int]:
        """
        Crée une nouvelle demande avec son email initial de type DEMANDE
        
        Args:
            conversation_id: ID de conversation (ex: 'ESPASS00000001')
            thread_key: Clé de thread pour regrouper les emails
            sujet: Sujet de la demande
            resumer: Résumé du contenu
            demandeur: Email du demandeur
            date_reception: Date de réception au format 'YYYY-MM-DD HH:MM:%S'
            id_canal: ID du canal (ex: CRP)
            id_etat: ID de l'état initial (ex: À étudier)
            identifiant_mail_unique: Identifiant unique du mail
            message_id: Message-ID de l'email
            in_reply_to: Message-ID de l'email auquel on répond
            email_references_str: Références email au format string
        
        Returns:
            int: ID de la demande créée, ou None si erreur
        """
        if self._refuser_si_pas_droit('mettre_a_jour', "lancer une collecte de mails"):
            return None
        try:
            with self._get_connection() as (conn, cursor):
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Insérer la nouvelle demande
                cursor.execute("""
                    INSERT INTO demandes (
                        conversation_id, thread_key, libelle, sujet, resume, demandeur,
                        date_reception, id_canal, id_etat, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id,
                    thread_key,
                    sujet[:100],
                    sujet,
                    resumer_txt[:500],
                    demandeur,
                    date_reception,
                    id_canal,
                    id_etat,
                    now,
                    now
                ))

                id_demande = cursor.lastrowid
                conn.commit()

            # Réutiliser la méthode existante pour ajouter l'email initial
            # Note: on passe type_message='DEMANDE' et est_derniere_reponse=1
            success = self._ajouter_email_a_demande(
                id_demande=id_demande,
                conversation_id=conversation_id,
                identifiant_mail_unique=identifiant_mail_unique,
                message_id=message_id,
                in_reply_to=in_reply_to,
                email_references_str=email_references_str,
                expediteur=demandeur,
                date_reception=date_reception,
                contenu=resumer,
                type_message='DEMANDE',
                est_derniere_reponse=1,
                update_demande=False  # Pas besoin de mettre à jour updated_at car on vient de créer
            )

            if success:
                logger.info(f"✨ Nouvelle demande créée : ID {id_demande}, conversation_id: {conversation_id}")
                return id_demande
            else:
                return None

        except Exception as e:
            logger.error(f"❌ Erreur création demande avec email : {e}")
            return None

    def lier_demande_a_collecte(self, id_collecte: int, id_demande: int) -> bool:
        """
        Lie une demande à une collecte dans la table de jonction collecte_demandes
        
        Args:
            id_collecte: ID de la collecte
            id_demande: ID de la demande
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            query = "INSERT INTO collecte_demandes (id_collecte, id_demande) VALUES (?, ?)"
            success = self._execute_update(query, (id_collecte, id_demande))

            return success

        except Exception as e:
            logger.error(f"❌ Erreur liaison demande-collecte : {e}")
            return False

    def ajouter_piece_jointe(self,
                             id_demande: int,
                             nom_fichier: str,
                             chemin_fichier: str,
                             taille_fichier: int,
                             content_id=None) -> bool:
        """
        Ajoute une pièce jointe à une demande
        
        Args:
            id_demande: ID de la demande
            nom_fichier: Nom du fichier
            chemin_fichier: Chemin complet du fichier sur le disque
            taille_fichier: Taille du fichier en octets
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            query = """
                INSERT INTO pieces_jointes (
                    id_demande, nom_fichier, chemin_fichier, taille_fichier,content_id
                ) VALUES (?, ?, ?, ?, ?)
            """
            success = self._execute_update(query, (id_demande, nom_fichier, chemin_fichier, taille_fichier,content_id))

            if success:
                logger.info(f"📎 Pièce jointe ajoutée : {nom_fichier} ({taille_fichier} octets)")

            return success

        except Exception as e:
            logger.error(f"❌ Erreur ajout pièce jointe : {e}")
            return False

    def get_images_inline_by_demande(self, id_demande: int,id_utilisateur: int = None) -> list:
        """
        Récupère toutes les images inline d'une demande (ayant un content_id)

        Args:
            id_demande: ID de la demande

        Returns:
            list: Liste des images inline avec leur content_id et chemin
        """
        # Si pas d'ID fourni, récupérer l'utilisateur connecté
        if id_utilisateur is None:
            user_info = self.get_current_user()
            id_utilisateur = user_info.get("id", -1)
        try:
            query = """
                SELECT content_id, nom_fichier, content_id,
                (SELECT valeur 
                 FROM parametres_app pa 
                 WHERE pa.id_utilisateur = ? AND pa.cle = 'pj_path'
                ) || '/' || pj.chemin_fichier as chemin_fichier
                FROM pieces_jointes pj
                WHERE id_demande = ? AND content_id IS NOT NULL
            """
            results = self._execute_query(query, (id_utilisateur,id_demande,))

            return [
                {
                    'id': row[0],
                    'nom_fichier': row[1],
                    'content_id': row[2],
                    'chemin_fichier': row[3],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"❌ Erreur récupération images inline : {e}")
            return []

    def mettre_a_jour_statistiques_collecte(self,
                                            id_collecte: int,
                                            nb_nouvelles_demandes: int,
                                            nb_emails_traites: int) -> bool:
        """
        Met à jour les statistiques d'une collecte
        Calcule automatiquement le nombre total de demandes en base
        
        Args:
            id_collecte: ID de la collecte
            nb_nouvelles_demandes: Nombre de nouvelles demandes créées
            nb_emails_traites: Nombre d'emails traités
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            query = """
                UPDATE metadonnees_collecte
                SET nb_nouvelles_demandes = ?,
                    nb_emails_traites = ?,
                    nb_total_demandes = (SELECT COUNT(*) FROM demandes)
                WHERE id_collecte = ?
            """
            success = self._execute_update(query, (nb_nouvelles_demandes, nb_emails_traites, id_collecte))

            if success:
                logger.info(
                    f"📊 Statistiques collecte #{id_collecte} mises à jour : {nb_nouvelles_demandes} nouvelles, {nb_emails_traites} traités")

            return success

        except Exception as e:
            logger.error(f"❌ Erreur mise à jour statistiques collecte : {e}")
            return False

    # ------------------------------------------------------------------ administration des collectes
    MAX_COLLECTES_PAR_SUPPRESSION = 500

    def get_collectes_pour_admin(self, limit: int = 300) -> List[Dict]:
        """Liste les collectes (les plus récentes d'abord) avec leurs statistiques, pour l'onglet d'administration.

        Réservé à l'Administrateur. `nb_liees` = demandes rattachées à la collecte (table collecte_demandes) ;
        une collecte « sans demande créée » a nb_nouvelles = 0 et nb_liees = 0.
        """
        if self._refuser_si_pas_droit('gerer_collectes', "consulter les collectes"):
            return []
        query = f"""
            SELECT mc.id_collecte,
                   mc.date_collecte,
                   COALESCE({sql_nom_utilisateur_ou_repere('u', 'mc.id_utilisateur_lanceur')}, 'Automatique'),
                   COALESCE(mc.nb_emails_traites, 0),
                   COALESCE(mc.nb_nouvelles_demandes, 0),
                   (SELECT COUNT(*) FROM collecte_demandes cd WHERE cd.id_collecte = mc.id_collecte),
                   mc.nb_total_demandes
            FROM metadonnees_collecte mc
            LEFT JOIN utilisateurs u ON u.id_utilisateur = mc.id_utilisateur_lanceur
            ORDER BY mc.date_collecte DESC, mc.id_collecte DESC
            LIMIT ?
        """
        rows = self._execute_query(query, (int(limit),))
        if rows is None:
            return []
        return [
            {'id_collecte': r[0], 'date_collecte': r[1], 'lanceur': r[2], 'nb_emails_traites': r[3],
             'nb_nouvelles': r[4], 'nb_liees': r[5], 'nb_total': r[6]}
            for r in rows
        ]

    def supprimer_collectes(self, ids_collectes) -> Dict:
        """Supprime les MÉTADONNÉES de collectes : lignes de metadonnees_collecte et de collecte_demandes.

        Ne touche JAMAIS aux demandes, ni à leurs mails ou pièces jointes. Sert au rattrapage : la prochaine
        collecte repart de la date de la dernière collecte restante ; les mails déjà importés sont reconnus
        (identifiants de message, conversation, clé de fil) et ne sont pas dupliqués.
        Réservé à l'Administrateur ; les deux suppressions se font dans une seule transaction.

        Retourne {'ok', 'collectes', 'liens', 'message'}.
        """
        echec = lambda msg: {'ok': False, 'collectes': 0, 'liens': 0, 'message': msg}
        if self._refuser_si_pas_droit('gerer_collectes', "supprimer des collectes"):
            return echec(self.last_error)
        try:
            ids = sorted({int(i) for i in ids_collectes})
        except (TypeError, ValueError):
            return echec("Identifiants de collecte invalides.")
        if not ids:
            return echec("Aucune collecte sélectionnée.")
        if len(ids) > self.MAX_COLLECTES_PAR_SUPPRESSION:
            return echec(f"Sélection trop large (maximum {self.MAX_COLLECTES_PAR_SUPPRESSION} collectes à la fois).")

        marques = ",".join("?" for _ in ids)
        try:
            with self._get_connection() as (conn, cursor):
                cursor.execute("BEGIN TRANSACTION")
                cursor.execute(f"DELETE FROM collecte_demandes WHERE id_collecte IN ({marques})", ids)
                liens = cursor.rowcount
                cursor.execute(f"DELETE FROM metadonnees_collecte WHERE id_collecte IN ({marques})", ids)
                collectes = cursor.rowcount
                conn.commit()
            self.last_error = None
        except Exception as e:
            self._record_error("DELETE", "suppression de collectes", e)
            return echec(f"Suppression impossible : {e}")

        logger.warning("Collectes supprimées (métadonnées seulement) : %s (%d collectes, %d liens)",
                       ids, collectes, liens)
        return {'ok': True, 'collectes': collectes, 'liens': liens,
                'message': f"{collectes} collecte(s) et {liens} lien(s) demande-collecte supprimés."}

    def supprimer_collecte(self, id_collecte: int) -> bool:
        """
        Supprime définitivement un utilisateur

        Args:
            id_utilisateur: ID de l'utilisateur

        Returns:
            True si succès, False sinon
        """
        if self._refuser_si_pas_droit('mettre_a_jour', "supprimer une collecte"):
            return False
        query = "DELETE FROM metadonnees_collecte WHERE id_collecte = ?"
        success = self._execute_update(query, (id_collecte,))

        if success:
            logger.warning(f"⚠️ collecte #{id_collecte} supprimé définitivement")

        return success
