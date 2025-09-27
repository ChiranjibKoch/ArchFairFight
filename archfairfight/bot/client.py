"""
Bot client implementation for ArchFairFight.
"""

import asyncio
from typing import Optional
from pyrogram import Client
from pyrogram.errors import AuthKeyInvalid, UserDeactivated
import structlog

from ..config import get_config
from ..database import get_database_manager, close_database
from .handlers import setup_handlers

logger = structlog.get_logger(__name__)


class ArchFairFightBot:
    """Main bot client class."""
    
    def __init__(self):
        self.config = get_config()
        self.client: Optional[Client] = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Initialize the bot."""
        try:
            # Initialize database
            db_manager = await get_database_manager()
            logger.info("Database initialized successfully")
            
            # Initialize Pyrogram client
            self.client = Client(
                "archfairfight_bot",
                api_id=self.config.api_id,
                api_hash=self.config.api_hash,
                bot_token=self.config.bot_token,
                workdir="sessions"
            )
            
            # Setup handlers
            setup_handlers(self.client)
            
            logger.info("Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize bot", error=str(e))
            return False
    
    async def start(self):
        """Start the bot."""
        if not self.client:
            raise RuntimeError("Bot not initialized")
        
        try:
            await self.client.start()
            self.is_running = True
            
            bot_info = await self.client.get_me()
            logger.info("Bot started", 
                       bot_id=bot_info.id, 
                       bot_username=bot_info.username,
                       bot_name=bot_info.first_name)
            
            # Start background tasks
            asyncio.create_task(self._background_tasks())
            
        except (AuthKeyInvalid, UserDeactivated) as e:
            logger.error("Bot authentication failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to start bot", error=str(e))
            raise
    
    async def stop(self):
        """Stop the bot."""
        if self.client and self.is_running:
            try:
                await self.client.stop()
                self.is_running = False
                logger.info("Bot stopped")
                
                # Close database connection
                await close_database()
                
            except Exception as e:
                logger.error("Error stopping bot", error=str(e))
    
    async def _background_tasks(self):
        """Background tasks for the bot."""
        from ..challenge import ChallengeManager
        
        challenge_manager = ChallengeManager()
        
        while self.is_running:
            try:
                # Expire old challenges every minute
                expired_count = await challenge_manager.expire_old_challenges()
                if expired_count > 0:
                    logger.info("Expired old challenges", count=expired_count)
                
                # Wait for 60 seconds before next cleanup
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error("Error in background tasks", error=str(e))
                await asyncio.sleep(60)
    
    def get_client(self) -> Optional[Client]:
        """Get the Pyrogram client."""
        return self.client