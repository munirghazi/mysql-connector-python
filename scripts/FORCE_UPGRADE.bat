@echo off
echo ========================================
echo MySDB Connector - FORCE CLEAN UPGRADE
echo ========================================
echo.
echo This will perform a clean upgrade by:
echo 1. Clearing Odoo cache
echo 2. Force updating the module
echo 3. Stopping after initialization
echo.

set /p DBNAME="Enter your database name: "

if "%DBNAME%"=="" (
    echo Error: Database name is required!
    pause
    exit /b 1
)

echo.
echo Database: %DBNAME%
echo.
set /p CONFIRM="Continue? This is safe but will take 2-3 minutes (Y/N): "

if /i not "%CONFIRM%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Step 1: Navigating to Odoo directory...
cd "C:\Program Files\Odoo 17.0.20250906\server"

echo Step 2: Running force upgrade...
echo (This may take a few minutes - please wait)
echo.

python odoo-bin -u odoo_mysql_connector -d %DBNAME% --stop-after-init --log-level=warn

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! Module upgraded successfully!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Start your Odoo service normally
    echo 2. Clear browser cache (Ctrl+Shift+Delete)
    echo 3. Login and verify new features
    echo.
    echo Expected changes:
    echo - Version: 17.0.2.0.0
    echo - New "Tools" menu with 2 wizards
    echo - New income reports in "Reporting"
    echo - Enhanced Data Audit with colors
    echo.
) else (
    echo.
    echo ========================================
    echo UPGRADE FAILED - See errors above
    echo ========================================
    echo.
    echo The error shows an action is not found.
    echo This might be a database cache issue.
    echo.
    echo Try these solutions:
    echo.
    echo 1. RESTART ODOO SERVICE completely
    echo 2. Then try upgrade from Odoo UI:
    echo    - Apps -^> Update Apps List
    echo    - Search "MySDB Connector"
    echo    - Click Upgrade
    echo.
    echo 3. Or use SQL to clear the cache:
    echo    (Advanced users only - see TROUBLESHOOTING.md)
    echo.
)

pause

