#!/usr/bin/env python3
"""
Custom logic handler for OPS Center Analyzer Adapter.
Implements custom ETL logic that requires Java backend.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CustomLogicHandler:
    """Handler for custom ETL logic types."""
    
    def __init__(self, config, ops_client):
        self._config = config
        self._ops = ops_client
    
    def process(self, etl_key: str, instance: Dict[str, Any], definition: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process custom logic for given etl_key.
        
        Args:
            etl_key: ETL key (e.g., 'host_group_ldev', 'ldev_all_read_write_response')
            instance: Instance dictionary
            definition: Full definition dict
            
        Returns:
            List of processed records
        """
        handlers = {
            'host_group_ldev': self._process_host_group_ldev,
            'ldev_all_read_write_response': self._process_ldev_all,
            'pool_capacity_per_host_group': self._process_pool_capacity_per_host_group,
            'port': self._process_port,
            'pool_capacity': self._process_pool_capacity,
            'custom_num_of_ldevs_logging': self._process_custom_num_of_ldevs,
        }
        
        handler = handlers.get(etl_key)
        if handler:
            return handler(instance, definition)
        
        logger.warning(f"No custom handler for {etl_key}")
        return []
    
    def _process_host_group_ldev(self, instance: Dict, definition: Dict) -> List[Dict]:
        """Process host_group_ldev - storage_host_group measurement.
        
        Custom logic: JOIN PD_LHGC (host group), PI_LDS (ldev stats), PI_LDE (ldev extended), PD_LDC (ldev config)
        """
        try:
            # Get time range
            time_range = self._get_time_range()
            instance_id = instance.get('instance_id', '')
            
            # Extract base data
            # 1. Get PD_LHGC - Host Group to LDEV mapping
            host_ldev = self._ops._call_ops_center_api(
                
                record_name='PD_LHGC',
                extract_type='latest',
                fields=['DATETIME', 'HOST_GROUP_NAME', 'LDEV_NUMBER'],
                time_range=time_range
            )
            
            # 2. Get PI_LDS - LDEV statistics (history)
            ldev_stats = self._ops._call_ops_center_api(
                
                record_name='PI_LDS',
                extract_type='history',
                fields=['DATETIME', 'LDEV_NUMBER', 'READ_IO_RATE', 'WRITE_IO_RATE', 
                       'READ_RESPONSE_RATE', 'WRITE_RESPONSE_RATE', 'READ_XFER_RATE', 
                       'WRITE_XFER_RATE', 'READ_MBYTES', 'WRITE_MBYTES', 
                       'READ_IO_COUNT', 'WRITE_IO_COUNT', 'READ_HIT_IO_COUNT'],
                time_range=time_range
            )
            
            # 3. Get PI_LDE - LDEV extended stats
            ldev_ext = self._ops._call_ops_center_api(
                instance,
                
                record_name='PI_LDE',
                extract_type='history',
                fields=['DATETIME', 'LDEV_NUMBER', 'RANDOM_READ_IO_RATE', 'SEQUENTIAL_READ_IO_RATE',
                       'RANDOM_WRITE_IO_RATE', 'SEQUENTIAL_WRITE_IO_RATE'],
                time_range=time_range
            )
            
            # 4. Get PD_LDC - LDEV configuration
            ldev_conf = self._ops._call_ops_center_api(
                instance,
                
                record_name='PD_LDC',
                extract_type='latest',
                fields=['DATETIME', 'LDEV_NUMBER', 'NVM_NAMESPACE_ID'],
                time_range=time_range
            )
            
            # Build lookup for host groups
            host_to_ldevs = {}
            for rec in host_ldev:
                hg = rec.get('HOST_GROUP_NAME', '')
                ldev = rec.get('LDEV_NUMBER')
                if hg and ldev:
                    if hg not in host_to_ldevs:
                        host_to_ldevs[hg] = []
                    host_to_ldevs[hg].append(ldev)
            
            # Build lookup for LDEV configs
            ldev_to_nvm = {}
            for rec in ldev_conf:
                ldev = rec.get('LDEV_NUMBER')
                nvm = rec.get('NVM_NAMESPACE_ID')
                if ldev:
                    ldev_to_nvm[ldev] = nvm
            
            # Aggregate by host group and datetime
            result = {}
            for rec in ldev_stats:
                dt = rec.get('DATETIME', '')
                host_groups = []
                
                # Find associated host groups
                ldev_num = rec.get('LDEV_NUMBER')
                for hg, ldevs in host_to_ldevs.items():
                    if ldev_num in ldevs:
                        host_groups.append(hg)
                
                if not host_groups:
                    host_groups = ['unknown']
                
                key = (dt, tuple(sorted(host_groups)))
                if key not in result:
                    result[key] = {
                        '_measurement': 'storage_host_group',
                        'pfmHostName': instance.get('pfmHostName', ''),
                        'agentInstanceName': instance.get('instance_name', ''),
                        'DATETIME': dt,
                        '_tag_host_group_name': ', '.join(sorted(host_groups)),
                        'sum_of_read_io_per_sec': 0,
                        'sum_of_write_io_per_sec': 0,
                        'sum_of_total_io_per_sec': 0,
                        'sum_of_read_io_count': 0,
                        'sum_of_write_io_count': 0,
                        'sum_of_read_hit_io_count': 0,
                        'sum_of_read_transfer_mebibytes_per_sec': 0,
                        'sum_of_write_transfer_mebibytes_per_sec': 0,
                        'sum_of_read_transfer_mebibytes': 0,
                        'sum_of_write_transfer_mebibytes': 0,
                        'max_of_read_response_time_in_micro_sec': None,
                        'max_of_write_response_time_in_micro_sec': None,
                    }
                
                r = result[key]
                r['sum_of_read_io_per_sec'] += rec.get('READ_IO_RATE', 0)
                r['sum_of_write_io_per_sec'] += rec.get('WRITE_IO_RATE', 0)
                r['sum_of_total_io_per_sec'] += rec.get('READ_IO_RATE', 0) + rec.get('WRITE_IO_RATE', 0)
                r['sum_of_read_io_count'] += rec.get('READ_IO_COUNT', 0)
                r['sum_of_write_io_count'] += rec.get('WRITE_IO_COUNT', 0)
                r['sum_of_read_hit_io_count'] += rec.get('READ_HIT_IO_COUNT', 0)
                r['sum_of_read_transfer_mebibytes_per_sec'] += rec.get('READ_XFER_RATE', 0)
                r['sum_of_write_transfer_mebibytes_per_sec'] += rec.get('WRITE_XFER_RATE', 0)
                r['sum_of_read_transfer_mebibytes'] += rec.get('READ_MBYTES', 0)
                r['sum_of_write_transfer_mebibytes'] += rec.get('WRITE_MBYTES', 0)
                
                # Response times (get max)
                if rec.get('READ_IO_COUNT', 0) > 0:
                    rr = rec.get('READ_RESPONSE_RATE')
                    if rr and (r['max_of_read_response_time_in_micro_sec'] is None or rr > r['max_of_read_response_time_in_micro_sec']):
                        r['max_of_read_response_time_in_micro_sec'] = rr
                if rec.get('WRITE_IO_COUNT', 0) > 0:
                    wr = rec.get('WRITE_RESPONSE_RATE')
                    if wr and (r['max_of_write_response_time_in_micro_sec'] is None or wr > r['max_of_write_response_time_in_micro_sec']):
                        r['max_of_write_response_time_in_micro_sec'] = wr
            
            return list(result.values()) if result else []
            
        except Exception as e:
            logger.error(f"host_group_ldev failed: {e}")
            import traceback
            logger.error(f"Stack: {traceback.format_exc()}")
            return []
    
    def _process_ldev_all(self, instance: Dict, definition: Dict) -> List[Dict]:
        """Process ldev_all_read_write_response - storage_ldev measurement.
        
        Custom logic: Extended LDEV statistics with host group and NVM info
        """
        try:
            time_range = self._get_time_range()
            instance_id = instance.get('instance_id', '')
            
            # Extract data
            ldev_stats = self._ops._call_ops_center_api(
                
                record_name='PI_LDS',
                extract_type='history',
                fields=['DATETIME', 'LDEV_NUMBER', 'READ_RESPONSE_RATE', 'READ_IO_RATE',
                       'READ_XFER_RATE', 'READ_MBYTES', 'READ_IO_COUNT',
                       'WRITE_RESPONSE_RATE', 'WRITE_IO_RATE', 'WRITE_XFER_RATE',
                       'WRITE_MBYTES', 'WRITE_IO_COUNT'],
                time_range=time_range
            )
            
            ldev_ext = self._ops._call_ops_center_api(
                instance,
                
                record_name='PI_LDE',
                extract_type='history',
                fields=['DATETIME', 'LDEV_NUMBER', 'RANDOM_READ_IO_RATE', 'RANDOM_WRITE_IO_RATE'],
                time_range=time_range
            )
            
            host_ldev = self._ops._call_ops_center_api(
                
                record_name='PD_LHGC',
                extract_type='latest',
                fields=['DATETIME', 'HOST_GROUP_NAME', 'LDEV_NUMBER'],
                time_range=time_range
            )
            
            # Extended stats lookup
            ext_lookup = {}
            for rec in ldev_ext:
                key = (rec.get('DATETIME'), rec.get('LDEV_NUMBER'))
                ext_lookup[key] = rec
            
            # Host group lookup
            host_lookup = {}
            for rec in host_ldev:
                ldev = rec.get('LDEV_NUMBER')
                hg = rec.get('HOST_GROUP_NAME', '')
                if ldev and hg:
                    host_lookup[ldev] = hg
            
            # Build result
            results = []
            for rec in ldev_stats:
                ldev = rec.get('LDEV_NUMBER')
                dt = rec.get('DATETIME')
                
                result_rec = {
                    '_measurement': 'storage_ldev',
                    'pfmHostName': instance.get('pfmHostName', ''),
                    'agentInstanceName': instance.get('instance_name', ''),
                    'DATETIME': dt,
                    '_tag_ldev_number': ldev,
                    'read_response_time_in_micro_sec': rec.get('READ_RESPONSE_RATE') if rec.get('READ_IO_COUNT', 0) > 0 else None,
                    'read_io_per_sec': rec.get('READ_IO_RATE', 0),
                    'write_response_time_in_micro_sec': rec.get('WRITE_RESPONSE_RATE') if rec.get('WRITE_IO_COUNT', 0) > 0 else None,
                    'write_io_per_sec': rec.get('WRITE_IO_RATE', 0),
                }
                
                # Add host group tag
                if ldev in host_lookup:
                    result_rec['_tag_associated_host_groups'] = host_lookup[ldev]
                
                # Transfer per IO
                if rec.get('READ_IO_COUNT', 0) > 0:
                    mb = rec.get('READ_MBYTES', 0)
                    cnt = rec.get('READ_IO_COUNT', 1)
                    result_rec['read_transfer_mebibytes_per_io'] = mb / cnt if cnt else None
                
                if rec.get('WRITE_IO_COUNT', 0) > 0:
                    mb = rec.get('WRITE_MBYTES', 0)
                    cnt = rec.get('WRITE_IO_COUNT', 1)
                    result_rec['write_transfer_mebibytes_per_io'] = mb / cnt if cnt else None
                
                # Extended stats
                ext_key = (dt, ldev)
                if ext_key in ext_lookup:
                    ext = ext_lookup[ext_key]
                    r_rate = rec.get('READ_IO_RATE', 1)
                    w_rate = rec.get('WRITE_IO_RATE', 1)
                    if r_rate > 0:
                        result_rec['random_read_io_to_read_io_ratio'] = ext.get('RANDOM_READ_IO_RATE', 0) / r_rate
                    if w_rate > 0:
                        result_rec['random_write_io_to_write_io_ratio'] = ext.get('RANDOM_WRITE_IO_RATE', 0) / w_rate
                
                results.append(result_rec)
            
            return results
            
        except Exception as e:
            logger.error(f"ldev_all failed: {e}")
            import traceback
            logger.error(f"Stack: {traceback.format_exc()}")
            return []
    
    def _process_pool_capacity_per_host_group(self, instance: Dict, definition: Dict) -> List[Dict]:
        """Process pool_capacity_per_host_group - storage_pool_capacity_per_host_group measurement."""
        # Similar structure to host_group_ldev
        return []
    
    def _process_port(self, instance: Dict, definition: Dict) -> List[Dict]:
        """Process port - storage_port measurement."""
        return []
    
    def _process_pool_capacity(self, instance: Dict, definition: Dict) -> List[Dict]:
        """Process pool_capacity."""
        return []
    
    def _process_custom_num_of_ldevs(self, instance: Dict, definition: Dict) -> List[Dict]:
        """Process custom_num_of_ldevs_logging."""
        return []
    
    def _get_time_range(self) -> Dict[str, str]:
        """Get time range for extraction."""
        # Default: last 5 minutes
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=5)
        
        return {
            'start': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'end': end_time.strftime('%Y-%m-%dT%H:%M:%S')
        }
