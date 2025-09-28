"""
Bot package for ArchFairFight.
"""

from .client import ArchFairFightBot
from .handlers import setup_handlers
from .utils import get_user_mention, format_duration

__all__ = [
    "ArchFairFightBot",
    "setup_handlers",
    "get_user_mention",
    "format_duration"
]