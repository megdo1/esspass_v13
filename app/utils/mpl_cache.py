"""Cache matplotlib : garantit que son dossier de configuration existe.

Dans une application PyInstaller, matplotlib peut utiliser un dossier temporaire jetable.
Si ce dossier est nettoyé (Windows, outil IT) pendant que l'application reste ouverte,
matplotlib échoue à écrire son cache de polices (FileNotFoundError ... .matplotlib-lock).
"""

import logging
import os

logger = logging.getLogger(__name__)


def ensure_mpl_cache_dir():
    """Recrée le dossier de configuration/cache matplotlib s'il a disparu."""
    try:
        import matplotlib
        for path in {matplotlib.get_configdir(), matplotlib.get_cachedir()}:
            os.makedirs(path, exist_ok=True)
    except Exception:
        logger.debug("Impossible de vérifier le dossier de cache matplotlib", exc_info=True)
