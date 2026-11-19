"""Petits libellés d'affichage sans dépendance Qt (testables en CI)."""


def avertissement_limite(nb_chargees: int, limite: int) -> str:
    """Texte d'alerte quand le tableau a atteint la limite de chargement (des demandes ne sont donc pas affichées).

    Retourne une chaîne vide tant que la limite n'est pas atteinte.
    """
    if not limite or nb_chargees < limite:
        return ""
    return (f" — ⚠️ limite de chargement atteinte ({limite} demandes) : des demandes ne sont pas affichées, "
            "augmentez la limite dans Configuration > Général")
