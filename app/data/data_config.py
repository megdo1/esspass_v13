import errno
import json
import logging
import os
from typing import Any, Dict, Optional

from app.utils.paths import resolve_config_path

logger = logging.getLogger(__name__)

CONFIG_FILE = resolve_config_path()

# Clés de la configuration qui contiennent des chemins de fichiers/dossiers
_PATH_KEYS = ("sqlite_path", "outlook_folder_path", "pieces_jointes_folder")


def _parse_json(raw: str) -> Dict[str, Any]:
    """
    Parse le JSON normalement. Si le fichier contient des chemins Windows écrits
    avec des backslashes simples (JSON invalide), on retente en les échappant
    (compatibilité avec les config.json existants).
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(raw.replace("\\", "\\\\"))


def loadConfig(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Charge la configuration depuis un fichier JSON.

    Args:
        config_file: chemin du fichier (par défaut : résolu automatiquement)

    Raises:
        FileNotFoundError: fichier introuvable
        json.JSONDecodeError: JSON malformé
        PermissionError: fichier illisible
    """
    config_file = config_file or resolve_config_path()

    if not os.path.isfile(config_file):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_file)

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            conf = _parse_json(f.read())
    except json.JSONDecodeError as e:
        logger.error("Erreur de parsing JSON dans %s (ligne %s, colonne %s): %s",
                     config_file, e.lineno, e.colno, e.msg)
        raise
    except PermissionError:
        logger.error("Permission refusée pour lire %s", config_file)
        raise

    if not isinstance(conf, dict):
        raise ValueError(
            "Le fichier de configuration doit contenir un objet JSON, "
            f"pas {type(conf).__name__}"
        )

    # Normalisation des chemins : toujours des "/"
    for key in _PATH_KEYS:
        if key in conf and isinstance(conf[key], str):
            conf[key] = conf[key].replace("\\", "/")

    return conf
