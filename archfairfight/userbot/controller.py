"""
Userbot controller for voice chat operations.
"""

import asyncio
from typing import Optional, Dict, Any, List
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.exceptions import GroupCallNotFound, AlreadyJoinedError
import structlog

logger = structlog.get_logger(__name__)


class UserbotController:
    """Controls a single userbot for voice chat operations."""
    
    def __init__(self, session_name: str, api_id: int, api_hash: str):
        self.session_name = session_name
        self.client = Client(session_name, api_id=api_id, api_hash=api_hash)
        self.pytgcalls = PyTgCalls(self.client)
        
        # Fight monitoring data
        self.current_fight_id: Optional[str] = None
        self.monitored_participants: Dict[int, Dict[str, Any]] = {}
        self.is_recording = False
        self.group_call_id: Optional[str] = None
        
        # Setup event handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup PyTgCalls event handlers."""
        
        @self.pytgcalls.on_stream_end()
        async def on_stream_end(client: PyTgCalls, update: Update):
            """Handle stream end event."""
            logger.info("Stream ended", chat_id=update.chat_id)
        
        @self.pytgcalls.on_participants_change()
        async def on_participants_change(client: PyTgCalls, update: Update):
            """Handle participants change event."""
            chat_id = update.chat_id
            
            if self.current_fight_id:
                # Update participant metrics
                for participant in update.participants:
                    user_id = participant.user_id
                    
                    if user_id in self.monitored_participants:
                        # Update join/leave times
                        if participant.is_speaking:
                            if 'last_speak_start' not in self.monitored_participants[user_id]:
                                self.monitored_participants[user_id]['last_speak_start'] = asyncio.get_event_loop().time()
                        else:
                            if 'last_speak_start' in self.monitored_participants[user_id]:
                                speak_duration = asyncio.get_event_loop().time() - self.monitored_participants[user_id]['last_speak_start']
                                self.monitored_participants[user_id]['speak_time'] += speak_duration
                                del self.monitored_participants[user_id]['last_speak_start']
                        
                        # Update volume metrics
                        if hasattr(participant, 'volume'):
                            self.monitored_participants[user_id]['volume_sum'] += participant.volume
                            self.monitored_participants[user_id]['volume_samples'] += 1
                
                logger.debug("Participants updated", chat_id=chat_id, participants_count=len(update.participants))
    
    async def start(self) -> bool:
        """Start the userbot."""
        try:
            await self.client.start()
            await self.pytgcalls.start()
            
            user_info = await self.client.get_me()
            logger.info("Userbot started", user_id=user_info.id, username=user_info.username)
            return True
            
        except Exception as e:
            logger.error("Failed to start userbot", session=self.session_name, error=str(e))
            return False
    
    async def stop(self):
        """Stop the userbot."""
        try:
            if self.pytgcalls:
                await self.pytgcalls.stop()
            if self.client:
                await self.client.stop()
            
            logger.info("Userbot stopped", session=self.session_name)
            
        except Exception as e:
            logger.error("Error stopping userbot", session=self.session_name, error=str(e))
    
    async def join_voice_chat(self, chat_id: int) -> bool:
        """Join a voice chat."""
        try:
            # Create a silent audio stream to join the call
            stream = AudioPiped("audio.raw")  # Placeholder stream
            
            await self.pytgcalls.join_group_call(
                chat_id,
                stream,
                join_as=None  # Join as the userbot account
            )
            
            logger.info("Joined voice chat", chat_id=chat_id, session=self.session_name)
            return True
            
        except AlreadyJoinedError:
            logger.info("Already in voice chat", chat_id=chat_id, session=self.session_name)
            return True
        except GroupCallNotFound:
            logger.error("Group call not found", chat_id=chat_id, session=self.session_name)
            return False
        except Exception as e:
            logger.error("Failed to join voice chat", chat_id=chat_id, 
                        session=self.session_name, error=str(e))
            return False
    
    async def leave_voice_chat(self, chat_id: int) -> bool:
        """Leave a voice chat."""
        try:
            await self.pytgcalls.leave_group_call(chat_id)
            logger.info("Left voice chat", chat_id=chat_id, session=self.session_name)
            return True
            
        except GroupCallNotFound:
            logger.warning("Group call not found when leaving", chat_id=chat_id, session=self.session_name)
            return True  # Consider it successful if call doesn't exist
        except Exception as e:
            logger.error("Failed to leave voice chat", chat_id=chat_id, 
                        session=self.session_name, error=str(e))
            return False
    
    async def get_group_call_participants(self, chat_id: int) -> List[Dict[str, Any]]:
        """Get list of participants in a group call."""
        try:
            # Get group call info using raw Telegram API
            group_call = await self.client.invoke(
                {
                    "_": "phone.GetGroupCall",
                    "call": {
                        "_": "inputGroupCall",
                        "id": chat_id,  # This should be the actual call ID
                        "access_hash": 0  # This should be the actual access hash
                    },
                    "limit": 100
                }
            )
            
            participants = []
            if hasattr(group_call, 'participants'):
                for participant in group_call.participants:
                    participant_info = {
                        "user_id": participant.peer.user_id if hasattr(participant.peer, 'user_id') else None,
                        "muted": participant.muted if hasattr(participant, 'muted') else False,
                        "volume": participant.volume if hasattr(participant, 'volume') else 0,
                        "active_date": participant.active_date if hasattr(participant, 'active_date') else None,
                        "is_speaking": not participant.muted if hasattr(participant, 'muted') else False
                    }
                    participants.append(participant_info)
            
            return participants
            
        except Exception as e:
            logger.error("Failed to get group call participants", chat_id=chat_id, error=str(e))
            return []
    
    async def mute_participant(self, chat_id: int, user_id: int) -> bool:
        """Mute a participant in the group call."""
        try:
            await self.client.invoke(
                {
                    "_": "phone.EditGroupCallParticipant",
                    "call": {
                        "_": "inputGroupCall",
                        "id": chat_id,
                        "access_hash": 0
                    },
                    "participant": {
                        "_": "inputPeerUser",
                        "user_id": user_id,
                        "access_hash": 0
                    },
                    "muted": True
                }
            )
            
            logger.info("Participant muted", chat_id=chat_id, user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to mute participant", chat_id=chat_id, user_id=user_id, error=str(e))
            return False
    
    async def unmute_participant(self, chat_id: int, user_id: int) -> bool:
        """Unmute a participant in the group call."""
        try:
            await self.client.invoke(
                {
                    "_": "phone.EditGroupCallParticipant",
                    "call": {
                        "_": "inputGroupCall",
                        "id": chat_id,
                        "access_hash": 0
                    },
                    "participant": {
                        "_": "inputPeerUser",
                        "user_id": user_id,
                        "access_hash": 0
                    },
                    "muted": False
                }
            )
            
            logger.info("Participant unmuted", chat_id=chat_id, user_id=user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to unmute participant", chat_id=chat_id, user_id=user_id, error=str(e))
            return False
    
    async def change_group_call_title(self, chat_id: int, title: str) -> bool:
        """Change the group call title."""
        try:
            await self.client.invoke(
                {
                    "_": "phone.EditGroupCallTitle",
                    "call": {
                        "_": "inputGroupCall",
                        "id": chat_id,
                        "access_hash": 0
                    },
                    "title": title
                }
            )
            
            logger.info("Group call title changed", chat_id=chat_id, title=title)
            return True
            
        except Exception as e:
            logger.error("Failed to change group call title", chat_id=chat_id, error=str(e))
            return False
    
    async def start_recording(self, chat_id: int, video: bool = False, 
                            portrait: bool = False, title: str = "") -> bool:
        """Start recording the group call."""
        try:
            await self.client.invoke(
                {
                    "_": "phone.ToggleGroupCallRecord",
                    "call": {
                        "_": "inputGroupCall",
                        "id": chat_id,
                        "access_hash": 0
                    },
                    "start": True,
                    "video": video,
                    "title": title,
                    "video_portrait": portrait
                }
            )
            
            self.is_recording = True
            logger.info("Recording started", chat_id=chat_id, video=video)
            return True
            
        except Exception as e:
            logger.error("Failed to start recording", chat_id=chat_id, error=str(e))
            return False
    
    async def stop_recording(self, chat_id: int) -> bool:
        """Stop recording the group call."""
        try:
            await self.client.invoke(
                {
                    "_": "phone.ToggleGroupCallRecord",
                    "call": {
                        "_": "inputGroupCall",
                        "id": chat_id,
                        "access_hash": 0
                    },
                    "start": False
                }
            )
            
            self.is_recording = False
            logger.info("Recording stopped", chat_id=chat_id)
            return True
            
        except Exception as e:
            logger.error("Failed to stop recording", chat_id=chat_id, error=str(e))
            return False
    
    async def start_fight_monitoring(self, fight_id: str, participant1_id: int, participant2_id: int):
        """Start monitoring a fight."""
        self.current_fight_id = fight_id
        self.monitored_participants = {
            participant1_id: {
                "join_time": asyncio.get_event_loop().time(),
                "speak_time": 0.0,
                "volume_sum": 0.0,
                "volume_samples": 0
            },
            participant2_id: {
                "join_time": asyncio.get_event_loop().time(),
                "speak_time": 0.0,
                "volume_sum": 0.0,
                "volume_samples": 0
            }
        }
        
        logger.info("Fight monitoring started", fight_id=fight_id)
    
    async def stop_fight_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring fight and return metrics."""
        current_time = asyncio.get_event_loop().time()
        
        # Calculate final metrics
        for user_id, metrics in self.monitored_participants.items():
            # Calculate total join time
            if 'join_time' in metrics:
                metrics['total_join_time'] = current_time - metrics['join_time']
            
            # Calculate average volume
            if metrics['volume_samples'] > 0:
                metrics['average_volume'] = metrics['volume_sum'] / metrics['volume_samples']
            else:
                metrics['average_volume'] = 0.0
        
        metrics = self.monitored_participants.copy()
        
        # Reset monitoring state
        self.current_fight_id = None
        self.monitored_participants = {}
        
        logger.info("Fight monitoring stopped")
        return metrics
    
    def is_monitoring_fight(self) -> bool:
        """Check if currently monitoring a fight."""
        return self.current_fight_id is not None
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current fight metrics."""
        return self.monitored_participants.copy()