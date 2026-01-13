@echo off
echo ========================================
echo MySDB Menu Cleanup Tool
echo ========================================
echo.

set /p DBNAME="Enter your database name: "

if "%DBNAME%"=="" (
    echo Error: Database name required!
    pause
    exit /b 1
)

echo.
echo Database: %DBNAME%
echo.
set /p CONFIRM="Continue? (Y/N): "

if /i not "%CONFIRM%"=="Y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo Creating SQL script...

echo DELETE FROM ir_ui_menu WHERE name = 'MySDB Dashboard' AND id NOT IN (SELECT res_id FROM ir_model_data WHERE module = 'odoo_mysql_connector' AND model = 'ir.ui.menu' AND name = 'menu_mysdb_dashboard_root'); > "%TEMP%\cleanup.sql"
echo SELECT COUNT(*) as "Remaining MySDB Dashboards" FROM ir_ui_menu WHERE name = 'MySDB Dashboard'; >> "%TEMP%\cleanup.sql"

echo.
echo Executing cleanup...
echo.

psql -U odoo -d %DBNAME% -f "%TEMP%\cleanup.sql"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS! Cleanup completed!
    echo ========================================
    echo.
    echo Next steps:
    echo 1. Start Odoo
    echo 2. Clear browser cache (Ctrl+Shift+Delete)
    echo 3. Login and verify
    echo.
    echo You should now see only ONE MySDB Dashboard with Tools
    echo.
) else (
    echo.
    echo ========================================
    echo ERROR: Cleanup failed
    echo ========================================
    echo.
    echo Please check:
    echo 1. Database name is correct
    echo 2. PostgreSQL is accessible
    echo 3. Odoo is stopped
    echo.
)

del "%TEMP%\cleanup.sql" 2>nul
pause

