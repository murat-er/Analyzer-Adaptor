#!/usr/bin/env python3
"""
Raid Agent Reporter for OPS Center Analyzer Adapter.
Generates the raid_agent result file showing collected metrics.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import Config


logger = logging.getLogger(__name__)


class RaidAgentReporter:
    """Reporter for raid_agent result file."""
    
    def __init__(self, config: Config):
        """Initialize raid agent reporter.
        
        Args:
            config: Configuration object
        """
        self._config = config
        self._results: List[Dict[str, Any]] = []
        self._start_time = datetime.utcnow()
        
        self._result_dir = Path(config.result_dir)
        self._result_dir.mkdir(parents=True, exist_ok=True)
        
        self._result_file = self._result_dir / 'raid_agent'
    
    def add_result(
        self,
        instance: Dict[str, Any],
        transformed_data: List[Dict[str, Any]]
    ):
        """Add result for an instance.
        
        Args:
            instance: Instance dictionary
            transformed_data: Transformed data points
        """
        instance_name = instance.get('instance_name', 'unknown')
        
        # Group data by measurement
        measurements = {}
        for record in transformed_data:
            measurement = record.get('_measurement', 'unknown')
            if measurement not in measurements:
                measurements[measurement] = {
                    'measurement': measurement,
                    'record_count': 0,
                    'fields': set()
                }
            
            measurements[measurement]['record_count'] += 1
            
            # Collect field names
            for field in record.get('fields', {}).keys():
                measurements[measurement]['fields'].add(field)
        
        # Add to results
        self._results.append({
            'instance_name': instance_name,
            'collection_time': datetime.utcnow().isoformat(),
            'measurements': [
                {
                    'measurement': m['measurement'],
                    'count': m['record_count'],
                    'fields': sorted(list(m['fields']))
                }
                for m in measurements.values()
            ]
        })
    
    def save(self):
        """Save results to raid_agent file."""
        end_time = datetime.utcnow()
        
        # Build output
        output = {
            'collection_start': self._start_time.isoformat(),
            'collection_end': end_time.isoformat(),
            'duration_seconds': (end_time - self._start_time).total_seconds(),
            'instance_count': len(self._results),
            'instances': self._results
        }
        
        try:
            # Write to file
            with open(self._result_file, 'w') as f:
                json.dump(output, f, indent=2)
            
            logger.info(f"Saved raid_agent result to {self._result_file}")
            
        except Exception as e:
            logger.error(f"Failed to save raid_agent: {e}")
    
    def get_summary(self) -> str:
        """Get summary string for logging.
        
        Returns:
            Summary string
        """
        total_records = sum(
            sum(m['count'] for m in r['measurements'])
            for r in self._results
        )
        
        return (
            f"Collected {total_records} records from "
            f"{len(self._results)} instances"
        )
    
    @property
    def result_file(self) -> Path:
        """Get path to result file."""
        return self._result_file
    
    @property
    def results(self) -> List[Dict[str, Any]]:
        """Get all results."""
        return self._results