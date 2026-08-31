"""CCNA Quiz Backend API."""
__version__ = "0.1.0"

from .config import get_settings
from .database import get_db, init_db

__all__ = ["get_settings", "get_db", "init_db"]
