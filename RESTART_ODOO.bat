@echo off
REM Restart Odoo Service
REM Must run as Administrator

echo.
echo =========================================================
echo  RESTARTING ODOO SERVICE
echo =========================================================
echo.

echo Stopping Odoo 17 service...
net stop "Odoo 17"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Could not stop Odoo service
    echo Please run this script as Administrator
    echo Right-click > Run as Administrator
    echo.
    pause
    exit /b 1
)

echo.
echo Waiting 5 seconds...
timeout /t 5 /nobreak

echo.
echo Starting Odoo 17 service...
net start "Odoo 17"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Could not start Odoo service
    echo Please check Windows Services
    echo.
    pause
    exit /b 1
)

echo.
echo =========================================================
echo  ODOO SERVICE RESTARTED SUCCESSFULLY!
echo =========================================================
echo.
echo Next steps:
echo  1. Open web browser
echo  2. Go to http://localhost:8069
echo  3. Login to Odoo
echo  4. Apps ^> MySDB MySQL Connector ^> Upgrade
echo.
pause

