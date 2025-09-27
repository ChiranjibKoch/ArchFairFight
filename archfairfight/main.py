"""
Main entry point for ArchFairFight bot.
"""

import asyncio
import signal
import sys
from typing import Optional
import structlog

from .config import get_config, setup_directories
from .utils.logging import setup_logging
from .bot import ArchFairFightBot
from .userbot import UserbotManager

logger: Optional[structlog.BoundLogger] = None


class ArchFairFightApp:
    """Main application class."""
    
    def __init__(self):
        self.config = get_config()
        self.bot: Optional[ArchFairFightBot] = None
        self.userbot_manager: Optional[UserbotManager] = None
        self.is_running = False
    
    async def startup(self) -> bool:
        """Start up the application."""
        try:
            global logger
            logger = setup_logging()
            logger.info("Starting ArchFairFight bot")
            
            # Setup directories
            setup_directories()
            
            # Initialize bot
            self.bot = ArchFairFightBot()
            if not await self.bot.initialize():
                logger.error("Failed to initialize bot")
                return False
            
            # Initialize userbot manager
            self.userbot_manager = UserbotManager()
            if not await self.userbot_manager.initialize():
                logger.warning("Failed to initialize userbot manager - fights may not work properly")
                # Continue anyway as bot can work without userbots for basic commands
            
            # Start bot
            await self.bot.start()
            self.is_running = True
            
            logger.info("ArchFairFight bot started successfully")
            return True
            
        except Exception as e:
            if logger:
                logger.error("Failed to start application", error=str(e))
            else:
                print(f"Failed to start application: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the application."""
        if logger:
            logger.info("Shutting down ArchFairFight bot")
        
        self.is_running = False
        
        try:
            # Stop userbot manager
            if self.userbot_manager:
                await self.userbot_manager.shutdown()
            
            # Stop bot
            if self.bot:
                await self.bot.stop()
            
            if logger:
                logger.info("ArchFairFight bot shutdown complete")
                
        except Exception as e:
            if logger:
                logger.error("Error during shutdown", error=str(e))
            else:
                print(f"Error during shutdown: {e}")
    
    async def run(self):
        """Run the application."""
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            if logger:
                logger.info("Received signal, initiating shutdown", signal=signum)
            else:
                print(f"Received signal {signum}, initiating shutdown")
            
            # Create shutdown task
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start the application
        if not await self.startup():
            return False
        
        try:
            # Keep running until shutdown
            while self.is_running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            if logger:
                logger.info("Keyboard interrupt received")
            else:
                print("Keyboard interrupt received")
        except Exception as e:
            if logger:
                logger.error("Unexpected error in main loop", error=str(e))
            else:
                print(f"Unexpected error: {e}")
        finally:
            await self.shutdown()
        
        return True


async def main():
    """Main entry point."""
    app = ArchFairFightApp()
    success = await app.run()
    sys.exit(0 if success else 1)


def cli_main():
    """CLI entry point for console_scripts."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Application failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()