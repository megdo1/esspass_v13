"""Configuration centralisée des logs (fichier rotatif dans %APPDATA%\ES-PIGC)."""

import logging
import os
from logging.handlers import RotatingFileHandler

_CONFIGURED = False


def setup_logging(level: int = None) -> str:
    """
    Configure le logger racine une seule fois. À appeler depuis main.py.
    Niveau par défaut : INFO (surchargeable via la variable ESPIGC_LOG_LEVEL).
    Retourne le chemin du fichier de log.
    """
    global _CONFIGURED
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    log_path = os.path.join(base, "ES-PIGC", "app.log")
    if _CONFIGURED:
        return log_path

    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if level is None:
        level = getattr(logging, os.environ.get("ESPIGC_LOG_LEVEL", "INFO").upper(), logging.INFO)

    handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s"))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    _CONFIGURED = True
    return log_path
