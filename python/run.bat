@echo off
REM OPS Center Analyzer Adapter - Windows Launcher

setlocal enabledelayedexpansion

REM Get script directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Add current directory to Python path
set PYTHONPATH=%SCRIPT_DIR%;%PYTHONPATH%

REM Set default config path
set CONFIG_FILE=%SCRIPT_DIR%\ops_center_adapter\etc\adapter.properties

REM Run Python module
python -m ops_center_adapter.main %*