#!/usr/bin/env python3
"""
Configuration module for OPS Center Analyzer Adapter.
Handles loading and parsing configuration properties.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import tomli


logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the adapter."""
    
    # Default paths - all under ops_center_adapter folder
    DEFAULT_BASE_DIR = './ops_center_adapter'
    DEFAULT_CONFIG_DIR = './ops_center_adapter/etc'
    DEFAULT_DEFINITION_DIR = './ops_center_adapter/definition/etl/built-in/default'
    DEFAULT_INSTANCE_DIR = './ops_center_adapter/agent_instance'
    DEFAULT_RESULT_DIR = './ops_center_adapter/result'
    DEFAULT_LOG_DIR = './ops_center_adapter/log'
    
    # Default values
    DEFAULT_COLLECTION_INTERVAL = 5  # minutes
    DEFAULT_INFLUXDB_URL = 'http://localhost:8086'
    DEFAULT_INFLUXDB_ORG = 'hitachi'
    DEFAULT_INFLUXDB_BUCKET = 'ops_center'
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to configuration file
        """
        self._config: Dict[str, Any] = {}
        self._config_path = config_path
        
        self._setup_directories()
        self._load_config()
    
    def _setup_directories(self):
        """Create required directories."""
        os.makedirs('./ops_center_adapter/etc', exist_ok=True)
        os.makedirs('./ops_center_adapter/agent_instance', exist_ok=True)
        os.makedirs('./ops_center_adapter/result', exist_ok=True)
        os.makedirs('./ops_center_adapter/log', exist_ok=True)
    
    def _load_config(self):
        """Load configuration from file and environment."""
        # Set defaults
        self._config = {
            'base_dir': self.DEFAULT_BASE_DIR,
            'definition_dir': self.DEFAULT_DEFINITION_DIR,
            'instance_dir': self.DEFAULT_INSTANCE_DIR,
            'result_dir': self.DEFAULT_RESULT_DIR,
            'collection_interval': self.DEFAULT_COLLECTION_INTERVAL,
            'influxdb_url': self.DEFAULT_INFLUXDB_URL,
            'influxdb_org': self.DEFAULT_INFLUXDB_ORG,
            'influxdb_bucket': self.DEFAULT_INFLUXDB_BUCKET,
            'influxdb_token': os.environ.get('INFLUXDB_TOKEN', ''),
        }
        
        # Load from file if exists
        if self._config_path and os.path.exists(self._config_path):
            self._load_from_file(self._config_path)
        
        # Override from environment
        self._load_from_env()
    
    def _load_from_file(self, config_path: str):
        """Load configuration from properties file.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            # Try loading as TOML first
            with open(config_path, 'rb') as f:
                file_config = tomli.load(f)
                self._merge_config(file_config)
        except Exception:
            # Fall back to properties file format
            self._load_properties_file(config_path)
    
    def _load_properties_file(self, config_path: str):
        """Load configuration from properties file.
        
        Args:
            config_path: Path to properties file
        """
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            self._config[key] = value
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # InfluxDB settings
        if influx_url := os.environ.get('INFLUXDB_URL'):
            self._config['influxdb_url'] = influx_url
        if influx_token := os.environ.get('INFLUXDB_TOKEN'):
            self._config['influxdb_token'] = influx_token
        if influx_org := os.environ.get('INFLUXDB_ORG'):
            self._config['influxdb_org'] = influx_org
        if influx_bucket := os.environ.get('INFLUXDB_BUCKET'):
            self._config['influxdb_bucket'] = influx_bucket
        
        # OPS Center settings
        if ops_url := os.environ.get('OPS_CENTER_URL'):
            self._config['ops_center_url'] = ops_url
        if ops_user := os.environ.get('OPS_CENTER_USER'):
            self._config['ops_center_user'] = ops_user
        if ops_password := os.environ.get('OPS_CENTER_PASSWORD'):
            self._config['ops_center_password'] = ops_password
        
        # Directories
        if base_dir := os.environ.get('ADAPTER_BASE_DIR'):
            self._config['base_dir'] = base_dir
        if definition_dir := os.environ.get('ADAPTER_DEFINITION_DIR'):
            self._config['definition_dir'] = definition_dir
        if instance_dir := os.environ.get('ADAPTER_INSTANCE_DIR'):
            self._config['instance_dir'] = instance_dir
        if result_dir := os.environ.get('ADAPTER_RESULT_DIR'):
            self._config['result_dir'] = result_dir
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration into existing config.
        
        Args:
            new_config: New configuration to merge
        """
        self._config.update(new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self._config.get(key, default)
    
    @property
    def base_dir(self) -> str:
        """Base directory for the adapter."""
        return self._config.get('base_dir', self.DEFAULT_BASE_DIR)
    
    @property
    def config_dir(self) -> str:
        """Directory containing config files."""
        return self._config.get('config_dir', self.DEFAULT_CONFIG_DIR)
    
    @property
    def definition_dir(self) -> str:
        """Directory containing definition JSON files."""
        return self._config.get('definition_dir', self.DEFAULT_DEFINITION_DIR)
    
    @property
    def instance_dir(self) -> str:
        """Directory containing instance files."""
        return self._config.get('instance_dir', self.DEFAULT_INSTANCE_DIR)
    
    @property
    def result_dir(self) -> str:
        """Directory for result files."""
        return self._config.get('result_dir', self.DEFAULT_RESULT_DIR)
    
    @property
    def log_dir(self) -> str:
        """Directory for log files."""
        return self._config.get('log_dir', self.DEFAULT_LOG_DIR)
    
    @property
    def collection_interval(self) -> int:
        """Collection interval in minutes."""
        return int(self._config.get('collection_interval', self.DEFAULT_COLLECTION_INTERVAL))
    
    @property
    def influxdb_url(self) -> str:
        """InfluxDB URL."""
        return self._config.get('influxdb_url', self.DEFAULT_INFLUXDB_URL)
    
    @property
    def influxdb_token(self) -> str:
        """InfluxDB authentication token."""
        return self._config.get('influxdb_token', '')
    
    @property
    def influxdb_org(self) -> str:
        """InfluxDB organization."""
        return self._config.get('influxdb_org', self.DEFAULT_INFLUXDB_ORG)
    
    @property
    def influxdb_bucket(self) -> str:
        """InfluxDB bucket."""
        return self._config.get('influxdb_bucket', self.DEFAULT_INFLUXDB_BUCKET)
    
    @property
    def ops_center_url(self) -> str:
        """OPS Center URL."""
        return self._config.get('ops_center_url', '')
    
    @property
    def ops_center_user(self) -> str:
        """OPS Center user."""
        return self._config.get('ops_center_user', '')
    
    @property
    def ops_center_password(self) -> str:
        """OPS Center password."""
        return self._config.get('ops_center_password', '')