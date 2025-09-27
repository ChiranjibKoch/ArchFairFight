"""
Bot utilities for ArchFairFight.
"""

from typing import Optional
from pyrogram.types import User


def get_user_mention(user: User) -> str:
    """Get a user mention string."""
    if user.username:
        return f"@{user.username}"
    else:
        full_name = user.first_name
        if user.last_name:
            full_name += f" {user.last_name}"
        return f"[{full_name}](tg://user?id={user.id})"


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{minutes}m {remaining_seconds}s"
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"


def parse_user_identifier(identifier: str) -> tuple[Optional[str], Optional[int]]:
    """Parse user identifier (username, user ID, or mention)."""
    # Remove @ if present
    if identifier.startswith('@'):
        return identifier[1:], None
    
    # Check if it's a numeric ID
    try:
        user_id = int(identifier)
        return None, user_id
    except ValueError:
        pass
    
    # Check if it's a mention format [text](tg://user?id=123)
    if identifier.startswith('[') and 'tg://user?id=' in identifier:
        try:
            start = identifier.find('tg://user?id=') + 13
            end = identifier.find(')', start)
            user_id = int(identifier[start:end])
            return None, user_id
        except (ValueError, IndexError):
            pass
    
    # Assume it's a username without @
    return identifier, None


def format_fight_result(participant1_name: str, participant2_name: str, 
                       winner_name: Optional[str], fight_type: str, duration: int) -> str:
    """Format fight result message."""
    duration_str = format_duration(duration)
    
    if winner_name:
        return (
            f"🏆 **Fight Result**\n\n"
            f"👥 **Participants:** {participant1_name} vs {participant2_name}\n"
            f"⚔️ **Fight Type:** {fight_type.title()}\n"
            f"⏱ **Duration:** {duration_str}\n"
            f"🥇 **Winner:** {winner_name}\n\n"
            f"Great fight! 🎉"
        )
    else:
        return (
            f"🤝 **Fight Result**\n\n"
            f"👥 **Participants:** {participant1_name} vs {participant2_name}\n"
            f"⚔️ **Fight Type:** {fight_type.title()}\n"
            f"⏱ **Duration:** {duration_str}\n"
            f"📊 **Result:** Draw\n\n"
            f"Well fought by both! 🤝"
        )


def format_user_stats(user_data: dict) -> str:
    """Format user statistics message."""
    total_fights = user_data.get('total_fights', 0)
    wins = user_data.get('wins', 0)
    losses = user_data.get('losses', 0)
    draws = user_data.get('draws', 0)
    
    win_rate = (wins / total_fights * 100) if total_fights > 0 else 0
    
    return (
        f"📊 **Your Fight Statistics**\n\n"
        f"⚔️ **Total Fights:** {total_fights}\n"
        f"🏆 **Wins:** {wins}\n"
        f"💔 **Losses:** {losses}\n"
        f"🤝 **Draws:** {draws}\n"
        f"📈 **Win Rate:** {win_rate:.1f}%\n"
    )


def format_leaderboard(users: list) -> str:
    """Format leaderboard message."""
    if not users:
        return "📊 **Leaderboard**\n\nNo fighters yet! Be the first to start a challenge!"
    
    message = "🏆 **Top Fighters Leaderboard**\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, user in enumerate(users):
        medal = medals[i] if i < 3 else f"{i+1}."
        username = user.get('username', 'Unknown')
        wins = user.get('wins', 0)
        total_fights = user.get('total_fights', 0)
        win_rate = (wins / total_fights * 100) if total_fights > 0 else 0
        
        message += f"{medal} **@{username}** - {wins} wins ({win_rate:.1f}%)\n"
    
    return message