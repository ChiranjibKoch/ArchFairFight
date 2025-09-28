"""
Statistics analyzer for ArchFairFight.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog

from ..database import UserOps, FightOps
from ..database.models import User, Fight

logger = structlog.get_logger(__name__)


class StatsAnalyzer:
    """Analyzes user and fight statistics."""
    
    def __init__(self):
        self.user_ops = UserOps()
        self.fight_ops = FightOps()
    
    async def generate_user_insights(self, telegram_id: int) -> Dict[str, Any]:
        """Generate insights for a specific user."""
        try:
            user = await self.user_ops.get_user_by_telegram_id(telegram_id)
            if not user:
                return {'error': 'User not found'}
            
            fight_history = await self.fight_ops.get_user_fight_history(telegram_id, limit=50)
            
            insights = {
                'user_id': telegram_id,
                'username': user.username,
                'total_fights': user.total_fights,
                'wins': user.wins,
                'losses': user.losses,
                'draws': user.draws,
                'win_rate': (user.wins / user.total_fights * 100) if user.total_fights > 0 else 0,
                'performance_trend': await self._analyze_performance_trend(fight_history),
                'favorite_fight_type': await self._get_favorite_fight_type(fight_history),
                'best_opponent': await self._get_best_opponent(fight_history),
                'longest_fight': await self._get_longest_fight(fight_history),
                'recent_activity': await self._analyze_recent_activity(fight_history),
                'skill_rating': await self._calculate_skill_rating(user, fight_history),
                'achievements': await self._get_achievements(user, fight_history)
            }
            
            return insights
            
        except Exception as e:
            logger.error("Error generating user insights", telegram_id=telegram_id, error=str(e))
            return {'error': str(e)}
    
    async def _analyze_performance_trend(self, fight_history: List[Fight]) -> str:
        """Analyze user's performance trend."""
        if len(fight_history) < 3:
            return 'insufficient_data'
        
        # Look at last 10 fights vs previous 10 fights
        recent_fights = fight_history[:10]
        older_fights = fight_history[10:20] if len(fight_history) > 10 else []
        
        if not older_fights:
            return 'improving'  # Default for new users
        
        recent_win_rate = sum(1 for fight in recent_fights 
                            if self._is_winner(fight)) / len(recent_fights)
        older_win_rate = sum(1 for fight in older_fights 
                           if self._is_winner(fight)) / len(older_fights)
        
        if recent_win_rate > older_win_rate + 0.1:
            return 'improving'
        elif recent_win_rate < older_win_rate - 0.1:
            return 'declining'
        else:
            return 'stable'
    
    def _is_winner(self, fight: Fight) -> bool:
        """Check if the user won a specific fight."""
        # This would need to be enhanced based on actual user context
        return fight.winner_id is not None
    
    async def _get_favorite_fight_type(self, fight_history: List[Fight]) -> Optional[str]:
        """Get user's most frequently played fight type."""
        if not fight_history:
            return None
        
        type_counts = {}
        for fight in fight_history:
            fight_type = fight.fight_type.value
            type_counts[fight_type] = type_counts.get(fight_type, 0) + 1
        
        return max(type_counts, key=type_counts.get) if type_counts else None
    
    async def _get_best_opponent(self, fight_history: List[Fight]) -> Optional[Dict[str, Any]]:
        """Get opponent user has best record against."""
        if not fight_history:
            return None
        
        opponent_records = {}
        
        for fight in fight_history:
            # Determine opponent (this is simplified - would need user context)
            opponent_id = fight.participant2_id  # Simplified assumption
            
            if opponent_id not in opponent_records:
                opponent_records[opponent_id] = {'wins': 0, 'total': 0}
            
            opponent_records[opponent_id]['total'] += 1
            if fight.winner_id:  # Simplified win check
                opponent_records[opponent_id]['wins'] += 1
        
        # Find opponent with best win rate (minimum 3 games)
        best_opponent = None
        best_rate = 0
        
        for opponent_id, record in opponent_records.items():
            if record['total'] >= 3:
                win_rate = record['wins'] / record['total']
                if win_rate > best_rate:
                    best_rate = win_rate
                    best_opponent = {
                        'opponent_id': opponent_id,
                        'wins': record['wins'],
                        'total': record['total'],
                        'win_rate': win_rate
                    }
        
        return best_opponent
    
    async def _get_longest_fight(self, fight_history: List[Fight]) -> Optional[Dict[str, Any]]:
        """Get user's longest fight."""
        if not fight_history:
            return None
        
        longest_fight = max(fight_history, key=lambda f: f.duration)
        
        return {
            'duration': longest_fight.duration,
            'fight_type': longest_fight.fight_type.value,
            'date': longest_fight.started_at,
            'opponent_id': longest_fight.participant2_id  # Simplified
        }
    
    async def _analyze_recent_activity(self, fight_history: List[Fight]) -> Dict[str, Any]:
        """Analyze user's recent activity."""
        now = datetime.utcnow()
        recent_fights = [f for f in fight_history 
                        if (now - f.started_at).days <= 7]
        
        return {
            'fights_this_week': len(recent_fights),
            'activity_level': 'high' if len(recent_fights) >= 5 else 
                            'medium' if len(recent_fights) >= 2 else 'low',
            'last_fight_date': fight_history[0].started_at if fight_history else None
        }
    
    async def _calculate_skill_rating(self, user: User, fight_history: List[Fight]) -> int:
        """Calculate a skill rating for the user (0-1000)."""
        base_rating = 500
        
        if user.total_fights == 0:
            return base_rating
        
        # Win rate impact
        win_rate = user.wins / user.total_fights
        win_bonus = (win_rate - 0.5) * 200  # -100 to +100
        
        # Experience impact
        experience_bonus = min(user.total_fights * 2, 100)  # Up to 100 points
        
        # Recent performance impact
        recent_fights = fight_history[:10]
        if recent_fights:
            recent_wins = sum(1 for fight in recent_fights if self._is_winner(fight))
            recent_bonus = (recent_wins / len(recent_fights) - 0.5) * 100
        else:
            recent_bonus = 0
        
        rating = int(base_rating + win_bonus + experience_bonus + recent_bonus)
        return max(0, min(1000, rating))  # Clamp between 0-1000
    
    async def _get_achievements(self, user: User, fight_history: List[Fight]) -> List[str]:
        """Get user's achievements."""
        achievements = []
        
        # Basic achievements
        if user.total_fights >= 1:
            achievements.append('First Fight')
        if user.total_fights >= 10:
            achievements.append('Veteran Fighter')
        if user.total_fights >= 50:
            achievements.append('Fight Master')
        if user.total_fights >= 100:
            achievements.append('Legend')
        
        # Win-based achievements
        if user.wins >= 5:
            achievements.append('Winner')
        if user.wins >= 20:
            achievements.append('Champion')
        if user.wins >= 50:
            achievements.append('Unstoppable')
        
        # Win rate achievements
        if user.total_fights >= 10:
            win_rate = user.wins / user.total_fights
            if win_rate >= 0.8:
                achievements.append('Dominator')
            elif win_rate >= 0.6:
                achievements.append('Skilled Fighter')
        
        # Streak achievements (would need streak tracking)
        # Special achievements based on fight history
        if fight_history:
            longest_fight = max(fight_history, key=lambda f: f.duration)
            if longest_fight.duration >= 300:  # 5 minutes
                achievements.append('Endurance Fighter')
        
        return achievements
    
    async def generate_global_stats(self) -> Dict[str, Any]:
        """Generate global platform statistics."""
        try:
            # Get top users
            top_users = await self.user_ops.get_leaderboard(limit=20)
            
            # Calculate global stats
            total_users = len(top_users)  # Simplified - would query total count
            total_fights = sum(user.total_fights for user in top_users)
            
            stats = {
                'total_users': total_users,
                'total_fights': total_fights,
                'top_fighters': [
                    {
                        'username': user.username,
                        'wins': user.wins,
                        'total_fights': user.total_fights,
                        'win_rate': (user.wins / user.total_fights * 100) if user.total_fights > 0 else 0
                    }
                    for user in top_users[:10]
                ],
                'fight_types_popularity': {
                    'timing': 60,  # Placeholder percentages
                    'volume': 40
                },
                'average_fight_duration': 120,  # Placeholder in seconds
                'most_active_day': 'Saturday',  # Placeholder
                'platform_growth': 'growing'  # Placeholder
            }
            
            return stats
            
        except Exception as e:
            logger.error("Error generating global stats", error=str(e))
            return {'error': str(e)}
    
    async def predict_fight_outcome(self, participant1_id: int, participant2_id: int) -> Dict[str, Any]:
        """Predict fight outcome based on historical data."""
        try:
            user1 = await self.user_ops.get_user_by_telegram_id(participant1_id)
            user2 = await self.user_ops.get_user_by_telegram_id(participant2_id)
            
            if not user1 or not user2:
                return {'error': 'One or both users not found'}
            
            # Simple prediction based on win rates and experience
            user1_skill = await self._calculate_skill_rating(user1, [])
            user2_skill = await self._calculate_skill_rating(user2, [])
            
            total_skill = user1_skill + user2_skill
            user1_win_probability = user1_skill / total_skill if total_skill > 0 else 0.5
            
            prediction = {
                'participant1_win_probability': user1_win_probability,
                'participant2_win_probability': 1 - user1_win_probability,
                'confidence': abs(user1_win_probability - 0.5) * 2,  # 0 to 1
                'predicted_winner': participant1_id if user1_win_probability > 0.5 else participant2_id,
                'fight_quality_prediction': 'high' if abs(user1_skill - user2_skill) < 100 else 'medium'
            }
            
            return prediction
            
        except Exception as e:
            logger.error("Error predicting fight outcome", error=str(e))
            return {'error': str(e)}