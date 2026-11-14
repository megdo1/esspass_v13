"""Résolution centralisée des chemins de l'application (script, PyInstaller)."""

import os
import sys

_DEFAULT_CONFIG = os.path.join("config", "config.json")


def app_base_dir() -> str:
    """Dossier de l'application : dossier de l'exe (PyInstaller) ou racine du projet."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def bundle_dir() -> str:
    """Dossier des ressources embarquées (_MEIPASS en PyInstaller, sinon racine du projet)."""
    return getattr(sys, "_MEIPASS", None) or app_base_dir()


def resolve_config_path(rel_path: str = _DEFAULT_CONFIG) -> str:
    """
    Cherche le fichier de configuration. Ordre :
      1. répertoire courant (comportement historique),
      2. dossier de l'application,
      3. ressources embarquées.
    Si rien n'existe, retourne le chemin historique (répertoire courant).
    """
    candidates = [
        os.path.join(os.getcwd(), rel_path),
        os.path.join(app_base_dir(), rel_path),
        os.path.join(bundle_dir(), rel_path),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return candidates[0]
