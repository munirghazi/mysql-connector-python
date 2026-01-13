@echo off
REM MySDB Connector - Module Cleanup Script
REM Removes backup files and prepares for production

echo ================================================
echo MySDB Connector - Module Cleanup
echo ================================================
echo.

cd /d "%~dp0"

echo [1/3] Checking for backup files...
if exist "models\mysdp_data_models.py" (
    echo   Found: models\mysdp_data_models.py
    set /p confirm="   Remove this backup file? (Y/N): "
    if /i "%confirm%"=="Y" (
        del /f "models\mysdp_data_models.py"
        echo   [OK] Removed backup file
    ) else (
        echo   [SKIP] Keeping backup file
    )
) else (
    echo   [OK] No backup files found
)

echo.
echo [2/3] Checking for temporary files...
if exist "*.pyc" (
    del /f /q "*.pyc"
    echo   [OK] Removed .pyc files
)
if exist "models\*.pyc" (
    del /f /q "models\*.pyc"
    echo   [OK] Removed models/*.pyc files
)
if exist "models\__pycache__" (
    rmdir /s /q "models\__pycache__"
    echo   [OK] Removed __pycache__ directory
)

echo.
echo [3/3] Validating module structure...
python FINAL_CONSISTENCY_CHECK.py
if errorlevel 1 (
    echo.
    echo [WARN] Some checks failed. Review output above.
) else (
    echo.
    echo [OK] All checks passed!
)

echo.
echo ================================================
echo Cleanup Complete!
echo ================================================
echo.
echo Next Steps:
echo 1. Run CLEANUP_MENUS.bat to clean database
echo 2. Restart Odoo service
echo 3. Upgrade module from Odoo Apps menu
echo.
pause

