import win32com.client
import pythoncom
import os
import re
import hashlib
from datetime import datetime
from app.data.data_manager import DataManager
import logging
from app.utils.decorators import busy_cursor

logger = logging.getLogger(__name__)

# Les logs sont configurés une seule fois dans main.py (app.utils.logging_setup)

class OutlookFolderNotFoundError(Exception):
    """Exception levée quand le dossier Outlook n'est pas trouvé"""
    pass

class pjFolderNotFoundError(Exception):
    """Exception levée quand le dossier pj n'est pas trouvé"""
    pass
def normalize_subject(subject):
    if not subject:
        return ""
    subject = re.sub(r'^(RE|FW|FWD|TR|AW):\s*', '', subject, flags=re.IGNORECASE)
    subject = re.sub(r'\[.*?\]', '', subject)
    return subject.strip().lower()

def generate_thread_key(subject, sender, recipient):
    normalized = normalize_subject(subject)
    participants = sorted([sender.lower(), recipient.lower()])
    key_string = f"{normalized}|{'|'.join(participants)}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_outlook_header(msg, schema):
    try:
        return str(msg.PropertyAccessor.GetProperty(schema))
    except Exception:
        logger.debug("Exception ignorée dans get_outlook_header", exc_info=True)
        return None

def extraire_metadata_email(msg):
    try:
        conversation_id = str(msg.ConversationID)
    except AttributeError:
        schema_conv = "http://schemas.microsoft.com/mapi/proptag/0x30130102"
        conversation_id = str(msg.PropertyAccessor.GetProperty(schema_conv))
    identifiant_mail_unique = str(msg.EntryID) if hasattr(msg, "EntryID") else f"{conversation_id}_{datetime.now().timestamp()}"
    sujet = str(msg.Subject or "")
    resumer = str((msg.HTMLBody or "").strip())
    resumer_txt = str((msg.Body or "").strip())
    demandeur = str(msg.SenderName.split("(")[0].strip() or "")
    destinataire = str(msg.To or "")
    date_reception = msg.ReceivedTime.strftime("%Y-%m-%d %H:%M:%S") if msg.ReceivedTime else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    schema_msgid = "http://schemas.microsoft.com/mapi/proptag/0x1035001F"
    schema_inreplyto = "http://schemas.microsoft.com/mapi/proptag/0x1042001F"
    schema_references = "http://schemas.microsoft.com/mapi/proptag/0x1039001F"

    message_id = get_outlook_header(msg, schema_msgid)
    in_reply_to = get_outlook_header(msg, schema_inreplyto)
    email_references_str_raw = get_outlook_header(msg, schema_references)
    if email_references_str_raw:
        email_references_str = '|'.join(email_references_str_raw.split())
    else:
        email_references_str = None

    return {
        'conversation_id': conversation_id,
        'identifiant_mail_unique': identifiant_mail_unique,
        'sujet': sujet,
        'resumer': resumer,
        'resumer_txt': resumer_txt,
        'demandeur': demandeur,
        'destinataire': destinataire,
        'date_reception': date_reception,
        'message_id': message_id,
        'in_reply_to': in_reply_to,
        'email_references_str': email_references_str
    }


def rechercher_demande_existante(data_manager, metadata):
    if metadata['in_reply_to'] or metadata['email_references_str']:
        all_refs = []
        if metadata['in_reply_to']:
            all_refs.append(metadata['in_reply_to'])
        if metadata['email_references_str']:
            all_refs.extend(metadata['email_references_str'].split('|'))
        id_demande = data_manager.get_demande_by_message_ids(all_refs)
        if id_demande:
            return id_demande
    if metadata['conversation_id']:
        id_demande = data_manager.get_demande_id_by_conversation_id(metadata['conversation_id'])
        if id_demande:
            return id_demande
    thread_key = generate_thread_key(metadata['sujet'], metadata['demandeur'], metadata['destinataire'])
    id_demande = data_manager.get_demande_id_by_thread_key(thread_key)
    return id_demande


def is_real_attachment(attachment):
    """
    Retourne True pour les vraies pièces jointes ET les images inline.
    Filtre uniquement les signatures et logos automatiques.
    """
    try:
        filename = attachment.FileName.lower()

        # ✅ D'ABORD : vérifier si c'est une image inline (Content-ID)
        has_content_id = False
        try:
            content_id = attachment.PropertyAccessor.GetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
            )
            if content_id:
                has_content_id = True
        except Exception:
            logger.debug("Exception ignorée dans is_real_attachment", exc_info=True)

        # Filtrer les signatures et éléments automatiques
        ignore_patterns = ['logo', 'signature', 'banner', 'footer', 'header', 'outlook-']
        if any(pattern in filename for pattern in ignore_patterns):
            return False

        # ✅ Si c'est une image inline (a un Content-ID), on l'accepte même si cachée
        if has_content_id:
            # Vérifier quand même que ce n'est pas une signature cachée
            if any(pattern in filename for pattern in ignore_patterns):
                return False
            return True  # ← Accepter l'image inline

        # ✅ Pour les PJ normales (sans Content-ID), vérifier si cachée
        try:
            is_hidden = attachment.PropertyAccessor.GetProperty(
                "http://schemas.microsoft.com/mapi/proptag/0x7FFE000B"
            )
            if is_hidden:
                return False  # ← Filtrer seulement si PAS d'image inline
        except Exception:
            logger.debug("Exception ignorée dans is_real_attachment", exc_info=True)

        # Accepter tout le reste
        return True

    except Exception:
        logger.debug("Exception ignorée dans is_real_attachment", exc_info=True)
        return True


