"""
Challenge state machine for ArchFairFight.
"""

from enum import Enum
from typing import Dict, Set, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class ChallengeState(str, Enum):
    """Challenge state enumeration."""
    CREATED = "created"
    SENT = "sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    FIGHT_TYPE_SELECTED = "fight_type_selected"
    PARTICIPANTS_JOINING = "participants_joining"
    FIGHT_ACTIVE = "fight_active"
    FIGHT_FINISHED = "fight_finished"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ChallengeStateMachine:
    """State machine for managing challenge states."""
    
    # Define valid state transitions
    VALID_TRANSITIONS: Dict[ChallengeState, Set[ChallengeState]] = {
        ChallengeState.CREATED: {
            ChallengeState.SENT,
            ChallengeState.CANCELLED
        },
        ChallengeState.SENT: {
            ChallengeState.ACCEPTED,
            ChallengeState.DECLINED,
            ChallengeState.EXPIRED,
            ChallengeState.CANCELLED
        },
        ChallengeState.ACCEPTED: {
            ChallengeState.FIGHT_TYPE_SELECTED,
            ChallengeState.CANCELLED
        },
        ChallengeState.FIGHT_TYPE_SELECTED: {
            ChallengeState.PARTICIPANTS_JOINING,
            ChallengeState.CANCELLED
        },
        ChallengeState.PARTICIPANTS_JOINING: {
            ChallengeState.FIGHT_ACTIVE,
            ChallengeState.EXPIRED,
            ChallengeState.CANCELLED
        },
        ChallengeState.FIGHT_ACTIVE: {
            ChallengeState.FIGHT_FINISHED,
            ChallengeState.CANCELLED
        },
        ChallengeState.FIGHT_FINISHED: set(),  # Terminal state
        ChallengeState.EXPIRED: set(),         # Terminal state
        ChallengeState.DECLINED: set(),        # Terminal state
        ChallengeState.CANCELLED: set()        # Terminal state
    }
    
    def __init__(self, initial_state: ChallengeState = ChallengeState.CREATED):
        self.current_state = initial_state
        self.state_history: list[tuple[ChallengeState, datetime]] = [
            (initial_state, datetime.utcnow())
        ]
    
    def can_transition_to(self, new_state: ChallengeState) -> bool:
        """Check if transition to new state is valid."""
        return new_state in self.VALID_TRANSITIONS.get(self.current_state, set())
    
    def transition_to(self, new_state: ChallengeState) -> bool:
        """Transition to a new state."""
        if not self.can_transition_to(new_state):
            logger.warning(
                "Invalid state transition attempted",
                current_state=self.current_state,
                new_state=new_state
            )
            return False
        
        old_state = self.current_state
        self.current_state = new_state
        self.state_history.append((new_state, datetime.utcnow()))
        
        logger.info(
            "Challenge state transitioned",
            old_state=old_state,
            new_state=new_state
        )
        
        return True
    
    def is_terminal_state(self) -> bool:
        """Check if current state is terminal."""
        return len(self.VALID_TRANSITIONS.get(self.current_state, set())) == 0
    
    def is_active(self) -> bool:
        """Check if challenge is in an active state."""
        active_states = {
            ChallengeState.SENT,
            ChallengeState.ACCEPTED,
            ChallengeState.FIGHT_TYPE_SELECTED,
            ChallengeState.PARTICIPANTS_JOINING,
            ChallengeState.FIGHT_ACTIVE
        }
        return self.current_state in active_states
    
    def get_current_state(self) -> ChallengeState:
        """Get current state."""
        return self.current_state
    
    def get_state_history(self) -> list[tuple[ChallengeState, datetime]]:
        """Get state transition history."""
        return self.state_history.copy()
    
    def get_time_in_state(self) -> int:
        """Get time spent in current state in seconds."""
        if not self.state_history:
            return 0
        
        last_transition_time = self.state_history[-1][1]
        return int((datetime.utcnow() - last_transition_time).total_seconds())
    
    def get_total_duration(self) -> int:
        """Get total duration since challenge creation in seconds."""
        if not self.state_history:
            return 0
        
        creation_time = self.state_history[0][1]
        return int((datetime.utcnow() - creation_time).total_seconds())
    
    @classmethod
    def from_state_string(cls, state_string: str) -> 'ChallengeStateMachine':
        """Create state machine from state string."""
        try:
            state = ChallengeState(state_string)
            return cls(state)
        except ValueError:
            logger.error("Invalid state string", state_string=state_string)
            return cls()  # Default to CREATED state