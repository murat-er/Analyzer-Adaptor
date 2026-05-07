@echo off
REM OPS Center Analyzer Adapter - Windows Launcher

REM Get script directory (parent of python folder)
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Run Python with explicit path
python -m ops_center_adapter.main %*