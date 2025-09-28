"""
Database models for ArchFairFight.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId class for Pydantic compatibility."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class ChallengeStatus(str, Enum):
    """Challenge status enumeration."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class FightType(str, Enum):
    """Fight type enumeration."""
    TIMING = "timing"
    VOLUME = "volume"


class FightResult(str, Enum):
    """Fight result enumeration."""
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


class User(BaseModel):
    """User model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    
    # Statistics
    total_challenges: int = Field(default=0, description="Total challenges initiated")
    total_fights: int = Field(default=0, description="Total fights participated in")
    wins: int = Field(default=0, description="Number of wins")
    losses: int = Field(default=0, description="Number of losses")
    draws: int = Field(default=0, description="Number of draws")
    
    # Settings
    is_active: bool = Field(default=True, description="Whether user is active")
    allow_challenges: bool = Field(default=True, description="Whether to accept challenges")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Challenge(BaseModel):
    """Challenge model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    challenger_id: int = Field(..., description="Challenger's Telegram ID")
    opponent_id: int = Field(..., description="Opponent's Telegram ID")
    
    # Challenge details
    fight_type: Optional[FightType] = Field(None, description="Type of fight")
    status: ChallengeStatus = Field(default=ChallengeStatus.PENDING, description="Challenge status")
    
    # Group call info
    group_call_id: Optional[str] = Field(None, description="Group call ID")
    group_call_access_hash: Optional[str] = Field(None, description="Group call access hash")
    
    # Timing
    challenge_expires_at: datetime = Field(..., description="When the challenge expires")
    fight_starts_at: Optional[datetime] = Field(None, description="When the fight starts")
    fight_ends_at: Optional[datetime] = Field(None, description="When the fight ends")
    
    # Messages
    challenge_message_id: Optional[int] = Field(None, description="Challenge message ID")
    chat_id: Optional[int] = Field(None, description="Chat where challenge was sent")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Fight(BaseModel):
    """Fight result model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    challenge_id: PyObjectId = Field(..., description="Associated challenge ID")
    
    # Participants
    participant1_id: int = Field(..., description="First participant's Telegram ID")
    participant2_id: int = Field(..., description="Second participant's Telegram ID")
    
    # Fight details
    fight_type: FightType = Field(..., description="Type of fight")
    duration: int = Field(..., description="Fight duration in seconds")
    
    # Results
    winner_id: Optional[int] = Field(None, description="Winner's Telegram ID")
    participant1_result: FightResult = Field(..., description="First participant's result")
    participant2_result: FightResult = Field(..., description="Second participant's result")
    
    # Metrics
    participant1_metrics: Dict[str, Any] = Field(default_factory=dict, description="First participant's metrics")
    participant2_metrics: Dict[str, Any] = Field(default_factory=dict, description="Second participant's metrics")
    
    # Group call info
    group_call_id: str = Field(..., description="Group call ID")
    peak_participants: int = Field(default=0, description="Peak number of participants")
    
    # AI analysis
    ai_analysis: Optional[Dict[str, Any]] = Field(None, description="AI analysis results")
    
    # Timestamps
    started_at: datetime = Field(..., description="When the fight started")
    ended_at: datetime = Field(..., description="When the fight ended")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Recording(BaseModel):
    """Recording metadata model."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    fight_id: PyObjectId = Field(..., description="Associated fight ID")
    
    # File details
    file_path: str = Field(..., description="Path to recording file")
    file_size: int = Field(..., description="File size in bytes")
    duration: int = Field(..., description="Recording duration in seconds")
    format: str = Field(..., description="Recording format (audio/video)")
    
    # Recording settings
    is_video: bool = Field(default=False, description="Whether recording includes video")
    is_portrait: bool = Field(default=False, description="Whether video is in portrait mode")
    
    # Quality metrics
    audio_bitrate: Optional[int] = Field(None, description="Audio bitrate")
    video_bitrate: Optional[int] = Field(None, description="Video bitrate")
    resolution: Optional[str] = Field(None, description="Video resolution")
    
    # Status
    is_processed: bool = Field(default=False, description="Whether recording is processed")
    is_uploaded: bool = Field(default=False, description="Whether recording is uploaded")
    upload_url: Optional[str] = Field(None, description="Upload URL if uploaded")
    
    # Timestamps
    recorded_at: datetime = Field(..., description="When recording was made")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}