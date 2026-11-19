"""Fragments SQL partagés : affichage du nom d'un utilisateur (responsable, lanceur de collecte, listes).

Pourquoi : `u.nom || ' ' || u.prenom` vaut NULL dès que le nom ou le prénom est NULL (cas des comptes
Outlook qui renvoient des noms vides). Une demande pourtant affectée s'affichait alors « sans responsable »
et le tableau ne correspondait plus à la tuile « Demandes non affectées ».
"""


def sql_nom_utilisateur(alias: str) -> str:
    """Nom affichable d'un utilisateur : « nom prénom », à défaut son e-mail, sinon NULL."""
    return (f"COALESCE(NULLIF(TRIM(COALESCE({alias}.nom, '') || ' ' || COALESCE({alias}.prenom, '')), ''), "
            f"NULLIF({alias}.email, ''))")


def sql_nom_utilisateur_ou_repere(alias: str, id_col: str) -> str:
    """Comme `sql_nom_utilisateur`, mais jamais NULL : un compte sans nom ni e-mail est repéré par son numéro."""
    return f"COALESCE({sql_nom_utilisateur(alias)}, '(utilisateur #' || {id_col} || ' sans nom)')"


def sql_responsable(id_responsable_col: str, alias: str) -> str:
    """Libellé du responsable d'une demande (le LEFT JOIN utilisateurs `alias` doit exister).

    - pas de responsable (id NULL)  -> '' (c'est le seul cas « sans responsable »)
    - responsable supprimé           -> '(utilisateur #4 introuvable)'
    - responsable sans nom ni e-mail -> '(utilisateur #4 sans nom)'
    - sinon                          -> « nom prénom » (ou e-mail)
    """
    return (f"CASE WHEN {id_responsable_col} IS NULL THEN '' "
            f"WHEN {alias}.id_utilisateur IS NULL THEN '(utilisateur #' || {id_responsable_col} || ' introuvable)' "
            f"ELSE {sql_nom_utilisateur_ou_repere(alias, id_responsable_col)} END")


def sql_responsable_sous_requete(id_responsable_col: str) -> str:
    """Même libellé que `sql_responsable`, mais sans jointure : pour les requêtes qui n'ont pas de
    LEFT JOIN utilisateurs et dont les colonnes non qualifiées (created_at...) deviendraient ambiguës."""
    cible = f"x.id_utilisateur = {id_responsable_col}"
    return (f"CASE WHEN {id_responsable_col} IS NULL THEN '' "
            f"WHEN NOT EXISTS (SELECT 1 FROM utilisateurs x WHERE {cible}) "
            f"THEN '(utilisateur #' || {id_responsable_col} || ' introuvable)' "
            f"ELSE COALESCE((SELECT {sql_nom_utilisateur('x')} FROM utilisateurs x WHERE {cible}), "
            f"'(utilisateur #' || {id_responsable_col} || ' sans nom)') END")
