@echo off
REM OPS Center Analyzer Adapter - Windows Launcher

REM Get script directory  
for %%i in (%~dp0.) do set SCRIPT_DIR=%%~fi

REM Run Python directly
python "%SCRIPT_DIR%\ops_center_adapter\__main__.py" %*