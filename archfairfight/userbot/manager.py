"""
Userbot manager for coordinating multiple userbots.
"""

import asyncio
from typing import List, Optional, Dict, Any
import structlog

from ..config import get_config
from .controller import UserbotController

logger = structlog.get_logger(__name__)


class UserbotManager:
    """Manages multiple userbots for fight monitoring."""
    
    def __init__(self):
        self.config = get_config()
        self.userbots: List[UserbotController] = []
        self.available_userbots: List[UserbotController] = []
        self.active_fights: Dict[str, UserbotController] = {}
    
    async def initialize(self) -> bool:
        """Initialize all userbots."""
        try:
            if not self.config.userbot_sessions:
                logger.warning("No userbot sessions configured")
                return False
            
            # Initialize each userbot
            for session_path in self.config.userbot_sessions:
                try:
                    session_name = session_path.replace('.session', '')
                    userbot = UserbotController(
                        session_name=session_name,
                        api_id=self.config.api_id,
                        api_hash=self.config.api_hash
                    )
                    
                    if await userbot.start():
                        self.userbots.append(userbot)
                        self.available_userbots.append(userbot)
                        logger.info("Userbot initialized", session=session_name)
                    else:
                        logger.error("Failed to start userbot", session=session_name)
                        
                except Exception as e:
                    logger.error("Error initializing userbot", session=session_path, error=str(e))
            
            if len(self.userbots) == 0:
                logger.error("No userbots could be initialized")
                return False
            
            logger.info("Userbot manager initialized", count=len(self.userbots))
            return True
            
        except Exception as e:
            logger.error("Failed to initialize userbot manager", error=str(e))
            return False
    
    async def shutdown(self):
        """Shutdown all userbots."""
        try:
            for userbot in self.userbots:
                await userbot.stop()
            
            self.userbots.clear()
            self.available_userbots.clear()
            self.active_fights.clear()
            
            logger.info("Userbot manager shutdown complete")
            
        except Exception as e:
            logger.error("Error during userbot manager shutdown", error=str(e))
    
    def get_available_userbot(self) -> Optional[UserbotController]:
        """Get an available userbot for a fight."""
        if self.available_userbots:
            return self.available_userbots.pop(0)
        return None
    
    def release_userbot(self, userbot: UserbotController):
        """Release a userbot back to the available pool."""
        if userbot not in self.available_userbots:
            self.available_userbots.append(userbot)
    
    async def assign_userbot_to_fight(self, fight_id: str, chat_id: int, 
                                    participant1_id: int, participant2_id: int) -> bool:
        """Assign a userbot to monitor a fight."""
        try:
            userbot = self.get_available_userbot()
            if not userbot:
                logger.error("No available userbots for fight", fight_id=fight_id)
                return False
            
            # Join the voice chat
            if not await userbot.join_voice_chat(chat_id):
                self.release_userbot(userbot)
                return False
            
            # Start fight monitoring
            await userbot.start_fight_monitoring(fight_id, participant1_id, participant2_id)
            
            # Track the assignment
            self.active_fights[fight_id] = userbot
            
            logger.info("Userbot assigned to fight", fight_id=fight_id, chat_id=chat_id)
            return True
            
        except Exception as e:
            logger.error("Error assigning userbot to fight", fight_id=fight_id, error=str(e))
            return False
    
    async def cleanup_fight(self, participant1_id: int, participant2_id: int, chat_id: Optional[int] = None):
        """Clean up userbots after a fight."""
        try:
            # Find and clean up any userbots assigned to these participants
            fights_to_cleanup = []
            
            for fight_id, userbot in self.active_fights.items():
                if userbot.is_monitoring_fight():
                    # Stop monitoring
                    await userbot.stop_fight_monitoring()
                    
                    # Leave voice chat if chat_id provided
                    if chat_id:
                        await userbot.leave_voice_chat(chat_id)
                    
                    # Release userbot
                    self.release_userbot(userbot)
                    fights_to_cleanup.append(fight_id)
            
            # Remove from active fights
            for fight_id in fights_to_cleanup:
                del self.active_fights[fight_id]
            
            logger.info("Fight cleanup completed", participant1_id=participant1_id, participant2_id=participant2_id)
            
        except Exception as e:
            logger.error("Error during fight cleanup", error=str(e))
    
    async def check_participants_joined(self, participant1_id: int, participant2_id: int) -> bool:
        """Check if both participants have joined the voice chat."""
        try:
            # For now, we'll simulate this check
            # In a real implementation, you would check with the assigned userbot
            # or query the Telegram API directly
            
            # Simulate a 50% chance that both participants joined
            # This is a placeholder - implement actual participant checking logic
            import random
            return random.choice([True, False])
            
        except Exception as e:
            logger.error("Error checking participants", error=str(e))
            return False
    
    async def are_participants_active(self, participant1_id: int, participant2_id: int) -> bool:
        """Check if participants are still active in the voice chat."""
        try:
            # For now, simulate this check
            # In a real implementation, you would check with the assigned userbot
            import random
            return random.choice([True, False])
            
        except Exception as e:
            logger.error("Error checking participant activity", error=str(e))
            return False
    
    async def get_fight_metrics(self, participant1_id: int, participant2_id: int) -> Optional[Dict[str, Any]]:
        """Get current fight metrics for participants."""
        try:
            # Find the userbot monitoring these participants
            for fight_id, userbot in self.active_fights.items():
                if userbot.is_monitoring_fight():
                    metrics = userbot.get_current_metrics()
                    
                    # Map participant IDs to metrics
                    if participant1_id in metrics and participant2_id in metrics:
                        return {
                            'participant1': metrics[participant1_id],
                            'participant2': metrics[participant2_id]
                        }
            
            return None
            
        except Exception as e:
            logger.error("Error getting fight metrics", error=str(e))
            return None
    
    async def mute_participant(self, chat_id: int, user_id: int) -> bool:
        """Mute a participant using any available userbot."""
        try:
            for userbot in self.userbots:
                if await userbot.mute_participant(chat_id, user_id):
                    return True
            return False
            
        except Exception as e:
            logger.error("Error muting participant", error=str(e))
            return False
    
    async def unmute_participant(self, chat_id: int, user_id: int) -> bool:
        """Unmute a participant using any available userbot."""
        try:
            for userbot in self.userbots:
                if await userbot.unmute_participant(chat_id, user_id):
                    return True
            return False
            
        except Exception as e:
            logger.error("Error unmuting participant", error=str(e))
            return False
    
    async def change_call_title(self, chat_id: int, title: str) -> bool:
        """Change the group call title using any available userbot."""
        try:
            for userbot in self.userbots:
                if await userbot.change_group_call_title(chat_id, title):
                    return True
            return False
            
        except Exception as e:
            logger.error("Error changing call title", error=str(e))
            return False
    
    async def start_recording(self, chat_id: int, video: bool = False) -> bool:
        """Start recording using any available userbot."""
        try:
            for userbot in self.userbots:
                if await userbot.start_recording(chat_id, video=video):
                    return True
            return False
            
        except Exception as e:
            logger.error("Error starting recording", error=str(e))
            return False
    
    async def stop_recording(self, chat_id: int) -> bool:
        """Stop recording using any available userbot."""
        try:
            for userbot in self.userbots:
                if await userbot.stop_recording(chat_id):
                    return True
            return False
            
        except Exception as e:
            logger.error("Error stopping recording", error=str(e))
            return False
    
    def get_available_userbot_count(self) -> int:
        """Get number of available userbots."""
        return len(self.available_userbots)
    
    def get_total_userbot_count(self) -> int:
        """Get total number of userbots."""
        return len(self.userbots)
    
    def get_active_fight_count(self) -> int:
        """Get number of active fights being monitored."""
        return len(self.active_fights)