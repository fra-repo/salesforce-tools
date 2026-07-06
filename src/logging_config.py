"""Logging configuration.

Centralized logging setup for the application.
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    enable_file: bool = True,
) -> logging.Logger:
    """Configure application logging.
    
    Args:
        log_dir: Directory for log files (default: ~/.salesforce-tools/logs)
        level: Logging level
        enable_file: If True, also log to file
    
    Returns:
        Configured root logger
    """
    if log_dir is None:
        log_dir = Path.home() / ".salesforce-tools" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Root logger config
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating)
    if enable_file:
        log_file = log_dir / "salesforce-tools.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
        file_format = logging.Formatter(
            '[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
    
    return root_logger
