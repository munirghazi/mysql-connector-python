@echo off
echo ========================================
echo MySDB Connector v2.0 - Quick Upgrade
echo ========================================
echo.

REM Get database name
set /p DBNAME="Enter your database name: "

if "%DBNAME%"=="" (
    echo Error: Database name is required!
    pause
    exit /b 1
)

echo.
echo Database: %DBNAME%
echo Module: odoo_mysql_connector
echo.
echo Starting upgrade...
echo.

cd "C:\Program Files\Odoo 17.0.20250906\server"

python odoo-bin -u odoo_mysql_connector -d %DBNAME% --stop-after-init

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Upgrade completed successfully!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Start Odoo service
    echo 2. Login and verify new features
    echo 3. Check MySDB Dashboard for new menus
    echo.
) else (
    echo.
    echo ========================================
    echo Upgrade failed! Check errors above.
    echo ========================================
    echo.
)

pause

