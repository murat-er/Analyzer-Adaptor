#!/usr/bin/env python3
"""
ETL Engine for OPS Center Analyzer Adapter.
Handles the Extract-Transform-Load process.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from .config import Config
from .definition_reader import DefinitionReader, EtlDefinition
from .custom_logic_handler import CustomLogicHandler


logger = logging.getLogger(__name__)


class EtlEngine:
    """ETL engine for processing metrics."""
    
    def __init__(self, config: Config):
        """Initialize ETL engine.
        
        Args:
            config: Configuration object
        """
        self._config = config
        self._definition_reader = DefinitionReader(config.definition_dir)
        
        self._session = requests.Session()
        
        # Initialize custom logic handler
        self._custom_handler = CustomLogicHandler(config, self)
        
    def extract(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from OPS Center for an instance.
        
        Args:
            instance: Instance dictionary
            
        Returns:
            Extracted data dictionary
        """
        logger.info(f"Extracting data for instance: {instance.get('instance_name')}")
        
        instance_host = instance.get('instance_host', '')
        
        # Get all definitions
        results = {}
        
        for etl_key in self._definition_reader.list_definitions():
            try:
                definition = self._definition_reader.get_definition(etl_key)
                if definition:
                    # Check if custom_logic type
                    if definition.etl_type == "custom_logic":
                        # Use custom handler
                        data = self._custom_handler.process(
                            etl_key,
                            instance,
                            definition._definition
                        )
                    else:
                        data = self._extract_for_definition(
                            instance,
                            definition
                        )
                    results[etl_key] = data
                    logger.info(f"Extracted {len(data) if data else 0} records for {etl_key} -> {definition.load_target_measurement}")
            except Exception as e:
                logger.error(f"Failed to extract for {etl_key}: {e}")
                continue
        
        return results
    
    def _extract_for_definition(
        self,
        instance: Dict[str, Any],
        definition: EtlDefinition
    ) -> List[Dict[str, Any]]:
        """Extract data for a specific definition.
        
        Args:
            instance: Instance dictionary
            definition: ETL definition
            
        Returns:
            List of extracted records
        """
        records = []
        
        # Get time range
        time_range = self._get_time_range()
        
        # For each extract target
        for target in definition.extract_targets:
            try:
                # Call OPS Center API to extract data
                data = self._call_ops_center_api(
                    instance,
                    target.record_name,
                    target.extract_type,
                    target.fields,
                    time_range
                )
                records.extend(data)
            except Exception as e:
                logger.error(f"Failed to extract {target.record_name}: {e}")
                continue
        
        return records
    
    def _call_ops_center_api(
        self,
        instance: Dict[str, Any],
        record_name: str,
        extract_type: List[str],
        fields: List[str],
        time_range: tuple
    ) -> List[Dict[str, Any]]:
        """Call OPS Center API to extract data.
        
        Args:
            instance: Instance dictionary
            record_name: Record type name
            extract_type: Type of extraction (history, etc.)
            fields: Fields to extract
            time_range: (start_time, end_time) tuple
            
        Returns:
            Extracted records
        """
        instance_host = instance.get('instance_host', '')
        agent_url = instance.get('agent_url', '')
        
        if not agent_url:
            # Use OPS Center URL from config
            agent_url = self._config.ops_center_url
        
        # Build request - use TuningAgent endpoint (like Java version)
        # URL: http://host:24221/TuningAgent/v1/objects/{record}?agentType=RAID&pfmHostName={host}&agentInstanceName={id}&...
        base_url = agent_url.rstrip('/')
        if '/api/' in base_url:
            base_url = base_url.replace('/api/', '/TuningAgent/v1/')
        else:
            base_url = f"{base_url}/TuningAgent/v1"
        
        url = f"{base_url}/objects/{record_name}"
        
        # Fields separator is %1F (unit separator), NOT URL-encoded
        # Send as-is, don't let requests encode it
        fields_separator = '%1F'
        
        import base64
        
        # Build URL manually to avoid encoding issues
        # Format: http://host:24221/TuningAgent/v1/objects/{record}?agentType=RAID&pfmHostName={host}&agentInstanceName={id}&fields=...&startTime=...&endTime=...
        fields_value = fields_separator.join(fields)
        
        # Build query string manually - don't use params dict to avoid encoding
        query_parts = [
            f"agentType=RAID",
            f"pfmHostName={instance_host.upper()}",
            f"agentInstanceName={instance.get('instance_name', instance.get('id', ''))}",
            f"fields={fields_value}",
        ]
        
        # Add time range for historical data
        if extract_type and extract_type[0] == 'history':
            query_parts.append(f"startTime={time_range[0].strftime('%Y-%m-%dT%H:%MZ')}")
            query_parts.append(f"endTime={time_range[1].strftime('%Y-%m-%dT%H:%MZ')}")
        
        query_string = '&'.join(query_parts)
        full_url = f"{url}?{query_string}"
        
        # Debug log
        logger.debug(f"Request URL: {full_url}")
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Add authentication if configured
        if self._config.ops_center_user:
            credentials = f"{self._config.ops_center_user}:{self._config.ops_center_password}"
            headers['Authorization'] = f"Basic {base64.b64encode(credentials.encode()).decode()}"
        
        try:
            response = self._session.get(
                full_url,
                headers=headers,
                timeout=30
            )
            
            content_type = response.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                if response.status_code == 200:
                    try:
                        return response.json().get('data', [])
                    except Exception:
                        logger.warning(f"Empty response")
                        return []
            elif 'text/csv' in content_type or 'text/plain' in content_type:
                # Parse CSV response
                return self._parse_csv_response(response.text, fields)
            else:
                # Handle empty
                logger.debug("Empty response")
                return []
                
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return []
    
    def _parse_csv_response(self, csv_text: str, fields: List[str]) -> List[Dict[str, Any]]:
        """Parse CSV response from OPS Center API.
        
        Args:
            csv_text: CSV response text
            fields: Field names
            
        Returns:
            List of parsed records
        """
        records = []
        
        if not csv_text or csv_text.strip() == '':
            return records
        
        lines = csv_text.strip().split('\n')
        
        if len(lines) < 3:
            return records
        
        # Skip header (line 1) and type (line 2), start from data (line 3)
        data_lines = lines[2:]
        
        for line in data_lines:
            if not line.strip():
                continue
            
            values = line.split(',')
            if len(values) >= len(fields):
                record = {}
                for i, field in enumerate(fields):
                    if i < len(values):
                        val = values[i].strip()
                        # Remove quotes
                        if val.startswith('"') and val.endswith('"'):
                            val = val[1:-1]
                        # Try to convert
                        try:
                            if '.' in val:
                                record[field] = float(val)
                            else:
                                record[field] = int(val)
                        except ValueError:
                            record[field] = val
                if record:
                    records.append(record)
        
        return records
    
    def _get_time_range(self) -> tuple:
        """Get time range for extraction.
        
        Returns:
            (start_time, end_time) tuple
        """
        end_time = datetime.utcnow()
        
        # Use offset from config (minutes to go back)
        offset = getattr(self._config, 'collection_offset', 0)
        if offset is None:
            offset = 0
            
        start_time = end_time - timedelta(
            minutes=self._config.collection_interval + offset
        )
        
        return (start_time, end_time)
    
    def _get_auth(self) -> str:
        """Get basic authentication string.
        
        Returns:
            Base64 encoded auth string
        """
        import base64
        
        credentials = f"{self._config.ops_center_user}:{self._config.ops_center_password}"
        return base64.b64encode(credentials.encode()).decode()
    
    def transform(
        self,
        extracted_data: Dict[str, Any],
        instance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform extracted data using transformation definitions.
        
        Args:
            extracted_data: Raw extracted data
            instance: Instance information
            
        Returns:
            Transformed data points
        """
        transformed = []
        
        for etl_key, records in extracted_data.items():
            definition = self._definition_reader.get_definition(etl_key)
            if not definition:
                continue
            
            # Transform using SQL or direct mapping
            try:
                transformed_records = self._transform_records(
                    records,
                    definition,
                    instance
                )
                logger.info(f"Transformed {len(transformed_records)} records for {etl_key}")
                transformed.extend(transformed_records)
            except Exception as e:
                logger.error(f"Transform failed for {etl_key}: {e}")
                continue
        
        return transformed
    
    def _transform_records(
        self,
        records: List[Dict[str, Any]],
        definition: EtlDefinition,
        instance: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Transform records according to definition.
        
        Args:
            records: Raw records
            definition: ETL definition
            instance: Instance info
            
        Returns:
            Transformed records
        """
        transformed_records = []
        
        for record in records:
            try:
                # Build target record
                target_record = {
                    '_measurement': definition.load_target_measurement,
                    '_time': record.get(definition.transform.timestamp_col_name),
                    'tags': {},
                    'fields': {}
                }
                
                # Add instance tag
                target_record['tags']['instance_name'] = instance.get('instance_name', '')
                
                # Map tag keys
                for tag_mapping in definition.transform.tag_key_to_col_names:
                    tag_key = tag_mapping['tagKey']
                    col_name = tag_mapping['queryColName']
                    value = record.get(col_name)
                    if value is not None:
                        target_record['tags'][tag_key] = value
                
                # Map field keys
                for field_mapping in definition.transform.field_key_to_col_names:
                    field_key = field_mapping['fieldKey']
                    col_name = field_mapping['queryColName']
                    value = record.get(col_name)
                    if value is not None:
                        try:
                            target_record['fields'][field_key] = float(value)
                        except (ValueError, TypeError):
                            target_record['fields'][field_key] = value
                
                transformed_records.append(target_record)
                
            except Exception as e:
                logger.error(f"Record transform failed: {e}")
                continue
        
        return transformed_records
    
    def load(self, transformed_data: List[Dict[str, Any]]) -> int:
        """Load transformed data (returns count for verification).
        
        Args:
            transformed_data: Transformed data points
            
        Returns:
            Number of records
        """
        # This is handled by InfluxClient
        return len(transformed_data)