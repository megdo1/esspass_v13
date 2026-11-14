"""Package utils - Utilitaires pour l'application"""

from .auth import (
    get_current_user_from_outlook,
    has_permission,
    get_user_permissions,
    PERMISSIONS
)

__all__ = [
    'get_current_user_from_outlook',
    'has_permission',
    'get_user_permissions',
    'PERMISSIONS'
]
