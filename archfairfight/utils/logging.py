"""
Logging configuration for ArchFairFight.
"""

import sys
import logging
from pathlib import Path
import structlog
from structlog.typing import FilteringBoundLogger

from ..config import get_config


def setup_logging() -> FilteringBoundLogger:
    """Setup structured logging for the application."""
    config = get_config()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, config.log_level.upper(), logging.INFO),
    )
    
    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if config.log_to_file:
        # Add file handler
        file_handler = logging.FileHandler(logs_dir / "archfairfight.log")
        file_handler.setLevel(getattr(logging, config.log_level.upper(), logging.INFO))
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Add to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)
        
        # Add JSON formatter for file output
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Add console pretty printing
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger = structlog.get_logger("archfairfight")
    logger.info("Logging configured", level=config.log_level, to_file=config.log_to_file)
    
    return logger