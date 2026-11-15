"""Exceptions de la couche d'accès aux données."""


class DatabaseError(Exception):
    """Erreur d'accès à la base (réseau coupé, base verrouillée, SQL invalide...).

    Levée par les méthodes « strictes » (`query_strict`, `update_strict`) pour que
    l'appelant puisse distinguer une erreur d'un résultat vide.
    """


class ConflitModificationError(Exception):
    """La demande a été modifiée (ou supprimée) par un autre utilisateur depuis son chargement."""
