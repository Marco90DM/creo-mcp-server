@echo off
setlocal enabledelayedexpansion

echo ========================================
echo CREO MCP SERVER - CLEAN INSTALLATION
echo ========================================
echo.

REM Trova Python
set PYTHON=
for %%P in (
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "python.exe"
) do (
    if exist %%P (
        set PYTHON=%%~P
        goto :found_python
    )
)

:found_python
if "%PYTHON%"=="" (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo Found Python: %PYTHON%
%PYTHON% --version
echo.

echo ========================================
echo INSTALLING DEPENDENCIES
echo ========================================
echo.

%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt

echo.
echo ========================================
echo VERIFICATION
echo ========================================
echo.

%PYTHON% -c "import mcp; print('OK mcp')"
%PYTHON% -c "import creopyson; print('OK creopyson')"
%PYTHON% -c "from mcp.server.fastmcp import FastMCP; print('OK FastMCP')"

echo.
echo ========================================
echo SUCCESS!
echo ========================================
echo.
echo Python: %PYTHON%
echo.

echo %PYTHON% > python_path.txt

pause
