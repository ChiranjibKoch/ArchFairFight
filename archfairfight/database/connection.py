"""
Database connection management for ArchFairFight.
"""

import asyncio
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure
import structlog

from ..config import get_config, get_db_config

logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.config = get_config()
        self.db_config = get_db_config()
    
    async def connect(self) -> bool:
        """Connect to MongoDB database."""
        try:
            self.client = AsyncIOMotorClient(
                self.config.mongodb_url,
                serverSelectionTimeoutMS=self.db_config.connection_timeout * 1000
            )
            
            # Test the connection
            await self.client.admin.command('ping')
            
            self.database = self.client[self.config.database_name]
            
            # Create indexes if enabled
            if self.db_config.enable_indexes:
                await self._create_indexes()
            
            logger.info("Connected to MongoDB", database=self.config.database_name)
            return True
            
        except ConnectionFailure as e:
            logger.error("Failed to connect to MongoDB", error=str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error connecting to MongoDB", error=str(e))
            return False
    
    async def disconnect(self):
        """Disconnect from MongoDB database."""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance."""
        if not self.database:
            return
        
        try:
            # Users collection indexes
            users_collection = self.database[self.db_config.users_collection]
            await users_collection.create_index("telegram_id", unique=True)
            await users_collection.create_index("username")
            await users_collection.create_index("created_at")
            
            # Challenges collection indexes
            challenges_collection = self.database[self.db_config.challenges_collection]
            await challenges_collection.create_index("challenger_id")
            await challenges_collection.create_index("opponent_id")
            await challenges_collection.create_index("status")
            await challenges_collection.create_index("challenge_expires_at")
            await challenges_collection.create_index("created_at")
            await challenges_collection.create_index([("challenger_id", 1), ("opponent_id", 1)])
            
            # Fights collection indexes
            fights_collection = self.database[self.db_config.fights_collection]
            await fights_collection.create_index("challenge_id")
            await fights_collection.create_index("participant1_id")
            await fights_collection.create_index("participant2_id")
            await fights_collection.create_index("winner_id")
            await fights_collection.create_index("fight_type")
            await fights_collection.create_index("started_at")
            await fights_collection.create_index("created_at")
            
            # Recordings collection indexes
            recordings_collection = self.database[self.db_config.recordings_collection]
            await recordings_collection.create_index("fight_id")
            await recordings_collection.create_index("is_processed")
            await recordings_collection.create_index("is_uploaded")
            await recordings_collection.create_index("recorded_at")
            await recordings_collection.create_index("created_at")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error("Failed to create database indexes", error=str(e))
    
    def get_database(self) -> Optional[AsyncIOMotorDatabase]:
        """Get the database instance."""
        return self.database
    
    def get_collection(self, collection_name: str):
        """Get a specific collection."""
        if not self.database:
            raise RuntimeError("Database not connected")
        return self.database[collection_name]


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
        connected = await _db_manager.connect()
        if not connected:
            raise RuntimeError("Failed to connect to database")
    
    return _db_manager


async def get_database() -> AsyncIOMotorDatabase:
    """Get the database instance."""
    db_manager = await get_database_manager()
    db = db_manager.get_database()
    if db is None:
        raise RuntimeError("Database not connected")
    return db


async def close_database():
    """Close the database connection."""
    global _db_manager
    if _db_manager:
        await _db_manager.disconnect()
        _db_manager = None