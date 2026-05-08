#!/usr/bin/env python3
"""
InfluxDB client for OPS Center Analyzer Adapter.
Handles writing data to InfluxDB.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# Try influxdb-client v3 first, fallback to influxdb v2
try:
    from influxdb_client import InfluxDBClient, Point, WriteOptions
    INFLUXDB_V3 = True
except ImportError:
    try:
        from influxdb import InfluxDBClient
        from influxdb.models import Point
        INFLUXDB_V3 = False
    except ImportError:
        # No library installed
        InfluxDBClient = None
        Point = None
        INFLUXDB_V3 = False

from .config import Config


logger = logging.getLogger(__name__)


class InfluxDBWriteResult:
    """Result of InfluxDB write operation."""
    def __init__(self):
        self._success: bool = True
        self._points_written: int = 0
        self._error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        """Whether write was successful."""
        return self._success
    
    @property
    def points_written(self) -> int:
        """Number of points written."""
        return self._points_written
    
    @property
    def error(self) -> Optional[str]:
        """Error message if failed."""
        return self._error
    
    def mark_failed(self, error: str):
        """Mark operation as failed."""
        self._success = False
        self._error = error
    
    def set_points_written(self, count: int):
        """Set number of points written."""
        self._points_written = count


class InfluxClient:
    """InfluxDB client for writing metrics."""
    
    def __init__(self, config: Config):
        """Initialize InfluxDB client.
        
        Args:
            config: Configuration object
        """
        self._config = config
        self._client: Optional[InfluxDBClient] = None
        self._write_api = None
        
        self._connect()
    
    def _connect(self):
        """Connect to InfluxDB."""
        try:
            self._client = InfluxDBClient(
                url=self._config.influxdb_url,
                token=self._config.influxdb_token,
                org=self._config.influxdb_org
            )
            
            # Use write_api with WriteOptions for better batching
            write_options = WriteOptions(
                batch_size=1000,
                flush_interval=5000,
                retry_interval=1000,
                max_retries=3
            )
            self._write_api = self._client.write_api(write_options)
            
            logger.info(f"Connected to InfluxDB at {self._config.influxdb_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise
    
    def create_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            buckets_api = self._client.buckets_api()
            
            # Check if bucket exists
            bucket = buckets_api.find_bucket_by_name(self._config.influxdb_bucket)
            
            if bucket is None:
                # Create bucket
                org = self._client.organizations_api().find_organizations(
                    org=self._config.influxdb_org
                )[0]
                
                buckets_api.create_bucket(
                    bucket_name=self._config.influxdb_bucket,
                    org_id=org.id,
                    retention_rules=None
                )
                
                logger.info(f"Created bucket: {self._config.influxdb_bucket}")
            
        except Exception as e:
            logger.error(f"Failed to create bucket: {e}")
            raise
    
    def write(self, data: List[Dict[str, Any]]) -> InfluxDBWriteResult:
        """Write data points to InfluxDB.
        
        Args:
            data: List of data points to write
            
        Returns:
            Write result
        """
        result = InfluxDBWriteResult()
        
        if not data:
            result.set_points_written(0)
            return result
        
        try:
            # Build points
            points = []
            for record in data:
                point = self._build_point(record)
                if point:
                    points.append(point)
            
            # Write points - direct HTTP write
            if points:
                # Use line protocol for synchronous write
                lines = "\n".join([p.to_line_protocol() for p in points])
                
                # Write via HTTP POST
                import urllib.request
                import urllib.parse
                
                url = f"{self._config.influxdb_url}/api/v2/write?bucket={self._config.influxdb_bucket}&org={self._config.influxdb_org}&precision=ns"
                
                request = urllib.request.Request(
                    url, 
                    data=lines.encode('utf-8'),
                    headers={
                        'Authorization': f'Token {self._config.influxdb_token}',
                        'Content-Type': 'text/plain'
                    },
                    method='POST'
                )
                
                try:
                    with urllib.request.urlopen(request) as response:
                        status = response.status
                        body = response.read().decode('utf-8') if response.status != 204 else ""
                        if status == 204:
                            result.set_points_written(len(points))
                            logger.info(f"Wrote {len(points)} points to InfluxDB (measurement: {points[0].to_line_protocol().split()[0]})")
                        else:
                            logger.warning(f"Write returned {status}: {body}")
                            result.set_points_written(len(points))
                except urllib.error.HTTPError as e:
                    logger.error(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
                    result.mark_failed(f"HTTP {e.code}")
            
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
            result.mark_failed(str(e))
        
        return result
    
    def _build_point(self, record: Dict[str, Any]) -> Optional[Point]:
        """Build InfluxDB point from record.
        
        Args:
            record: Data record
            
        Returns:
            InfluxDB Point or None
        """
        try:
            measurement = record.get('_measurement', 'storage')
            timestamp = record.get('_time', datetime.utcnow())
            
            # Create point
            point = Point(measurement).time(timestamp)
            
            # Add tags
            for key, value in record.get('tags', {}).items():
                if value is not None:
                    point.tag(key, str(value))
            
            # Add fields
            for key, value in record.get('fields', {}).items():
                if value is not None:
                    if isinstance(value, (int, float)):
                        point.field(key, value)
                    elif isinstance(value, bool):
                        point.field(key, value)
                    else:
                        point.field(key, str(value))
            
            return point
            
        except Exception as e:
            logger.error(f"Failed to build point: {e}")
            return None
    
    def query(self, query: str) -> List[Dict[str, Any]]:
        """Query data from InfluxDB.
        
        Args:
            query: InfluxQL query
            
        Returns:
            Query results
        """
        try:
            query_api = self._client.query_api()
            result = query_api.query_data_frame(query)
            
            if result.empty:
                return []
            
            return result.to_dict(orient='records')
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def close(self):
        """Close the InfluxDB connection."""
        if self._client:
            self._client.close()
            logger.info("Closed InfluxDB connection")