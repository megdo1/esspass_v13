"""Matrice des droits affichée à l'écran Utilisateurs (sans dépendance Qt, donc testable en CI).

Les valeurs viennent de `utils.auth.PERMISSIONS` (source unique des droits réellement appliqués).
Chaque nouveau droit de `PERMISSIONS` doit figurer ici avec son libellé : un test le vérifie.
"""

from app.utils.auth import PERMISSIONS

# (libellé affiché, clé de droit dans PERMISSIONS ; None = ouvert à tous les rôles)
MATRICE_DROITS = [
    ("Consulter les demandes", None),
    ("Consulter les archives", None),
    ("Consulter les rapports", 'rapports'),
    ("Exporter (demandes et rapports)", 'exporter'),
    ("Créer une demande", 'creer_demande'),
    ("Dupliquer une demande", 'dupliquer'),
    ("Modifier une demande", 'gerer'),
    ("Traiter une demande (réponse)", 'traiter'),
    ("Traitement en masse", 'gerer_masse'),
    ("Annuler une demande", 'annuler'),
    ("Lancer une collecte des mails", 'mettre_a_jour'),
    ("Archiver une demande", 'archiver'),
    ("Gérer les listes de valeurs", 'gerer_listes'),
    ("Gérer les utilisateurs et les responsables ES-PASS", 'gerer_utilisateurs'),
    ("Administrer les collectes (rattrapage)", 'gerer_collectes'),
]
ROLES_MATRICE = ("Consultant", "Membre MCO", "Administrateur")


def droit_accorde(role, cle):
    """True si le rôle possède le droit (ou si la ligne est ouverte à tous)."""
    return True if cle is None else bool(PERMISSIONS.get(role, {}).get(cle, False))