def traiter_pieces_jointes(msg, id_demande, data_manager, pj_path):
    """
    Traite toutes les pièces jointes ET les images inline du message.
    Sauvegarde le Content-ID pour les images inline.
    """
    nb_pieces_jointes = 0

    if msg.Attachments.Count == 0:
        return nb_pieces_jointes

    for i in range(1, msg.Attachments.Count + 1):
        attachment = msg.Attachments.Item(i)

        try:
            nom_fichier = attachment.FileName

            # Filtrer les signatures et logos automatiques
            if not is_real_attachment(attachment):
                continue

            # ✅ Récupérer le Content-ID pour les images inline
            content_id = None
            try:
                cid = attachment.PropertyAccessor.GetProperty(
                    "http://schemas.microsoft.com/mapi/proptag/0x3712001F"
                )
                if cid:
                    # Nettoyer le Content-ID (enlever les < et > si présents)
                    content_id = cid.strip('<>').strip()
            except Exception:
                logger.debug("Exception ignorée dans traiter_pieces_jointes", exc_info=True)

            # Générer un nom unique pour le fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")  # Ajout microsecondes pour unicité

            # Si c'est une image inline, préfixer avec "inline_"
            if content_id:
                nom_unique = f"{id_demande}_inline_{timestamp}_{nom_fichier}"
            else:
                nom_unique = f"{id_demande}_{timestamp}_{nom_fichier}"

            chemin_complet = os.path.join(pj_path, nom_unique)

            # Sauvegarder le fichier
            attachment.SaveAsFile(chemin_complet)
            taille_fichier = os.path.getsize(chemin_complet)

            # ✅ Enregistrer en base avec le content_id
            if data_manager.ajouter_piece_jointe(
                    id_demande,
                    nom_fichier,
                    nom_unique,
                    taille_fichier,
                    content_id  # ← Nouveau paramètre
            ):
                nb_pieces_jointes += 1
                if content_id:
                    logging.info(f"Image inline sauvegardée: {nom_fichier} (CID: {content_id})")
                else:
                    logging.info(f"Pièce jointe sauvegardée: {nom_fichier}")

        except Exception as e:
            logging.error(f"Erreur lors du traitement de la pièce jointe '{nom_fichier}': {e}")
            continue

    return nb_pieces_jointes


def traiter_reponse_existante(data_manager, id_demande, metadata):
    success = data_manager.ajouter_reponse_a_demande(
        id_demande=id_demande,
        conversation_id=metadata['conversation_id'],
        identifiant_mail_unique=metadata['identifiant_mail_unique'],
        message_id=metadata['message_id'],
        in_reply_to=metadata['in_reply_to'],
        email_references_str=metadata['email_references_str'],
        expediteur=metadata['demandeur'],
        date_reception=metadata['date_reception'],
        contenu=metadata['resumer']
    )
    return success

def creer_nouvelle_demande(data_manager, metadata, id_canal, id_etat, id_collecte):
    thread_key = generate_thread_key(metadata['sujet'], metadata['demandeur'], metadata['destinataire'])
    id_demande = data_manager.creer_demande_avec_email_initial(
        conversation_id=metadata['conversation_id'],
        thread_key=thread_key,
        sujet=metadata['sujet'],
        resumer=metadata['resumer'],
        resumer_txt=metadata['resumer_txt'],
        demandeur=metadata['demandeur'],
        date_reception=metadata['date_reception'],
        id_canal=id_canal,
        id_etat=id_etat,
        identifiant_mail_unique=metadata['identifiant_mail_unique'],
        message_id=metadata['message_id'],
        in_reply_to=metadata['in_reply_to'],
        email_references_str=metadata['email_references_str']
    )
    if id_demande:
        if data_manager.lier_demande_a_collecte(id_collecte, id_demande):
            return id_demande
    return None

def traiter_email(msg, data_manager, id_collecte, id_canal, id_etat, pj_path):
    stats = {'nouvelle_demande': False, 'reponse': False, 'nb_pj': 0}
    try:
        logging.info("Début traitement email")
        metadata = extraire_metadata_email(msg)

        id_demande = rechercher_demande_existante(data_manager, metadata)
        if id_demande:
            deja_connu = data_manager.existe_email_dans_demande(
                id_demande,metadata['identifiant_mail_unique']
            )
            if not deja_connu:
                if traiter_reponse_existante(data_manager, id_demande, metadata):
                    stats['reponse'] = True
            else:
                logging.info(f"Email déjà traité pour la demande #{id_demande}, ignoré.")
        else:
            id_demande = creer_nouvelle_demande(data_manager, metadata, id_canal, id_etat, id_collecte)
            if id_demande:
                stats['nouvelle_demande'] = True

        if id_demande:
            stats['nb_pj'] = traiter_pieces_jointes(msg, id_demande, data_manager, pj_path)

        # Ne pas marquer comme lu
        # msg.UnRead = False
        # msg.Save()

    except Exception as e:
        logging.error(f"Erreur lors du traitement de l'email : {e}", exc_info=True)
    return stats

