#!/usr/bin/env python3
"""
Instance Manager for OPS Center Analyzer Adapter.
Manages instance_host and instance_names files.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

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
        """Initialize instance manager."""
        self._config = config
        self._instances: List[AgentInstance] = []
        self._setup_directories()
        
    def _setup_directories(self):
        """Create required directories if they don't exist."""
        # Get the base directory (parent of ops_center_adapter)
        base_dir = Path(__file__).parent.parent
        instance_dir = base_dir / 'agent_instance'
        instance_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Instance directory: {instance_dir}")
    
    def create_instances(self) -> List[AgentInstance]:
        """Create instances by querying OPS Center."""
        logger.info("Creating instances from OPS Center")
        instances_data = self._query_ops_center()
        
        self._instances = []
        for instance_data in instances_data:
            instance = AgentInstance(
                instance_id=instance_data.get('id', ''),
                instance_name=instance_data.get('name', ''),
                instance_host=instance_data.get('host', ''),
                agent_url=instance_data.get('url', ''),
                agent_type=instance_data.get('type', 'storage')
            )
            self._instances.append(instance)
        
        self._save_instance_files()
        logger.info(f"Created {len(self._instances)} instances")
        return self._instances
    
    def _query_ops_center(self) -> List[Dict[str, str]]:
        """Query OPS Center for available instances using native tools.
        
        Uses:
        - jpcinslist agtd: Get instance list
        - jpcconf host hostmode -display: Get host information
        """
        instances = []
        
        if not self._config.ops_center_url:
            logger.warning("OPS Center URL not configured, using defaults")
            return self._get_default_instances()
        
        # Try using native OPS Center tools first (like Java version does)
        try:
            instances = self._query_with_jpc_tools()
            if instances:
                return instances
        except Exception as e:
            logger.debug(f"jpc tools failed: {e}")
        
        # Fallback to API
        try:
            url = f"{self._config.ops_center_url}/api/v1/instances"
            headers = {'Content-Type': 'application/json'}
            
            if self._config.ops_center_user:
                import base64
                credentials = f"{self._config.ops_center_user}:{self._config.ops_center_password}"
                headers['Authorization'] = f"Basic {base64.b64encode(credentials.encode()).decode()}"
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                instances = data.get('instances', [])
            else:
                logger.warning(f"OPS Center returned {response.status_code}")
                instances = self._get_default_instances()
                
        except Exception as e:
            logger.error(f"Failed to query OPS Center: {e}")
            instances = self._get_default_instances()
        
        return instances
    
    def _query_with_jpc_tools(self) -> List[Dict[str, str]]:
        """Query using Hitachi jpc tools (jpcinslist, jpcconf).
        
        Returns:
            List of instance dictionaries
        """
        instances = []
        
        try:
            import subprocess
            
            # Get instance list: jpcinslist agtd
            result = subprocess.run(
                ['/opt/jp1pc/tools/jpcinslist', 'agtd'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"jpcinslist failed: {result.stderr}")
            
            # Parse instance names (format: instance_id=instance_name)
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    parts = line.split('=', 1)
                    instance_id = parts[0].strip()
                    instance_name = parts[1].strip() if len(parts) > 1 else instance_id
                    
                    # Get host info for this instance
                    host = self._get_instance_host()
                    
                    instances.append({
                        'id': instance_id,
                        'name': instance_name,
                        'host': host,
                        'url': f"https://{host}",
                        'type': 'storage'
                    })
            
            logger.info(f"Found {len(instances)} instances from jpcinslist")
            
        except FileNotFoundError:
            logger.debug("jpcinslist not found, trying API")
            raise
        except Exception as e:
            logger.debug(f"jpc tools error: {e}")
            raise
        
        return instances
    
    def _get_instance_host(self) -> str:
        """Get host information using jpcconf.
        
        Returns:
            Hostname
        """
        try:
            import subprocess
            
            # Get hostname: jpcconf host hostmode -display
            result = subprocess.run(
                ['/opt/jp1pc/tools/jpcconf', 'host', 'hostmode', '-display'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Parse hostname from output
                # Format: hostname: <value> or aliasname: <value>
                for line in result.stdout.strip().split('\n'):
                    line = line.strip().lower()
                    if line.startswith('hostname:') or line.startswith('aliasname:'):
                        return line.split(':', 1)[1].strip()
            
            # Fallback to socket hostname
            import socket
            return socket.gethostname()
            
        except Exception as e:
            logger.debug(f"jpcconf failed: {e}")
            import socket
            return socket.gethostname()
    
    def _get_default_instances(self) -> List[Dict[str, str]]:
        """Get default instances when OPS Center is not available."""
        instances = []
        
        instance_names_config = self._config.get('instance_names', '')
        
        if instance_names_config:
            for item in instance_names_config.split(','):
                parts = item.split('=')
                if len(parts) == 2:
                    instances.append({
                        'id': parts[0].strip(),
                        'name': parts[1].strip(),
                        'host': '',
                        'url': '',
                        'type': 'storage'
                    })
        
        if not instances:
            instances.append({
                'id': 'default',
                'name': 'default',
                'host': 'localhost',
                'url': self._config.ops_center_url or 'http://localhost:8080',
                'type': 'storage'
            })
        
        return instances
    
    def _save_instance_files(self):
        """Save instances to instance_host and instance_names files."""
        base_dir = Path(__file__).parent.parent
        instance_dir = base_dir / 'agent_instance'
        
        with open(instance_dir / 'instance_names', 'w') as f:
            for instance in self._instances:
                f.write(f"{instance.instance_id}={instance.instance_name}\n")
        
        with open(instance_dir / 'instance_host', 'w') as f:
            for instance in self._instances:
                f.write(f"{instance.instance_id}={instance.instance_host}|{instance.agent_url}|{instance.agent_type}\n")
        
        logger.info(f"Saved instance files to {instance_dir}")
    
    def load_instances(self) -> List[Dict[str, Any]]:
        """Load all instances as dictionaries."""
        if not self._instances:
            try:
                self._instances = self.create_instances()
            except Exception as e:
                logger.error(f"Failed to create instances: {e}")
        
        if not self._instances:
            self._load_from_files()
        
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
    
    def _load_from_files(self):
        """Load instances from existing files."""
        base_dir = Path(__file__).parent.parent
        instance_dir = base_dir / 'agent_instance'
        
        instance_names = self._load_instance_names(instance_dir / 'instance_names')
        instance_hosts = self._load_instance_hosts(instance_dir / 'instance_host')
        
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
        """Load instance names from file (format: instance_id=instance_name)."""
        instances = []
        
        if not file_path.exists():
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
        """Load instance hosts from file (format: instance_id=host|url|type)."""
        hosts = {}
        
        if not file_path.exists():
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
    
    def get_instance(self, instance_id: str) -> Optional[AgentInstance]:
        """Get instance by ID."""
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