@echo off
REM OPS Center Analyzer Adapter - Windows Launcher
REM Usage: run.bat [options]

set SCRIPT_DIR=%~dp0
set PYTHON=python

REM Set default config path
set CONFIG_FILE=%SCRIPT_DIR%ops_center_adapter\etc\adapter.properties

REM Parse arguments
if "%~1"=="" goto help
if "%~1"=="--help" goto help
if "%~1"=="-h" goto help
if "%~1"=="--create-instances" goto run_create
if "%~1"=="--scheduled" goto run_scheduled
if "%~1"=="--register-db" goto run_register
goto run_custom

:run_create
%PYTHON% -m ops_center_adapter.main --config "%CONFIG_FILE%" --create-instances
goto end

:run_scheduled
%PYTHON% -m ops_center_adapter.main --config "%CONFIG_FILE%" --scheduled
goto end

:run_register
%PYTHON% -m ops_center_adapter.main --config "%CONFIG_FILE%" --register-db
goto end

:run_custom
%PYTHON% -m ops_center_adapter.main --config "%CONFIG_FILE%" %*
goto end

:help
echo.
echo OPS Center Analyzer Adapter
echo.
echo Usage:
echo   run.bat --create-instances   Create instance files
echo   run.bat --scheduled      Run ETL process
echo   run.bat --register-db    Register database
echo   run.bat --config ^<file^>  Use custom config
echo.
echo Options:
echo   --help, -h          Show this help
echo   --debug             Enable debug logging
echo.

:end