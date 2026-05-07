#!/usr/bin/env python3
"""
Instance Manager for OPS Center Analyzer Adapter.
Manages instance_host and instance_names files.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config


logger = logging.getLogger(__name__)


@dataclass
class AgentInstance:
    """Represents an agent instance."""
    instance_id: str
    instance_name: str
    instance_host: str
    agent_url: str
    agent_type: str = 'storage'


class InstanceManager:
    """Manages agent instances for the adapter."""
    
    def __init__(self, config: Config):
        """Initialize instance manager.
        
        Args:
            config: Configuration object
        """
        self._config = config
        self._instances: List[AgentInstance] = []
        
        self._load_instances()
    
    def _load_instances(self):
        """Load instances from instance_host and instance_names files."""
        instance_dir = Path(self._config.instance_dir)
        
        if not instance_dir.exists():
            logger.warning(f"Instance directory not found: {self._config.instance_dir}")
            return
        
        # Load instance_names
        instance_names = self._load_instance_names(instance_dir / 'instance_names')
        
        # Load instance_host
        instance_hosts = self._load_instance_hosts(instance_dir / 'instance_host')
        
        # Combine into instances
        for name in instance_names:
            instance_id = name['instance_id']
            instance_host = instance_hosts.get(instance_id, {})
            
            self._instances.append(AgentInstance(
                instance_id=instance_id,
                instance_name=name['instance_name'],
                instance_host=instance_host.get('host', ''),
                agent_url=instance_host.get('url', ''),
                agent_type=instance_host.get('type', 'storage')
            ))
    
    def _load_instance_names(self, file_path: Path) -> List[Dict[str, str]]:
        """Load instance names from file.
        
        File format: instance_id=instance_name
        
        Args:
            file_path: Path to instance_names file
            
        Returns:
            List of instance dictionaries
        """
        instances = []
        
        if not file_path.exists():
            logger.warning(f"instance_names file not found: {file_path}")
            return instances
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            instances.append({
                                'instance_id': parts[0].strip(),
                                'instance_name': parts[1].strip()
                            })
        except Exception as e:
            logger.error(f"Failed to load instance_names: {e}")
        
        return instances
    
    def _load_instance_hosts(self, file_path: Path) -> Dict[str, Dict[str, str]]:
        """Load instance hosts from file.
        
        File format: instance_id=host|url|type
        
        Args:
            file_path: Path to instance_host file
            
        Returns:
            Dictionary of instance_id to host info
        """
        hosts = {}
        
        if not file_path.exists():
            logger.warning(f"instance_host file not found: {file_path}")
            return hosts
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            instance_id = parts[0].strip()
                            values = parts[1].split('|')
                            
                            hosts[instance_id] = {
                                'host': values[0] if len(values) > 0 else '',
                                'url': values[1] if len(values) > 1 else '',
                                'type': values[2] if len(values) > 2 else 'storage'
                            }
        except Exception as e:
            logger.error(f"Failed to load instance_host: {e}")
        
        return hosts
    
    def load_instances(self) -> List[Dict[str, Any]]:
        """Load all instances as dictionaries.
        
        Returns:
            List of instance dictionaries
        """
        return [
            {
                'instance_id': inst.instance_id,
                'instance_name': inst.instance_name,
                'instance_host': inst.instance_host,
                'agent_url': inst.agent_url,
                'agent_type': inst.agent_type
            }
            for inst in self._instances
        ]
    
    def save_instance(self, instance: AgentInstance):
        """Save instance to files.
        
        Args:
            instance: Instance to save
        """
        instance_dir = Path(self._config.instance_dir)
        instance_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to instance_names
        with open(instance_dir / 'instance_names', 'a') as f:
            f.write(f"{instance.instance_id}={instance.instance_name}\n")
        
        # Save to instance_host
        with open(instance_dir / 'instance_host', 'a') as f:
            f.write(f"{instance.instance_id}={instance.instance_host}|{instance.agent_url}|{instance.agent_type}\n")
    
    def get_instance(self, instance_id: str) -> Optional[AgentInstance]:
        """Get instance by ID.
        
        Args:
            instance_id: Instance ID
            
        Returns:
            Instance or None if not found
        """
        for inst in self._instances:
            if inst.instance_id == instance_id:
                return inst
        return None
    
    @property
    def instances(self) -> List[AgentInstance]:
        """Get all instances."""
        return self._instances
    
    @property
    def instance_count(self) -> int:
        """Get count of instances."""
        return len(self._instances)