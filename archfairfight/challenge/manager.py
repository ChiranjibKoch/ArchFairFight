"""
Challenge manager for ArchFairFight.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import structlog

from ..config import get_config
from ..database import ChallengeOps, FightOps, UserOps
from ..database.models import Challenge, ChallengeStatus, Fight, FightType, FightResult
from ..userbot import UserbotManager
from ..recording import RecordingManager
from .state_machine import ChallengeStateMachine, ChallengeState

logger = structlog.get_logger(__name__)


class ChallengeManager:
    """Manages challenge lifecycle and fight execution."""
    
    def __init__(self):
        self.config = get_config()
        self.challenge_ops = ChallengeOps()
        self.fight_ops = FightOps()
        self.user_ops = UserOps()
        self.userbot_manager = UserbotManager()
        self.recording_manager = RecordingManager()
        
        # Active challenges tracking
        self._active_challenges: Dict[str, ChallengeStateMachine] = {}
        self._fight_tasks: Dict[str, asyncio.Task] = {}
    
    async def create_challenge(self, challenger_id: int, opponent_id: int, 
                             chat_id: int) -> Optional[str]:
        """Create a new challenge."""
        try:
            # Check if there's already an active challenge between these users
            existing_challenges = await self.challenge_ops.get_pending_challenges(opponent_id)
            for challenge in existing_challenges:
                if challenge.challenger_id == challenger_id:
                    logger.warning("Challenge already exists between users", 
                                 challenger_id=challenger_id, opponent_id=opponent_id)
                    return None
            
            # Create challenge
            challenge = Challenge(
                challenger_id=challenger_id,
                opponent_id=opponent_id,
                chat_id=chat_id,
                challenge_expires_at=datetime.utcnow() + timedelta(
                    seconds=self.config.challenge_timeout * 2  # Double timeout for acceptance
                )
            )
            
            challenge_id = await self.challenge_ops.create_challenge(challenge)
            if challenge_id:
                # Initialize state machine
                state_machine = ChallengeStateMachine(ChallengeState.CREATED)
                state_machine.transition_to(ChallengeState.SENT)
                self._active_challenges[challenge_id] = state_machine
                
                logger.info("Challenge created", challenge_id=challenge_id,
                           challenger_id=challenger_id, opponent_id=opponent_id)
            
            return challenge_id
            
        except Exception as e:
            logger.error("Failed to create challenge", error=str(e))
            return None
    
    async def start_fight(self, challenge_id: str) -> bool:
        """Start a fight from an accepted challenge."""
        try:
            challenge = await self.challenge_ops.get_challenge(challenge_id)
            if not challenge:
                logger.error("Challenge not found", challenge_id=challenge_id)
                return False
            
            # Update state machine
            if challenge_id in self._active_challenges:
                state_machine = self._active_challenges[challenge_id]
                if not state_machine.transition_to(ChallengeState.PARTICIPANTS_JOINING):
                    return False
            
            # Create fight record
            fight = Fight(
                challenge_id=challenge.id,
                participant1_id=challenge.challenger_id,
                participant2_id=challenge.opponent_id,
                fight_type=challenge.fight_type,
                duration=0,  # Will be updated when fight ends
                participant1_result=FightResult.WIN,  # Temporary, will be updated
                participant2_result=FightResult.LOSS,  # Temporary, will be updated
                group_call_id="",  # Will be set by userbot
                started_at=datetime.utcnow()
            )
            
            fight_id = await self.fight_ops.create_fight(fight)
            if not fight_id:
                logger.error("Failed to create fight record", challenge_id=challenge_id)
                return False
            
            # Start fight monitoring task
            task = asyncio.create_task(self._monitor_fight(challenge_id, fight_id))
            self._fight_tasks[challenge_id] = task
            
            logger.info("Fight started", challenge_id=challenge_id, fight_id=fight_id)
            return True
            
        except Exception as e:
            logger.error("Failed to start fight", error=str(e), challenge_id=challenge_id)
            return False
    
    async def _monitor_fight(self, challenge_id: str, fight_id: str):
        """Monitor a fight in progress."""
        try:
            challenge = await self.challenge_ops.get_challenge(challenge_id)
            if not challenge:
                return
            
            # Update state to active
            if challenge_id in self._active_challenges:
                state_machine = self._active_challenges[challenge_id]
                
                # Wait for participants to join (30 seconds)
                await asyncio.sleep(self.config.challenge_timeout)
                
                # Check if participants joined via userbots
                participants_joined = await self.userbot_manager.check_participants_joined(
                    challenge.challenger_id, challenge.opponent_id
                )
                
                if not participants_joined:
                    # No one joined, end fight as no-show
                    await self._end_fight_no_show(challenge_id, fight_id)
                    return
                
                # Transition to active fight
                state_machine.transition_to(ChallengeState.FIGHT_ACTIVE)
                
                # Start recording
                recording_started = await self.recording_manager.start_recording(
                    fight_id, challenge.fight_type == FightType.VOLUME
                )
                
                if recording_started:
                    logger.info("Recording started", fight_id=fight_id)
                
                # Monitor fight for maximum duration
                fight_duration = 0
                max_duration = self.config.max_fight_duration
                
                participant1_metrics = {"join_time": 0, "speak_time": 0, "volume_sum": 0.0}
                participant2_metrics = {"join_time": 0, "speak_time": 0, "volume_sum": 0.0}
                
                while fight_duration < max_duration:
                    await asyncio.sleep(self.config.monitoring_interval)
                    fight_duration += self.config.monitoring_interval
                    
                    # Get current metrics from userbots
                    current_metrics = await self.userbot_manager.get_fight_metrics(
                        challenge.challenger_id, challenge.opponent_id
                    )
                    
                    if current_metrics:
                        participant1_metrics = current_metrics.get('participant1', participant1_metrics)
                        participant2_metrics = current_metrics.get('participant2', participant2_metrics)
                        
                        # Update fight metrics in database
                        await self.fight_ops.update_fight_metrics(
                            fight_id, challenge.challenger_id, participant1_metrics
                        )
                        await self.fight_ops.update_fight_metrics(
                            fight_id, challenge.opponent_id, participant2_metrics
                        )
                    
                    # Check if both participants left
                    if not await self.userbot_manager.are_participants_active(
                        challenge.challenger_id, challenge.opponent_id
                    ):
                        logger.info("Both participants left, ending fight early", fight_id=fight_id)
                        break
                
                # End fight and determine winner
                await self._end_fight_with_results(
                    challenge_id, fight_id, fight_duration,
                    participant1_metrics, participant2_metrics, challenge.fight_type
                )
            
        except Exception as e:
            logger.error("Error monitoring fight", error=str(e), challenge_id=challenge_id)
            await self._end_fight_error(challenge_id, fight_id)
    
    async def _end_fight_no_show(self, challenge_id: str, fight_id: str):
        """End fight due to no participants joining."""
        try:
            # Update fight result
            await self.fight_ops.finish_fight(
                fight_id, None, FightResult.NO_SHOW, FightResult.NO_SHOW
            )
            
            # Update challenge status
            await self.challenge_ops.update_challenge_status(
                challenge_id, ChallengeStatus.COMPLETED
            )
            
            # Update state machine
            if challenge_id in self._active_challenges:
                self._active_challenges[challenge_id].transition_to(ChallengeState.FIGHT_FINISHED)
                del self._active_challenges[challenge_id]
            
            logger.info("Fight ended - no show", challenge_id=challenge_id, fight_id=fight_id)
            
        except Exception as e:
            logger.error("Error ending no-show fight", error=str(e))
    
    async def _end_fight_with_results(self, challenge_id: str, fight_id: str, 
                                    duration: int, participant1_metrics: Dict[str, Any],
                                    participant2_metrics: Dict[str, Any], fight_type: FightType):
        """End fight and determine winner based on metrics."""
        try:
            # Stop recording
            await self.recording_manager.stop_recording(fight_id)
            
            # Determine winner based on fight type
            winner_id = None
            participant1_result = FightResult.LOSS
            participant2_result = FightResult.WIN
            
            challenge = await self.challenge_ops.get_challenge(challenge_id)
            
            if fight_type == FightType.TIMING:
                # Winner is who stayed longer
                p1_time = participant1_metrics.get('join_time', 0)
                p2_time = participant2_metrics.get('join_time', 0)
                
                if p1_time > p2_time:
                    winner_id = challenge.challenger_id
                    participant1_result = FightResult.WIN
                    participant2_result = FightResult.LOSS
                elif p2_time > p1_time:
                    winner_id = challenge.opponent_id
                    participant1_result = FightResult.LOSS
                    participant2_result = FightResult.WIN
                else:
                    # Draw
                    participant1_result = FightResult.DRAW
                    participant2_result = FightResult.DRAW
                    
            elif fight_type == FightType.VOLUME:
                # Winner is who was more active (spoke more/louder)
                p1_activity = (participant1_metrics.get('speak_time', 0) * 
                             participant1_metrics.get('volume_sum', 0))
                p2_activity = (participant2_metrics.get('speak_time', 0) * 
                             participant2_metrics.get('volume_sum', 0))
                
                if p1_activity > p2_activity:
                    winner_id = challenge.challenger_id
                    participant1_result = FightResult.WIN
                    participant2_result = FightResult.LOSS
                elif p2_activity > p1_activity:
                    winner_id = challenge.opponent_id
                    participant1_result = FightResult.LOSS
                    participant2_result = FightResult.WIN
                else:
                    # Draw
                    participant1_result = FightResult.DRAW
                    participant2_result = FightResult.DRAW
            
            # Update fight result
            await self.fight_ops.finish_fight(
                fight_id, winner_id, participant1_result, participant2_result
            )
            
            # Update user statistics
            if participant1_result == FightResult.WIN:
                await self.user_ops.update_user_stats(challenge.challenger_id, wins=1, total_fights=1)
                await self.user_ops.update_user_stats(challenge.opponent_id, losses=1, total_fights=1)
            elif participant2_result == FightResult.WIN:
                await self.user_ops.update_user_stats(challenge.challenger_id, losses=1, total_fights=1)
                await self.user_ops.update_user_stats(challenge.opponent_id, wins=1, total_fights=1)
            else:
                await self.user_ops.update_user_stats(challenge.challenger_id, draws=1, total_fights=1)
                await self.user_ops.update_user_stats(challenge.opponent_id, draws=1, total_fights=1)
            
            # Update challenge status
            await self.challenge_ops.update_challenge_status(
                challenge_id, ChallengeStatus.COMPLETED
            )
            
            # Update state machine
            if challenge_id in self._active_challenges:
                self._active_challenges[challenge_id].transition_to(ChallengeState.FIGHT_FINISHED)
                del self._active_challenges[challenge_id]
            
            # Clean up userbot connections
            await self.userbot_manager.cleanup_fight(challenge.challenger_id, challenge.opponent_id)
            
            logger.info("Fight completed", challenge_id=challenge_id, fight_id=fight_id,
                       winner_id=winner_id, duration=duration)
            
        except Exception as e:
            logger.error("Error ending fight with results", error=str(e))
            await self._end_fight_error(challenge_id, fight_id)
    
    async def _end_fight_error(self, challenge_id: str, fight_id: str):
        """End fight due to error."""
        try:
            # Update fight result as cancelled
            await self.fight_ops.finish_fight(
                fight_id, None, FightResult.CANCELLED, FightResult.CANCELLED
            )
            
            # Update challenge status
            await self.challenge_ops.update_challenge_status(
                challenge_id, ChallengeStatus.CANCELLED
            )
            
            # Update state machine
            if challenge_id in self._active_challenges:
                self._active_challenges[challenge_id].transition_to(ChallengeState.CANCELLED)
                del self._active_challenges[challenge_id]
            
            # Stop recording if active
            await self.recording_manager.stop_recording(fight_id)
            
            logger.info("Fight cancelled due to error", challenge_id=challenge_id, fight_id=fight_id)
            
        except Exception as e:
            logger.error("Error cancelling fight", error=str(e))
    
    async def expire_old_challenges(self) -> int:
        """Expire old pending challenges."""
        try:
            expired_count = await self.challenge_ops.expire_old_challenges()
            
            # Clean up state machines for expired challenges
            expired_challenges = []
            for challenge_id, state_machine in self._active_challenges.items():
                if state_machine.get_time_in_state() > self.config.challenge_timeout * 3:
                    expired_challenges.append(challenge_id)
            
            for challenge_id in expired_challenges:
                self._active_challenges[challenge_id].transition_to(ChallengeState.EXPIRED)
                del self._active_challenges[challenge_id]
            
            return expired_count
            
        except Exception as e:
            logger.error("Error expiring challenges", error=str(e))
            return 0
    
    async def cancel_challenge(self, challenge_id: str) -> bool:
        """Cancel an active challenge."""
        try:
            # Cancel fight task if active
            if challenge_id in self._fight_tasks:
                task = self._fight_tasks[challenge_id]
                task.cancel()
                del self._fight_tasks[challenge_id]
            
            # Update challenge status
            await self.challenge_ops.update_challenge_status(
                challenge_id, ChallengeStatus.CANCELLED
            )
            
            # Update state machine
            if challenge_id in self._active_challenges:
                self._active_challenges[challenge_id].transition_to(ChallengeState.CANCELLED)
                del self._active_challenges[challenge_id]
            
            logger.info("Challenge cancelled", challenge_id=challenge_id)
            return True
            
        except Exception as e:
            logger.error("Error cancelling challenge", error=str(e))
            return False
    
    def get_active_challenges_count(self) -> int:
        """Get count of active challenges."""
        return len(self._active_challenges)
    
    def is_challenge_active(self, challenge_id: str) -> bool:
        """Check if challenge is active."""
        return challenge_id in self._active_challenges