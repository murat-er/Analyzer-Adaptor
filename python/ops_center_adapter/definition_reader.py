#!/usr/bin/env python3
"""
Definition file reader for OPS Center Analyzer Adapter.
Reads and parses definition JSON files.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


@dataclass
class ExtractTarget:
    """Definition for data extraction."""
    record_name: str
    extract_type: List[str]
    fields: List[str]
    indexes: List[List[str]]
    

@dataclass
class TransformDefinition:
    """Definition for data transformation."""
    sql: str
    timestamp_col_name: str
    tag_key_to_col_names: List[Dict[str, str]]
    field_key_to_col_names: List[Dict[str, str]]


@dataclass
class EtlDefinition:
    """Complete ETL definition."""
    etl_type: str
    etl_key: str
    load_target_measurement: str
    extract_targets: List[ExtractTarget]
    transform: TransformDefinition


class DefinitionReader:
    """Reader for definition JSON files."""
    
    def __init__(self, definition_dir: str):
        """Initialize definition reader.
        
        Args:
            definition_dir: Directory containing definition JSON files
        """
        self._definition_dir = definition_dir
        self._definitions: Dict[str, EtlDefinition] = {}
        
        self._load_definitions()
    
    def _load_definitions(self):
        """Load all definition files from directory."""
        definition_path = Path(self._definition_dir)
        
        if not definition_path.exists():
            logger.warning(f"Definition directory not found: {self._definition_dir}")
            return
        
        # Load all JSON files
        for json_file in definition_path.glob('*.json'):
            try:
                definition = self._load_definition(json_file)
                if definition:
                    self._definitions[definition.etl_key] = definition
            except Exception as e:
                logger.error(f"Failed to load definition {json_file}: {e}")
    
    def _load_definition(self, json_file: Path) -> Optional[EtlDefinition]:
        """Load a single definition file.
        
        Args:
            json_file: Path to definition JSON file
            
        Returns:
            ETL definition or None if loading fails
        """
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Parse extract targets
            extract_targets = []
            for target in data.get('definition', {}).get('extractTargets', []):
                extract_targets.append(ExtractTarget(
                    record_name=target['recordName'],
                    extract_type=target['extractType'],
                    fields=target['fields'],
                    indexes=target.get('indexes', [])
                ))
            
            # Parse transform definition
            transform = data.get('definition', {}).get('transform', {})
            transform_def = TransformDefinition(
                sql=transform.get('sql', ''),
                timestamp_col_name=transform.get('timestampColName', 'DATETIME'),
                tag_key_to_col_names=transform.get('tagKeyToColNames', []),
                field_key_to_col_names=transform.get('fieldKeyToColNames', [])
            )
            
            # Get loadTargetMeasurement from different possible locations
            definition_data = data.get('definition', {})
            load_target = definition_data.get('loadTargetMeasurement', '')
            if not load_target:
                factory_param = definition_data.get('factoryParameter', {})
                load_target = factory_param.get('loadTargetMeasurement', '')
                # Check measurement field for custom logic
                if not load_target:
                    load_target = factory_param.get('measurement', '')
            
            return EtlDefinition(
                etl_type=data.get('type', 'simple'),
                etl_key=data.get('etlKey', json_file.stem),
                load_target_measurement=load_target,
                extract_targets=extract_targets,
                transform=transform_def
            )
            
        except Exception as e:
            logger.error(f"Error parsing definition {json_file}: {e}")
            return None
    
    def get_definition(self, etl_key: str) -> Optional[EtlDefinition]:
        """Get definition by key.
        
        Args:
            etl_key: ETL definition key
            
        Returns:
            ETL definition or None if not found
        """
        return self._definitions.get(etl_key)
    
    def list_definitions(self) -> List[str]:
        """List all available definition keys.
        
        Returns:
            List of definition keys
        """
        if not self._definitions:
            self._load_definitions()
        
        logger.info(f"Total definitions loaded: {len(self._definitions)}")
        for key in self._definitions.keys():
            logger.info(f"  - {key}")
        
        return list(self._definitions.keys())
    
    @property
    def definitions(self) -> Dict[str, EtlDefinition]:
        """Get all definitions."""
        return self._definitions