# OPS Center Analyzer Adapter - Python Implementation

## Directory Structure

```
python/
├── ops_center_adapter/
│   ├── __main__.py              # Main entry point
│   ├── __init__.py              # Package initialization
│   ├── config.py                 # Configuration
│   ├── definition_reader.py    # Definition JSON parser
│   ├── etl_engine.py           # ETL engine
│   ├── instance_manager.py     # Instance management
│   ├── influx_client.py        # InfluxDB client
│   ├── logging_config.py      # Logging
│   ├── raid_agent_reporter.py  # Result reporter
│   ├── etc/
│   │   └── adapter.properties # Configuration file
│   ├── definition/
│   │   └── etl/built-in/default/ # Definition files
│   ├── agent_instance/
│   │   ├── instance_host
│   │   └── instance_names
│   ├── result/
│   │   └── raid_agent
│   └── log/
│       └── adapter.log
├── run.sh
└── requirements.txt
```

## Usage

### Environment Variables

```bash
# InfluxDB
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_TOKEN=your-token
export INFLUXDB_ORG=hitachi
export INFLUXDB_BUCKET=ops_center

# OPS Center
export OPS_CENTER_URL=https://ops-center.example.com
export OPS_CENTER_USER=admin
export OPS_CENTER_PASSWORD=your-password
```

### Configuration File

Create `/var/opt/hitachi/analyzer_adapter/etc/adapter.properties`:

```properties
influxdb_url=http://localhost:8086
influxdb_token=your-token
influxdb_org=hitachi
influxdb_bucket=ops_center
ops_center_url=https://ops-center.example.com
ops_center_user=admin
ops_center_password=your-password
```

## Usage

### Run ETL Process

```bash
# Manual run
python -m ops_center_adapter.main --config /path/to/config.properties

# Scheduled run (cron mode)
python -m ops_center_adapter.main --scheduled

# Register database
python -m ops_center_adapter.main --register-db

# Debug mode
python -m ops_center_adapter.main --debug
```

### Instance Management

The adapter reads instances from:

- `/var/opt/hitachi/analyzer_adapter/agent_instance/instance_names`
- `/var/opt/hitachi/analyzer_adapter/agent_instance/instance_host`

Format for `instance_names`:
```
instance_id=instance_name
```

Format for `instance_host`:
```
instance_id=host|url|type
```

## Definition Files

Definition JSON files are located in:
`/var/opt/hitachi/analyzer_adapter/definition/etl/built-in/default/`

Each JSON file defines:
- What metrics to collect (extract targets)
- How to transform the data (SQL queries, field mappings)
- The InfluxDB measurement name

## Result Files

The adapter creates result files in:
`/var/opt/hitachi/analyzer_adapter/result/raid_agent`

The `raid_agent` file contains:
- Collection start/end times
- Number of instances
- Per-instance metrics collected

## Migration from Java

### Java to Python Usage Comparison

```bash
# Java (old)
java -jar analyzer-adapter.jar --config config.properties

# Python (new)
python -m ops_center_adapter.main --config config.properties
```

### Cron Job

Replace Java cron entries:
```cron
# Java
0-59/5 * * * * root sleep 30; /opt/hitachi/analyzer_adapter/run.sh --scheduled > /dev/null 2>&1

# Python
0-59/5 * * * * root sleep 30; /path/to/python/run.sh --scheduled > /dev/null 2>&1
```

## Dependencies

- Python 3.9+
- influxdb-client (InfluxDB 2.x)
- requests (HTTP client)
- tomli (config parsing, Python < 3.11)

## License

Copyright (C) 2024, Hitachi Vantara, Ltd.