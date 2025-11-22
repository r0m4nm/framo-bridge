import logging
import bpy
import os
from pathlib import Path
import tempfile

# Module-level logger instance
_logger = None

def get_addon_log_path():
    """Get path to logs/framo.log relative to this addon"""
    # Use the directory where this file is located to find the addon root
    this_file = Path(__file__)
    addon_root = this_file.parent.parent  # utils/ -> addon root
    log_dir = addon_root / "logs"

    # Ensure directory exists
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # Fallback to temp dir if permission denied
        log_dir = Path(tempfile.gettempdir()) / "framo_bridge_logs"
        log_dir.mkdir(parents=True, exist_ok=True)

    return log_dir / "framo.log"

def setup_logging():
    """Configure structured logging for the addon with immediate flush"""
    global _logger

    if _logger is not None:
        return _logger

    log_file = get_addon_log_path()

    # Create a custom handler that flushes immediately
    class FlushingFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()  # Force flush after every log entry

    # Clear any existing handlers on the logger
    logger = logging.getLogger('framo_bridge')
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)  # Set to DEBUG for crash debugging

    # File handler with immediate flush
    file_handler = FlushingFileHandler(str(log_file), mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    # Console handler (optional, may not show if Blender crashes)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _logger = logger
    return logger

def get_logger():
    """Get the addon logger, initializing if needed"""
    global _logger
    if _logger is None:
        return setup_logging()
    return _logger

