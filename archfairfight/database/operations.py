"""
Database operations for ArchFairFight.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import structlog

from .models import Challenge, User, Fight, Recording, ChallengeStatus, FightResult
from .connection import get_database
from ..config import get_db_config

logger = structlog.get_logger(__name__)


class BaseOperations:
    """Base operations class."""
    
    def __init__(self):
        self.db_config = get_db_config()
    
    async def get_db(self) -> AsyncIOMotorDatabase:
        """Get database instance."""
        return await get_database()


class UserOps(BaseOperations):
    """User database operations."""
    
    async def create_user(self, user: User) -> Optional[str]:
        """Create a new user."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.users_collection]
            
            result = await collection.insert_one(user.dict(by_alias=True, exclude={"id"}))
            logger.info("User created", user_id=str(result.inserted_id), telegram_id=user.telegram_id)
            return str(result.inserted_id)
            
        except DuplicateKeyError:
            logger.warning("User already exists", telegram_id=user.telegram_id)
            return None
        except Exception as e:
            logger.error("Failed to create user", error=str(e), telegram_id=user.telegram_id)
            return None
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.users_collection]
            
            user_data = await collection.find_one({"telegram_id": telegram_id})
            if user_data:
                return User(**user_data)
            return None
            
        except Exception as e:
            logger.error("Failed to get user", error=str(e), telegram_id=telegram_id)
            return None
    
    async def update_user_stats(self, telegram_id: int, **stats) -> bool:
        """Update user statistics."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.users_collection]
            
            update_data = {f"${k}": v for k, v in stats.items()}
            update_data["updated_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"telegram_id": telegram_id},
                {"$inc": stats, "$set": {"updated_at": datetime.utcnow()}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error("Failed to update user stats", error=str(e), telegram_id=telegram_id)
            return False
    
    async def get_leaderboard(self, limit: int = 10) -> List[User]:
        """Get user leaderboard."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.users_collection]
            
            cursor = collection.find({"is_active": True}).sort("wins", -1).limit(limit)
            users = []
            async for user_data in cursor:
                users.append(User(**user_data))
            
            return users
            
        except Exception as e:
            logger.error("Failed to get leaderboard", error=str(e))
            return []


