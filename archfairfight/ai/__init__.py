"""
AI features package for ArchFairFight.
"""

from .winner_detector import WinnerDetector
from .stats_analyzer import StatsAnalyzer

__all__ = [
    "WinnerDetector",
    "StatsAnalyzer"
]