def initialiser_collecte(user, data_manager):
    id_collecte = data_manager.creer_collecte(user['id'])
    return user['id'], id_collecte

def recuperer_messages_pigc(outlook, outlook_folder, date_debut=None):
    inbox = outlook.GetDefaultFolder(6)
    try:
        pigc_folder = inbox.Folders[outlook_folder]
    except Exception as e:
        raise OutlookFolderNotFoundError(
            f"Le dossier Outlook '{outlook_folder}' est introuvable.\n\n"
            f"Vérifiez que :\n"
            f"1. Le dossier '{outlook_folder}' existe dans votre boîte de réception\n"
            f"2. Le nom du dossier est correctement orthographié\n"
            f"3. Outlook est bien configuré et accessible\n\n"
            f"Vous pouvez modifier le nom du dossier dans Menu > Paramétrage"
        )
    messages = pigc_folder.Items

    if date_debut is not None:
        date_str = date_debut.strftime("%d/%m/%Y %H:%M")
        filter_str = f"[ReceivedTime] >= '{date_str}'"
        messages = messages.Restrict(filter_str)

    messages.Sort("[ReceivedTime]", True)

    messages_list = []
    for i in range(1, messages.Count + 1):
        try:
            msg = messages.Item(i)
            messages_list.append(msg)
        except Exception:
            logger.debug("Exception ignorée dans recuperer_messages_pigc", exc_info=True)
            continue

    return messages_list

@busy_cursor
def sync_outlook_to_sqlite(user, outlook_folder, pj_path, date_debut=None,progress_callback=None):
    pythoncom.CoInitialize()
    data_manager = DataManager()

    if not os.path.exists(pj_path):
        raise pjFolderNotFoundError(
            f"Le dossier '{pj_path}' est introuvable.\n\n"
            f"Vérifiez que :\n"
            f"2. Le nom du dossier est correctement orthographié et que le répertoire est accessible \n"
        )

    try:
        outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        id_utilisateur_lanceur, id_collecte = initialiser_collecte(user, data_manager)

        messages_list = recuperer_messages_pigc(outlook, outlook_folder, date_debut)
        if not messages_list:
            return 0,0

        # ✅ Appeler le callback AVANT de commencer (avec total)
        if progress_callback:
            progress_callback(0, len(messages_list), 0)  # 0 traité, 0 nouvelles demandes

        id_canal_crp = data_manager.get_id_by_libelle('canaux', 'CRP', default=1)
        id_etat_initial = data_manager.get_id_by_libelle('etats', 'À étudier', default=1)

        nb_nouvelles_demandes = 0
        nb_reponses_attachees = 0
        nb_emails_traites = 0
        nb_pieces_jointes = 0

        #for msg in messages_list:
        for idx, msg in enumerate(messages_list, start=1):
            if progress_callback:
                progress_callback(idx, len(messages_list), nb_nouvelles_demandes)

            stats = traiter_email(msg, data_manager, id_collecte, id_canal_crp, id_etat_initial, pj_path)
            if stats['nouvelle_demande']:
                nb_nouvelles_demandes += 1
            if stats['reponse']:
                nb_reponses_attachees += 1
            nb_pieces_jointes += stats['nb_pj']
            nb_emails_traites += 1

        # Mettre à jour les statistiques de la collecte
        data_manager.mettre_a_jour_statistiques_collecte(
            id_collecte,
            nb_nouvelles_demandes,
            nb_emails_traites
        )
        
        logger.info(f"\n✅ Synchronisation terminée avec succès !")
        logger.info(f" - Emails traités : {nb_emails_traites}")
        logger.info(f" - Nouvelles demandes : {nb_nouvelles_demandes}")
        logger.info(f" - Réponses attachées : {nb_reponses_attachees}")
        logger.info(f" - Pièces jointes extraites : {nb_pieces_jointes}")
        return nb_emails_traites,nb_nouvelles_demandes

    except OutlookFolderNotFoundError as e:
        logger.error(f"\n❌ {e}")
        if id_collecte:
            data_manager.supprimer_collecte(id_collecte)
        raise
    except pjFolderNotFoundError as e:
        logger.error(f"\n❌ {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Erreur critique : {e}")
        return 0
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    # Config utilisateur et dossier PJ
    user = {"id": 1, "nom": "Utilisateur Test"}
    outlook_folder = "PIGC"
    pj_path = r"C:\chemin\vers\PJ"

    # Date à partir de laquelle traiter les emails sans changer leur statut "non lu"
    date_cible = datetime(2025, 12, 1, 16, 13, 19)

    nb_traite = sync_outlook_to_sqlite(user, outlook_folder, pj_path, date_debut=date_cible)
    logger.info(f"✅ {nb_traite} emails traités à partir de {date_cible}.")
