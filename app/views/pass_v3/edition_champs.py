"""Règles d'édition des champs depuis le tableau des demandes (sans Qt : testable seul).

Les champs modifiables sont ceux du dialogue « Gérer la demande » ; les champs calculés ou issus du mail
(priorité, ID, date de réception, pièces jointes...) ne le sont jamais.

Clés de `SPECS` = valeur de `champ_demande` des colonnes du tableau (clés des dicts de `get_demandes`).
"""

from datetime import datetime
from typing import Optional, Tuple

from app.utils.auth import has_permission

ETATS_AVEC_DATE = ('Traitée', 'Fermée')
ETATS_SANS_DATE = ('En cours de traitement', 'À étudier')

# type : liste (référentiel), responsable, categorie, sous_categorie, etat, date, texte_long, texte_court
SPECS = {
    'canal':          {'type': 'liste', 'ref': 'canaux', 'cle': 'id_canal', 'lib_demande': 'libelle_canal'},
    'domaine':        {'type': 'liste', 'ref': 'domaines', 'cle': 'id_domaine', 'lib_demande': 'libelle_domaine'},
    'nature':         {'type': 'liste', 'ref': 'natures', 'cle': 'id_nature', 'lib_demande': 'libelle_nature'},
    'impact':         {'type': 'liste', 'ref': 'impacts', 'cle': 'id_impact', 'lib_demande': 'libelle_impact'},
    'urgence':        {'type': 'liste', 'ref': 'urgences', 'cle': 'id_urgence', 'lib_demande': 'libelle_urgence'},
    'etat':           {'type': 'etat', 'ref': 'etats', 'cle': 'id_etat', 'lib_demande': 'libelle_etat'},
    'responsable':    {'type': 'responsable', 'cle': 'id_responsable', 'lib_demande': 'responsable'},
    'categorie':      {'type': 'categorie', 'ref': 'categories', 'cle': 'id_categorie',
                       'lib_demande': 'libelle_categorie'},
    'sous_categorie': {'type': 'sous_categorie', 'ref': 'sous_categories', 'cle': 'id_sous_categorie',
                       'lib_demande': 'libelle_sous_categorie'},
    'date_traitement': {'type': 'date', 'cle': 'date_traitement'},
    'resume':         {'type': 'texte_long', 'cle': 'resume'},
    'solution':       {'type': 'texte_long', 'cle': 'solution_suite_a_donner'},
    'commentaire':    {'type': 'texte_long', 'cle': 'commentaire'},
    'libelle':        {'type': 'texte_court', 'cle': 'libelle', 'manuel_seulement': True},
    'sujet':          {'type': 'texte_court', 'cle': 'sujet', 'manuel_seulement': True},
    'demandeur':      {'type': 'texte_court', 'cle': 'demandeur', 'manuel_seulement': True},
}

# Colonnes sans valeur éditable (cases à cocher, pièces jointes, boutons) : pas d'entrée de menu du tout
TYPES_COLONNE_SANS_EDITION = ('checkbox', 'icone', 'actions')

MESSAGES_NON_MODIFIABLE = {
    'priorite': "Priorité calculée automatiquement à partir de l'impact et de l'urgence",
    'id_demande': "Identifiant attribué automatiquement",
    'date_reception': "Date de réception du mail (non modifiable)",
    'pieces_jointes': "Pièces jointes du mail (non modifiables)",
}


def est_demande_manuelle(demande: dict) -> bool:
    """Demande créée dans l'application (et non issue d'un mail) : libellé/sujet/demandeur modifiables."""
    return str((demande or {}).get('conversation_id') or '').startswith('ESPASS')


def statut_edition(champ: str, type_col: str, demande: dict, role: Optional[str]) -> Tuple[Optional[bool], str]:
    """(modifiable, raison). modifiable None = pas d'entrée de menu ; False = entrée grisée avec la raison."""
    if type_col in TYPES_COLONNE_SANS_EDITION:
        return None, ""
    if type_col == 'priorite' or champ in MESSAGES_NON_MODIFIABLE:
        return False, MESSAGES_NON_MODIFIABLE.get(champ, MESSAGES_NON_MODIFIABLE['priorite'])
    spec = SPECS.get(champ)
    if spec is None:
        return False, "Champ non modifiable"
    if not role or not has_permission(role, 'gerer'):
        return False, "Vous n'avez pas le droit de modifier les demandes"
    if spec.get('manuel_seulement') and not est_demande_manuelle(demande):
        return False, "Demande issue d'un mail : ce champ n'est pas modifiable"
    if champ == 'date_traitement' and (demande or {}).get('libelle_etat') not in ETATS_AVEC_DATE:
        return False, "La date de traitement n'existe que pour les états Traitée ou Fermée"
    return True, ""


def etats_proposes(libelles, role):
    """Mêmes états que le dialogue Gérer : « Archivée » réservé à l'Administrateur."""
    return [e for e in libelles if e != "Archivée" or role == "Administrateur"]


def donnees_date_traitement(libelle_etat: str, texte_date: str, maintenant: Optional[datetime] = None):
    """Règle de la date de traitement selon l'état (identique au dialogue Gérer).

    Retourne (donnees, erreur) : `donnees` à fusionner dans la mise à jour (peut être vide), `erreur` un message
    pour l'utilisateur (alors rien ne doit être enregistré).
    """
    maintenant = maintenant or datetime.now()
    if libelle_etat in ETATS_AVEC_DATE:
        try:
            jour = datetime.strptime(texte_date, '%Y-%m-%d')
        except (TypeError, ValueError):
            return {}, "Le format de la date de traitement doit être : AAAA-MM-JJ"
        if jour > maintenant:
            return {}, ("La date de traitement ne peut pas être dans le futur.\n\n"
                        f"Date saisie : {jour:%Y-%m-%d}\nDate actuelle : {maintenant:%Y-%m-%d}")
        return {'date_traitement': texte_date}, None
    if libelle_etat in ETATS_SANS_DATE:
        return {'date_traitement': ''}, None
    return {}, None
