"""
Fonctions utilitaires pour l'authentification et les permissions
Centralise la logique d'authentification et la matrice des droits
"""

import os
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import win32com.client
except ImportError:
    win32com = None


def get_current_user_from_outlook() -> Tuple[Optional[str], Optional[str]]:
    """
    Récupère le nom et email de l'utilisateur depuis Outlook

    Returns:
        Tuple (nom_complet, email) ou (None, None) en cas d'erreur
    """
    try:
        if win32com is None:
            raise ImportError("win32com non disponible")

        try:
            outlook_app = win32com.client.GetActiveObject("Outlook.Application")
            namespace = outlook_app.GetNamespace("MAPI")
            user = namespace.CurrentUser

            nom_complet = user.Name
            recipient = namespace.CreateRecipient(nom_complet)
            recipient.Resolve()
            email = recipient.AddressEntry.GetExchangeUser().PrimarySmtpAddress

            return nom_complet, email
        except Exception:
            # Outlook indisponible : repli sur l'identité Windows
            logger.debug("Exception ignorée dans get_current_user_from_outlook", exc_info=True)

        username = os.getenv("USERNAME")
        email = f"{username}@sncf.fr"

        return username, email

    except Exception as e:
        logger.error(f"❌ Erreur lors de la récupération utilisateur : {e}")
        return None, None


# ========== MATRICE DES DROITS ==========
PERMISSIONS = {
    'Consultant': {
        'creer_demande': False,
        'traiter': False,
        'gerer_masse': False,
        'archiver': False,
        'exporter': True,
        'rapports': True,
        'dupliquer': False,
        'gerer': False,
        'annuler': False,
        'mettre_a_jour': False,
        'gerer_listes': False,
        'gerer_utilisateurs': False,
    },
    'Membre MCO': {
        'creer_demande': True,
        'traiter': True,
        'gerer_masse': True,
        'archiver': False,
        'exporter': True,
        'rapports': True,
        'dupliquer': True,
        'gerer': True,
        'annuler': True,
        'mettre_a_jour': True,
        'gerer_listes': False,
        'gerer_utilisateurs': False,
    },
    'Administrateur': {
        'creer_demande': True,
        'traiter': True,
        'gerer_masse': True,
        'archiver': True,
        'exporter': True,
        'rapports': True,
        'dupliquer': True,
        'gerer': True,
        'annuler': True,
        'mettre_a_jour': True,
        'gerer_listes': True,
        'gerer_utilisateurs': True,
    },
}


def has_permission(user_role: str, action: str) -> bool:
    """
    Vérifie si un utilisateur a les droits pour une action

    Args:
        user_role: Rôle de l'utilisateur
        action: Action à vérifier

    Returns:
        True si l'utilisateur a les droits, False sinon
    """
    if user_role not in PERMISSIONS:
        return False

    return PERMISSIONS[user_role].get(action, False)


def get_user_permissions(user_role: str) -> dict:
    """Retourne le dictionnaire complet des permissions pour un rôle"""
    return PERMISSIONS.get(user_role, {})
