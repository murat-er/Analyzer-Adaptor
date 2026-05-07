#!/bin/bash
#
# OPS Center Analyzer Adapter - Python Launcher
# Wrapper script to run the Python adapter
#
# Copyright (C) 2024, Hitachi Vantara, Ltd.
#

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_DIR="${SCRIPT_DIR}/python"

# Python executable
PYTHON="${PYTHON:-python3}"

# Configuration
CONFIG_FILE="${CONFIG_FILE:-/var/opt/hitachi/analyzer_adapter/etc/adapter.properties}"

# Check for scheduled mode
SCHEDULED_MODE=""
if [[ "$1" == "--scheduled" ]]; then
    SCHEDULED_MODE="--scheduled"
fi

# Export InfluxDB configuration from environment
if [[ -f "${CONFIG_FILE}" ]]; then
    source "${CONFIG_FILE}"
    
    export INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
    export INFLUXDB_TOKEN="${INFLUXDB_TOKEN}"
    export INFLUXDB_ORG="${INFLUXDB_ORG:-hitachi}"
    export INFLUXDB_BUCKET="${INFLUXDB_BUCKET:-ops_center}"
    
    export OPS_CENTER_URL="${OPS_CENTER_URL}"
    export OPS_CENTER_USER="${OPS_CENTER_USER}"
    export OPS_CENTER_PASSWORD="${OPS_CENTER_PASSWORD}"
fi

# Run the adapter
exec "${PYTHON}" -m ops_center_adapter.main \
    --config "${CONFIG_FILE}" \
    ${SCHEDULED_MODE} \
    "$@"