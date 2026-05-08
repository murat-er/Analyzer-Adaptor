#!/usr/bin/env python3
"""
OPS Center Analyzer Adapter - Python Implementation

This tool collects performance data from Hitachi OPS Center Analyzer
using definition JSON files and sends them to InfluxDB.

Usage:
    python3 -m ops_center_adapter.main [--config CONFIG] [--scheduled]
    python3 -m ops_center_adapter.main --register-db
    python3 -m ops_center_adapter.main --help
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ops_center_adapter.config import Config
from ops_center_adapter.etl_engine import EtlEngine
from ops_center_adapter.instance_manager import InstanceManager
from ops_center_adapter.influx_client import InfluxClient
from ops_center_adapter.logging_config import setup_logging
from ops_center_adapter.raid_agent_reporter import RaidAgentReporter


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='OPS Center Analyzer Adapter - Collects metrics and sends to InfluxDB'
    )
    parser.add_argument(
        '--config', '-c',
        default='./ops_center_adapter/etc/adapter.properties',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--scheduled',
        action='store_true',
        help='Run in scheduled/cron mode'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously until stopped (for daemon mode)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='Interval in seconds between runs (default: 300)'
    )
    parser.add_argument(
        '--register-db',
        action='store_true',
        help='Register database schema'
    )
    parser.add_argument(
        '--create-instances',
        action='store_true',
        help='Create instance_host and instance_names files'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    return parser.parse_args()


def run_etl(config: Config, scheduled: bool = False):
    """Run the ETL process."""
    logger = logging.getLogger(__name__)
    
    logger.info("Starting OPS Center Analyzer Adapter")
    
    # Initialize instance manager
    instance_mgr = InstanceManager(config)
    
    # Load instance information
    instances = instance_mgr.load_instances()
    logger.info(f"Loaded {len(instances)} instances")
    
    # Initialize ETL engine
    etl_engine = EtlEngine(config)
    
    # Initialize InfluxDB client
    influx_client = InfluxClient(config)
    
    # Initialize raid agent reporter
    raid_reporter = RaidAgentReporter(config)
    
    # Collect and process data for each instance
    for instance in instances:
        logger.info(f"Processing instance: {instance.get('instance_name')}")
        
        try:
            # Extract data from OPS Center
            extracted_data = etl_engine.extract(instance)
            
            # Transform data
            transformed_data = etl_engine.transform(extracted_data, instance)
            
            # Load to InfluxDB (grouped by measurement)
            measurement_groups: dict = {}
            for record in transformed_data:
                measurement = record.get('_measurement', 'storage')
                if measurement not in measurement_groups:
                    measurement_groups[measurement] = []
                measurement_groups[measurement].append(record)
            
            for measurement, data in measurement_groups.items():
                if data:
                    result = influx_client.write(data)
                    logger.info(f"Wrote {result.points_written} points to {measurement}")
            
            # Update raid agent result
            raid_reporter.add_result(instance, transformed_data)
            
        except Exception as e:
            logger.error(f"Error processing instance {instance.get('instance_name')}: {e}")
            continue
    
    # Finalize raid agent report
    raid_reporter.save()
    
    logger.info("ETL process completed")


def register_database(config: Config):
    """Register/create database schema."""
    logger = logging.getLogger(__name__)
    logger.info("Registering database schema")
    
    influx_client = InfluxClient(config)
    influx_client.create_bucket()
    
    logger.info("Database registration completed")


def create_instances(config: Config):
    """Create instance files."""
    logger = logging.getLogger(__name__)
    logger.info("Creating instance files")
    
    instance_mgr = InstanceManager(config)
    instances = instance_mgr.create_instances()
    
    logger.info(f"Created {len(instances)} instances in {config.instance_dir}")


def main():
    """Main entry point."""
    args = parse_args()
    
    setup_logging(debug=args.debug)
    logger = logging.getLogger(__name__)
    
    config = Config(args.config)
    
    if args.register_db:
        register_database(config)
        return 0
    
    if args.create_instances:
        create_instances(config)
        return 0
    
    if args.continuous:
        import time
        logger.info(f"Running in continuous mode (interval: {args.interval}s, Ctrl+C to stop)")
        try:
            while True:
                run_etl(config, scheduled=True)
                logger.info(f"Sleeping for {args.interval}s...")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        return 0
    
    if args.scheduled:
        run_etl(config, scheduled=True)
        return 0
    
    args.parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())