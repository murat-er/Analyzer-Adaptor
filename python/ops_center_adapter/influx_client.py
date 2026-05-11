#!/usr/bin/env python3
"""
InfluxDB client for OPS Center Analyzer Adapter.
Uses direct HTTP API - no async, no dependencies.
"""

import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Simple Point class - no external dependency
class Point:
    """Simple Point for line protocol."""
    def __init__(self, measurement: str):
        self._measurement = measurement
        self._tags = {}
        self._fields = {}
    
    def tag(self, name: str, value: str):
        self._tags[name] = value
        return self
    
    def field(self, name: str, value):
        self._fields[name] = value
        return self
    
    def to_line_protocol(self) -> str:
        line = self._measurement
        if self._tags:
            line += ',' + ','.join([f'{k}={v}' for k,v in sorted(self._tags.items())])
        field_parts = []
        for k,v in sorted(self._fields.items()):
            if v is None:
                continue
            if isinstance(v, bool):
                field_parts.append(f"{k}={str(v).lower()}")
            elif isinstance(v, int):
                field_parts.append(f"{k}i={v}")
            elif isinstance(v, float):
                field_parts.append(f"{k}={v}")
            else:
                field_parts.append(f'{k}="{v}"')
        line += ' ' + ','.join(field_parts)
        line += f' {int(datetime.now().timestamp() * 1e9)}'
        return line


class InfluxDBWriteResult:
    def __init__(self):
        self._success = True
        self._points_written = 0
        self._error = None

    def set_points_written(self, count: int):
        self._points_written = count

    def points_written(self) -> int:
        return self._points_written

    def mark_failed(self, error: str):
        self._success = False
        self._error = error

    def is_failed(self) -> bool:
        return not self._success

    def error(self) -> Optional[str]:
        return self._error


class InfluxClient:
    """InfluxDB client using direct HTTP."""

    def __init__(self, config):
        self._config = config
        self._connected = False

    def connect(self):
        """Connect to InfluxDB."""
        self._connected = True
        logger.info(f"Connected to InfluxDB at {self._config.influxdb_url}")

    def write(self, data: List[Dict[str, Any]]) -> InfluxDBWriteResult:
        """Write data to InfluxDB."""
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

            if not points:
                result.set_points_written(0)
                return result

            # Write all points in one request
            lines = "\n".join([p.to_line_protocol() for p in points])
            url = f"{self._config.influxdb_url}/api/v2/write?bucket={self._config.influxdb_bucket}&org={self._config.influxdb_org}&precision=ns"
            
            req = urllib.request.Request(
                url,
                data=lines.encode('utf-8'),
                headers={
                    'Authorization': f'Token {self._config.influxdb_token}',
                    'Content-Type': 'text/plain'
                },
                method='POST'
            )

            try:
                with urllib.request.urlopen(req) as response:
                    if response.status != 204:
                        raise Exception(f"HTTP {response.status}")
            except urllib.error.HTTPError as e:
                raise Exception(f"HTTP error {e.code}: {e.reason}")

            result.set_points_written(len(points))
            logger.info(f"Wrote {len(points)} points to InfluxDB")

        except Exception as e:
            logger.error(f"Failed to write: {e}")
            import traceback
            logger.error(f"Stack: {traceback.format_exc()}")
            result.mark_failed(str(e))

        return result

    def _build_point(self, record: Dict[str, Any]) -> Optional[Point]:
        """Build point from record."""
        try:
            measurement = record.get('_measurement', record.get('measurement', 'unknown'))
            point = Point(measurement)
            
            # Add tags
            for key, value in record.items():
                if key.startswith('_tag_'):
                    point.tag(key[5:], str(value))
                elif key in ['pfmHostName', 'agentInstanceName', 'storageId']:
                    if value is not None:
                        point.tag(key, str(value))
            
            # Add fields
            for key, value in record.items():
                if key.startswith('_'):
                    continue
                if value is None:
                    continue
                if isinstance(value, bool):
                    point.field(key, value)
                elif isinstance(value, int):
                    point.field(key, value)
                elif isinstance(value, float):
                    point.field(key, value)
                elif isinstance(value, str):
                    try:
                        point.field(key, int(value))
                    except:
                        try:
                            point.field(key, float(value))
                        except:
                            point.field(key, value)
                else:
                    point.field(key, str(value))
            
            return point if point._fields else None
        except Exception as e:
            logger.error(f"Build point failed: {e}")
            return None

    def close(self):
        """Close connection."""
        self._connected = False
        logger.info("Closed InfluxDB connection")
