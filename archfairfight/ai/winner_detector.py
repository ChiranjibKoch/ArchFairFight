"""
AI-based winner detection for ArchFairFight.
"""

from typing import Optional, Dict, Any, Tuple
import structlog

from ..config import get_config
from ..database.models import FightType, FightResult

logger = structlog.get_logger(__name__)


class WinnerDetector:
    """AI-based winner detection system."""
    
    def __init__(self):
        self.config = get_config()
    
    async def determine_winner(self, fight_type: FightType, 
                             participant1_metrics: Dict[str, Any],
                             participant2_metrics: Dict[str, Any]) -> Tuple[Optional[int], FightResult, FightResult]:
        """
        Determine fight winner based on AI analysis.
        
        Returns:
            Tuple of (winner_participant_number, participant1_result, participant2_result)
            winner_participant_number: 1 for participant1, 2 for participant2, None for draw
        """
        try:
            if fight_type == FightType.TIMING:
                return await self._analyze_timing_fight(participant1_metrics, participant2_metrics)
            elif fight_type == FightType.VOLUME:
                return await self._analyze_volume_fight(participant1_metrics, participant2_metrics)
            else:
                logger.error("Unknown fight type", fight_type=fight_type)
                return None, FightResult.DRAW, FightResult.DRAW
                
        except Exception as e:
            logger.error("Error determining winner", error=str(e))
            return None, FightResult.DRAW, FightResult.DRAW
    
    async def _analyze_timing_fight(self, p1_metrics: Dict[str, Any], 
                                  p2_metrics: Dict[str, Any]) -> Tuple[Optional[int], FightResult, FightResult]:
        """Analyze timing-based fight."""
        try:
            # Get join times (how long each participant stayed)
            p1_join_time = p1_metrics.get('total_join_time', 0)
            p2_join_time = p2_metrics.get('total_join_time', 0)
            
            # Apply AI analysis (simple comparison for now, can be enhanced)
            time_difference = abs(p1_join_time - p2_join_time)
            
            # If the difference is very small (less than 5 seconds), it's a draw
            if time_difference < 5:
                return None, FightResult.DRAW, FightResult.DRAW
            
            # Winner is who stayed longer
            if p1_join_time > p2_join_time:
                return 1, FightResult.WIN, FightResult.LOSS
            else:
                return 2, FightResult.LOSS, FightResult.WIN
                
        except Exception as e:
            logger.error("Error analyzing timing fight", error=str(e))
            return None, FightResult.DRAW, FightResult.DRAW
    
    async def _analyze_volume_fight(self, p1_metrics: Dict[str, Any], 
                                  p2_metrics: Dict[str, Any]) -> Tuple[Optional[int], FightResult, FightResult]:
        """Analyze volume-based fight."""
        try:
            # Calculate activity scores based on multiple factors
            p1_score = self._calculate_activity_score(p1_metrics)
            p2_score = self._calculate_activity_score(p2_metrics)
            
            # Apply threshold for draws
            score_difference = abs(p1_score - p2_score)
            threshold = self.config.volume_threshold
            
            if score_difference < threshold:
                return None, FightResult.DRAW, FightResult.DRAW
            
            # Winner is who has higher activity score
            if p1_score > p2_score:
                return 1, FightResult.WIN, FightResult.LOSS
            else:
                return 2, FightResult.LOSS, FightResult.WIN
                
        except Exception as e:
            logger.error("Error analyzing volume fight", error=str(e))
            return None, FightResult.DRAW, FightResult.DRAW
    
    def _calculate_activity_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate activity score based on metrics."""
        try:
            # Base metrics
            speak_time = metrics.get('speak_time', 0)
            average_volume = metrics.get('average_volume', 0)
            total_join_time = metrics.get('total_join_time', 1)  # Avoid division by zero
            
            # Calculate speaking percentage
            speaking_percentage = speak_time / total_join_time if total_join_time > 0 else 0
            
            # Weighted activity score
            # Speaking time is weighted more heavily than volume
            activity_score = (
                speaking_percentage * 0.7 +  # 70% weight for speaking time
                (average_volume / 10000) * 0.3  # 30% weight for volume (normalized)
            )
            
            return activity_score
            
        except Exception as e:
            logger.error("Error calculating activity score", error=str(e))
            return 0.0
    
    async def analyze_fight_quality(self, participant1_metrics: Dict[str, Any],
                                  participant2_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the overall quality of the fight."""
        try:
            analysis = {
                'total_participants': 2,
                'fight_quality': 'good',  # good, fair, poor
                'engagement_level': 'high',  # high, medium, low
                'balance_rating': 0.5,  # 0.0 to 1.0, where 0.5 is perfectly balanced
                'notable_events': []
            }
            
            # Calculate engagement level
            p1_score = self._calculate_activity_score(participant1_metrics)
            p2_score = self._calculate_activity_score(participant2_metrics)
            
            total_engagement = p1_score + p2_score
            
            if total_engagement > 1.5:
                analysis['engagement_level'] = 'high'
                analysis['fight_quality'] = 'excellent'
            elif total_engagement > 1.0:
                analysis['engagement_level'] = 'medium'
                analysis['fight_quality'] = 'good'
            else:
                analysis['engagement_level'] = 'low'
                analysis['fight_quality'] = 'fair'
            
            # Calculate balance (how evenly matched the participants were)
            if p1_score + p2_score > 0:
                analysis['balance_rating'] = min(p1_score, p2_score) / max(p1_score, p2_score)
            
            # Notable events
            if participant1_metrics.get('speak_time', 0) > 60:
                analysis['notable_events'].append('Participant 1 spoke for over 1 minute')
            if participant2_metrics.get('speak_time', 0) > 60:
                analysis['notable_events'].append('Participant 2 spoke for over 1 minute')
            
            if analysis['balance_rating'] > 0.8:
                analysis['notable_events'].append('Very evenly matched fight')
            
            return analysis
            
        except Exception as e:
            logger.error("Error analyzing fight quality", error=str(e))
            return {'fight_quality': 'unknown', 'error': str(e)}
    
    async def get_winner_confidence(self, winner_participant: Optional[int], 
                                  participant1_metrics: Dict[str, Any],
                                  participant2_metrics: Dict[str, Any]) -> float:
        """Get confidence level for the winner determination (0.0 to 1.0)."""
        try:
            if winner_participant is None:
                return 0.5  # Draw has medium confidence
            
            p1_score = self._calculate_activity_score(participant1_metrics)
            p2_score = self._calculate_activity_score(participant2_metrics)
            
            # Calculate confidence based on score difference
            total_score = p1_score + p2_score
            if total_score == 0:
                return 0.5
            
            score_difference = abs(p1_score - p2_score)
            confidence = min(score_difference / total_score * 2, 1.0)
            
            return confidence
            
        except Exception as e:
            logger.error("Error calculating winner confidence", error=str(e))
            return 0.5