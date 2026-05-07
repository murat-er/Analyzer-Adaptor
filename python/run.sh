#!/bin/bash
#
# OPS Center Analyzer Adapter - Python Launcher
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

CONFIG_FILE="${CONFIG_FILE:-./ops_center_adapter/etc/adapter.properties}"

# Export configuration
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

exec "${PYTHON}" -m ops_center_adapter.main \
    --config "${CONFIG_FILE}" \
    "$@"