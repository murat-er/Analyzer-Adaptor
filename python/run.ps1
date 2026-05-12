# OPS Center Analyzer Adapter - Windows PowerShell Launcher
# Usage: .\run.ps1 [options]

param(
    [switch]$CreateInstances,
    [switch]$Scheduled,
    [switch]$RegisterDb,
    [switch]$Debug,
    [string]$Config = "./ops_center_adapter/etc/adapter.properties"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "python"

# Build arguments
$Args = @("--config", "$ScriptDir\$Config")

if ($CreateInstances) { $Args += "--create-instances" }
if ($Scheduled) { $Args += "--scheduled" }
if ($RegisterDb) { $Args += "--register-db" }
if ($Debug) { $Args += "--debug" }

# Run
& $Python -m ops_center_adapter.main @Args