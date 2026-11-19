"""Garde-fou : toute méthode appelée sur le gestionnaire de données doit exister.

Une régression remontée par un client venait d'un appel à `data_manager.ajouter_image_inline(...)`
alors que cette méthode n'a jamais existé : l'erreur n'apparaissait qu'au traitement d'un mail réel.
Ce test parcourt tout le code de `app/` et vérifie les appels du type `<gestionnaire>.methode(...)`.
"""

import ast
import glob
import os

import pytest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMS_GESTIONNAIRE = {"data_manager", "datamanager", "dm"}


def _appels_gestionnaire():
    """Retourne [(fichier, ligne, nom_de_methode)] pour chaque appel sur un gestionnaire de données."""
    appels = []
    for chemin in glob.glob(os.path.join(RACINE, "app", "**", "*.py"), recursive=True):
        with open(chemin, encoding="utf8") as f:
            arbre = ast.parse(f.read(), chemin)
        for noeud in ast.walk(arbre):
            if not (isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Attribute)):
                continue
            cible = noeud.func.value
            nom = cible.id if isinstance(cible, ast.Name) else cible.attr if isinstance(cible, ast.Attribute) else None
            if nom in NOMS_GESTIONNAIRE:
                appels.append((os.path.relpath(chemin, RACINE), noeud.lineno, noeud.func.attr))
    return appels


def test_le_parcours_trouve_des_appels():
    # Si ce test échoue, le garde-fou ne vérifie plus rien (renommage de variable, etc.)
    assert len(_appels_gestionnaire()) > 100


def test_toutes_les_methodes_appelees_existent(dm):
    manquantes = sorted({f"{fichier}:{ligne} -> {methode}()"
                         for fichier, ligne, methode in _appels_gestionnaire()
                         if not hasattr(dm, methode)})
    assert not manquantes, "Méthodes appelées mais inexistantes sur DataManager :\n" + "\n".join(manquantes)