class ChallengeOps(BaseOperations):
    """Challenge database operations."""
    
    async def create_challenge(self, challenge: Challenge) -> Optional[str]:
        """Create a new challenge."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.challenges_collection]
            
            result = await collection.insert_one(challenge.dict(by_alias=True, exclude={"id"}))
            logger.info("Challenge created", challenge_id=str(result.inserted_id))
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error("Failed to create challenge", error=str(e))
            return None
    
    async def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Get challenge by ID."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.challenges_collection]
            
            challenge_data = await collection.find_one({"_id": ObjectId(challenge_id)})
            if challenge_data:
                return Challenge(**challenge_data)
            return None
            
        except Exception as e:
            logger.error("Failed to get challenge", error=str(e), challenge_id=challenge_id)
            return None
    
    async def update_challenge_status(self, challenge_id: str, status: ChallengeStatus, **kwargs) -> bool:
        """Update challenge status."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.challenges_collection]
            
            update_data = {"status": status, "updated_at": datetime.utcnow()}
            update_data.update(kwargs)
            
            result = await collection.update_one(
                {"_id": ObjectId(challenge_id)},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error("Failed to update challenge status", error=str(e), challenge_id=challenge_id)
            return False
    
    async def get_pending_challenges(self, telegram_id: int) -> List[Challenge]:
        """Get pending challenges for a user."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.challenges_collection]
            
            cursor = collection.find({
                "opponent_id": telegram_id,
                "status": ChallengeStatus.PENDING,
                "challenge_expires_at": {"$gt": datetime.utcnow()}
            })
            
            challenges = []
            async for challenge_data in cursor:
                challenges.append(Challenge(**challenge_data))
            
            return challenges
            
        except Exception as e:
            logger.error("Failed to get pending challenges", error=str(e), telegram_id=telegram_id)
            return []
    
    async def expire_old_challenges(self) -> int:
        """Expire old challenges."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.challenges_collection]
            
            result = await collection.update_many(
                {
                    "status": ChallengeStatus.PENDING,
                    "challenge_expires_at": {"$lt": datetime.utcnow()}
                },
                {"$set": {"status": ChallengeStatus.EXPIRED, "updated_at": datetime.utcnow()}}
            )
            
            return result.modified_count
            
        except Exception as e:
            logger.error("Failed to expire old challenges", error=str(e))
            return 0


class FightOps(BaseOperations):
    """Fight database operations."""
    
    async def create_fight(self, fight: Fight) -> Optional[str]:
        """Create a new fight."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.fights_collection]
            
            result = await collection.insert_one(fight.dict(by_alias=True, exclude={"id"}))
            logger.info("Fight created", fight_id=str(result.inserted_id))
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error("Failed to create fight", error=str(e))
            return None
    
    async def get_fight(self, fight_id: str) -> Optional[Fight]:
        """Get fight by ID."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.fights_collection]
            
            fight_data = await collection.find_one({"_id": ObjectId(fight_id)})
            if fight_data:
                return Fight(**fight_data)
            return None
            
        except Exception as e:
            logger.error("Failed to get fight", error=str(e), fight_id=fight_id)
            return None
    
    async def update_fight_metrics(self, fight_id: str, participant_id: int, metrics: Dict[str, Any]) -> bool:
        """Update fight participant metrics."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.fights_collection]
            
            fight = await self.get_fight(fight_id)
            if not fight:
                return False
            
            field_name = "participant1_metrics" if participant_id == fight.participant1_id else "participant2_metrics"
            
            result = await collection.update_one(
                {"_id": ObjectId(fight_id)},
                {"$set": {field_name: metrics}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error("Failed to update fight metrics", error=str(e), fight_id=fight_id)
            return False
    
    async def finish_fight(self, fight_id: str, winner_id: Optional[int], 
                          participant1_result: FightResult, participant2_result: FightResult) -> bool:
        """Finish a fight with results."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.fights_collection]
            
            result = await collection.update_one(
                {"_id": ObjectId(fight_id)},
                {"$set": {
                    "winner_id": winner_id,
                    "participant1_result": participant1_result,
                    "participant2_result": participant2_result,
                    "ended_at": datetime.utcnow()
                }}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error("Failed to finish fight", error=str(e), fight_id=fight_id)
            return False
    
    async def get_user_fight_history(self, telegram_id: int, limit: int = 10) -> List[Fight]:
        """Get user's fight history."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.fights_collection]
            
            cursor = collection.find({
                "$or": [
                    {"participant1_id": telegram_id},
                    {"participant2_id": telegram_id}
                ]
            }).sort("created_at", -1).limit(limit)
            
            fights = []
            async for fight_data in cursor:
                fights.append(Fight(**fight_data))
            
            return fights
            
        except Exception as e:
            logger.error("Failed to get user fight history", error=str(e), telegram_id=telegram_id)
            return []


class RecordingOps(BaseOperations):
    """Recording database operations."""
    
    async def create_recording(self, recording: Recording) -> Optional[str]:
        """Create a new recording."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.recordings_collection]
            
            result = await collection.insert_one(recording.dict(by_alias=True, exclude={"id"}))
            logger.info("Recording created", recording_id=str(result.inserted_id))
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error("Failed to create recording", error=str(e))
            return None
    
    async def get_recording(self, recording_id: str) -> Optional[Recording]:
        """Get recording by ID."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.recordings_collection]
            
            recording_data = await collection.find_one({"_id": ObjectId(recording_id)})
            if recording_data:
                return Recording(**recording_data)
            return None
            
        except Exception as e:
            logger.error("Failed to get recording", error=str(e), recording_id=recording_id)
            return None
    
    async def get_recording_by_fight(self, fight_id: str) -> Optional[Recording]:
        """Get recording by fight ID."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.recordings_collection]
            
            recording_data = await collection.find_one({"fight_id": ObjectId(fight_id)})
            if recording_data:
                return Recording(**recording_data)
            return None
            
        except Exception as e:
            logger.error("Failed to get recording by fight", error=str(e), fight_id=fight_id)
            return None
    
    async def update_recording_status(self, recording_id: str, **kwargs) -> bool:
        """Update recording status."""
        try:
            db = await self.get_db()
            collection = db[self.db_config.recordings_collection]
            
            result = await collection.update_one(
                {"_id": ObjectId(recording_id)},
                {"$set": kwargs}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error("Failed to update recording status", error=str(e), recording_id=recording_id)
            return False