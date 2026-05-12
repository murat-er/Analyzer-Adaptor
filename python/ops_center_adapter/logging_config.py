#!/usr/bin/env python3
"""
Logging configuration for OPS Center Analyzer Adapter.
"""

import logging
import sys
from pathlib import Path


def setup_logging(debug: bool = False):
    """Setup logging configuration.
    
    Args:
        debug: Enable debug logging
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Set specific log levels for libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('influxdb_client').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def get_log_file_path() -> Path:
    """Get path to log file."""
    base_dir = Path(__file__).parent.parent
    log_dir = base_dir / 'log'
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / 'adapter.log'


def configure_file_handler():
    """Configure file handler for logging."""
    log_file = get_log_file_path()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    
    logging.getLogger().addHandler(file_handler)