"""
Recording manager for ArchFairFight.
"""

import os
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import structlog

from ..config import get_config
from ..database import RecordingOps
from ..database.models import Recording

logger = structlog.get_logger(__name__)


class RecordingManager:
    """Manages fight recordings."""
    
    def __init__(self):
        self.config = get_config()
        self.recording_ops = RecordingOps()
        self.active_recordings: Dict[str, Dict[str, Any]] = {}
    
    async def start_recording(self, fight_id: str, include_video: bool = False) -> bool:
        """Start recording a fight."""
        try:
            # Generate recording filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_extension = "mp4" if include_video else "mp3"
            filename = f"fight_{fight_id}_{timestamp}.{file_extension}"
            file_path = os.path.join(self.config.recordings_path, filename)
            
            # Ensure recordings directory exists
            os.makedirs(self.config.recordings_path, exist_ok=True)
            
            # Create recording record
            recording = Recording(
                fight_id=fight_id,
                file_path=file_path,
                file_size=0,  # Will be updated when recording stops
                duration=0,   # Will be updated when recording stops
                format="video" if include_video else "audio",
                is_video=include_video,
                recorded_at=datetime.utcnow()
            )
            
            recording_id = await self.recording_ops.create_recording(recording)
            if not recording_id:
                logger.error("Failed to create recording record", fight_id=fight_id)
                return False
            
            # Track active recording
            self.active_recordings[fight_id] = {
                'recording_id': recording_id,
                'file_path': file_path,
                'start_time': datetime.utcnow(),
                'include_video': include_video
            }
            
            logger.info("Recording started", fight_id=fight_id, recording_id=recording_id, 
                       file_path=file_path, include_video=include_video)
            return True
            
        except Exception as e:
            logger.error("Failed to start recording", fight_id=fight_id, error=str(e))
            return False
    
    async def stop_recording(self, fight_id: str) -> Optional[str]:
        """Stop recording a fight and return recording ID."""
        try:
            if fight_id not in self.active_recordings:
                logger.warning("No active recording found for fight", fight_id=fight_id)
                return None
            
            recording_info = self.active_recordings[fight_id]
            recording_id = recording_info['recording_id']
            file_path = recording_info['file_path']
            start_time = recording_info['start_time']
            
            # Calculate duration
            end_time = datetime.utcnow()
            duration = int((end_time - start_time).total_seconds())
            
            # Get file size (simulated for now, as actual recording would be handled by userbots)
            file_size = 0
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
            else:
                # Create a dummy file for demonstration
                # In a real implementation, this would be the actual recording file
                with open(file_path, 'w') as f:
                    f.write(f"Recording placeholder for fight {fight_id}")
                file_size = os.path.getsize(file_path)
            
            # Update recording record
            await self.recording_ops.update_recording_status(
                recording_id,
                file_size=file_size,
                duration=duration,
                is_processed=True
            )
            
            # Remove from active recordings
            del self.active_recordings[fight_id]
            
            logger.info("Recording stopped", fight_id=fight_id, recording_id=recording_id,
                       duration=duration, file_size=file_size)
            
            return recording_id
            
        except Exception as e:
            logger.error("Failed to stop recording", fight_id=fight_id, error=str(e))
            return None
    
    async def get_recording(self, recording_id: str) -> Optional[Recording]:
        """Get recording by ID."""
        try:
            return await self.recording_ops.get_recording(recording_id)
        except Exception as e:
            logger.error("Failed to get recording", recording_id=recording_id, error=str(e))
            return None
    
    async def get_recording_by_fight(self, fight_id: str) -> Optional[Recording]:
        """Get recording by fight ID."""
        try:
            return await self.recording_ops.get_recording_by_fight(fight_id)
        except Exception as e:
            logger.error("Failed to get recording by fight", fight_id=fight_id, error=str(e))
            return None
    
    async def process_recording(self, recording_id: str) -> bool:
        """Process a recording (e.g., compress, optimize)."""
        try:
            recording = await self.recording_ops.get_recording(recording_id)
            if not recording:
                logger.error("Recording not found", recording_id=recording_id)
                return False
            
            if recording.is_processed:
                logger.info("Recording already processed", recording_id=recording_id)
                return True
            
            # Simulate processing (in a real implementation, you might use ffmpeg)
            logger.info("Processing recording", recording_id=recording_id, file_path=recording.file_path)
            
            # Simulate processing time
            await asyncio.sleep(1)
            
            # Update recording status
            await self.recording_ops.update_recording_status(
                recording_id,
                is_processed=True
            )
            
            logger.info("Recording processed", recording_id=recording_id)
            return True
            
        except Exception as e:
            logger.error("Failed to process recording", recording_id=recording_id, error=str(e))
            return False
    
    async def upload_recording(self, recording_id: str, upload_url: str) -> bool:
        """Upload a recording to external storage."""
        try:
            recording = await self.recording_ops.get_recording(recording_id)
            if not recording:
                logger.error("Recording not found", recording_id=recording_id)
                return False
            
            if recording.is_uploaded:
                logger.info("Recording already uploaded", recording_id=recording_id)
                return True
            
            # Simulate upload (in a real implementation, you would upload to cloud storage)
            logger.info("Uploading recording", recording_id=recording_id, 
                       file_path=recording.file_path, upload_url=upload_url)
            
            # Simulate upload time
            await asyncio.sleep(2)
            
            # Update recording status
            await self.recording_ops.update_recording_status(
                recording_id,
                is_uploaded=True,
                upload_url=upload_url
            )
            
            logger.info("Recording uploaded", recording_id=recording_id, upload_url=upload_url)
            return True
            
        except Exception as e:
            logger.error("Failed to upload recording", recording_id=recording_id, error=str(e))
            return False
    
    async def delete_recording(self, recording_id: str) -> bool:
        """Delete a recording file from disk."""
        try:
            recording = await self.recording_ops.get_recording(recording_id)
            if not recording:
                logger.error("Recording not found", recording_id=recording_id)
                return False
            
            # Delete file from disk
            if os.path.exists(recording.file_path):
                os.remove(recording.file_path)
                logger.info("Recording file deleted", recording_id=recording_id, 
                           file_path=recording.file_path)
            
            return True
            
        except Exception as e:
            logger.error("Failed to delete recording", recording_id=recording_id, error=str(e))
            return False
    
    async def cleanup_old_recordings(self, days_old: int = 30) -> int:
        """Clean up old recording files."""
        try:
            # This is a simplified cleanup - in a real implementation,
            # you would query the database for old recordings and delete them
            
            if not os.path.exists(self.config.recordings_path):
                return 0
            
            import time
            current_time = time.time()
            cleanup_count = 0
            
            for filename in os.listdir(self.config.recordings_path):
                file_path = os.path.join(self.config.recordings_path, filename)
                
                if os.path.isfile(file_path):
                    file_age_days = (current_time - os.path.getmtime(file_path)) / (24 * 3600)
                    
                    if file_age_days > days_old:
                        try:
                            os.remove(file_path)
                            cleanup_count += 1
                            logger.info("Old recording file cleaned up", file_path=file_path)
                        except Exception as e:
                            logger.error("Failed to clean up recording file", 
                                       file_path=file_path, error=str(e))
            
            logger.info("Recording cleanup completed", cleaned_count=cleanup_count)
            return cleanup_count
            
        except Exception as e:
            logger.error("Failed to cleanup old recordings", error=str(e))
            return 0
    
    def is_recording_active(self, fight_id: str) -> bool:
        """Check if recording is active for a fight."""
        return fight_id in self.active_recordings
    
    def get_active_recording_count(self) -> int:
        """Get number of active recordings."""
        return len(self.active_recordings)
    
    def get_recording_info(self, fight_id: str) -> Optional[Dict[str, Any]]:
        """Get active recording info for a fight."""
        return self.active_recordings.get(fight_id)