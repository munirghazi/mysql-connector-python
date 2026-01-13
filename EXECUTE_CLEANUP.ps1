# MySDB Connector - Automated Duplicate Menu Cleanup
# This script will clean up duplicate MySDB Dashboard menus

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MySDB Duplicate Menu Cleanup Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get database name
$dbname = Read-Host "Enter your database name"

if ([string]::IsNullOrWhiteSpace($dbname)) {
    Write-Host "Error: Database name is required!" -ForegroundColor Red
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host ""
Write-Host "Database: $dbname" -ForegroundColor Yellow
Write-Host ""
Write-Host "This will:" -ForegroundColor White
Write-Host "  1. Remove duplicate MySDB Dashboard menus" -ForegroundColor White
Write-Host "  2. Keep only the official one with Tools" -ForegroundColor White
Write-Host "  3. Clean up orphaned submenus" -ForegroundColor White
Write-Host ""

# Confirm
$confirm = Read-Host "Continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 0
}

Write-Host ""
Write-Host "Step 1: Checking if Odoo is running..." -ForegroundColor Cyan

$odooProcess = Get-Process | Where-Object {$_.ProcessName -like "*odoo*" -or $_.ProcessName -like "*python*"}
if ($odooProcess) {
    Write-Host ""
    Write-Host "WARNING: Odoo appears to be running!" -ForegroundColor Red
    Write-Host "Please STOP Odoo before running this cleanup." -ForegroundColor Red
    Write-Host ""
    Write-Host "Detected processes:" -ForegroundColor Yellow
    $odooProcess | ForEach-Object { Write-Host "  - $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Yellow }
    Write-Host ""
    $forceRun = Read-Host "Stop Odoo is STRONGLY recommended. Continue anyway? (yes/no)"
    if ($forceRun -ne "yes") {
        Write-Host "Cancelled. Please stop Odoo and run this script again." -ForegroundColor Yellow
        Write-Host "Press any key to exit..."
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        exit 0
    }
}

Write-Host ""
Write-Host "Step 2: Creating SQL cleanup script..." -ForegroundColor Cyan

$sqlScript = @"
-- Show current MySDB menus
\echo 'Current MySDB Dashboard menus:'
SELECT id, name, complete_name FROM ir_ui_menu WHERE name = 'MySDB Dashboard';

-- Remove duplicates
\echo ''
\echo 'Removing duplicate menus...'
DELETE FROM ir_ui_menu 
WHERE name = 'MySDB Dashboard' 
AND id NOT IN (
    SELECT res_id FROM ir_model_data 
    WHERE module = 'odoo_mysql_connector' 
    AND model = 'ir.ui.menu' 
    AND name = 'menu_mysdb_dashboard_root'
);

-- Verify
\echo ''
\echo 'Verification (should show 1):'
SELECT COUNT(*) as "MySDB Dashboards Remaining" FROM ir_ui_menu WHERE name = 'MySDB Dashboard';

\echo ''
\echo 'Cleanup complete!'
"@

$tempSqlFile = "$env:TEMP\mysdb_cleanup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
$sqlScript | Out-File -FilePath $tempSqlFile -Encoding UTF8

Write-Host "SQL script created: $tempSqlFile" -ForegroundColor Green
Write-Host ""
Write-Host "Step 3: Executing SQL cleanup..." -ForegroundColor Cyan
Write-Host ""

# Execute SQL
try {
    $psqlPath = "psql"
    
    # Try to execute
    Write-Host "Connecting to database..." -ForegroundColor Yellow
    & $psqlPath -U odoo -d $dbname -f $tempSqlFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "SUCCESS! Cleanup completed!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "1. Start Odoo service" -ForegroundColor White
        Write-Host "2. Clear browser cache (Ctrl+Shift+Delete)" -ForegroundColor White
        Write-Host "3. Login to Odoo" -ForegroundColor White
        Write-Host "4. Verify: You should see only ONE 'MySDB Dashboard' with Tools" -ForegroundColor White
        Write-Host ""
        Write-Host "Expected menu structure:" -ForegroundColor Cyan
        Write-Host "  MySDB Dashboard" -ForegroundColor White
        Write-Host "  ├── Data Management" -ForegroundColor White
        Write-Host "  ├── Sections & Projects" -ForegroundColor White
        Write-Host "  ├── Marketing" -ForegroundColor White
        Write-Host "  ├── Relations & Targets" -ForegroundColor White
        Write-Host "  ├── Reporting (4 reports)" -ForegroundColor White
        Write-Host "  ├── Tools (2 wizards) <-- Should be here!" -ForegroundColor Green
        Write-Host "  └── Configuration" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "ERROR: SQL execution failed" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Common issues:" -ForegroundColor Yellow
        Write-Host "1. Wrong database name" -ForegroundColor White
        Write-Host "2. PostgreSQL not accessible" -ForegroundColor White
        Write-Host "3. Wrong credentials" -ForegroundColor White
        Write-Host ""
        Write-Host "Try manual execution:" -ForegroundColor Yellow
        Write-Host "  psql -U odoo -d $dbname" -ForegroundColor White
        Write-Host "  Then paste SQL from: $tempSqlFile" -ForegroundColor White
        Write-Host ""
    }
} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: Could not execute SQL" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Possible issues:" -ForegroundColor Yellow
    Write-Host "1. PostgreSQL (psql) not in PATH" -ForegroundColor White
    Write-Host "2. PostgreSQL not installed/running" -ForegroundColor White
    Write-Host "3. Incorrect credentials" -ForegroundColor White
    Write-Host ""
    Write-Host "SQL script saved at:" -ForegroundColor Yellow
    Write-Host "  $tempSqlFile" -ForegroundColor White
    Write-Host ""
    Write-Host "You can run it manually:" -ForegroundColor Yellow
    Write-Host "  psql -U odoo -d $dbname -f `"$tempSqlFile`"" -ForegroundColor White
    Write-Host ""
}

# Cleanup
Write-Host "Cleaning up temporary files..." -ForegroundColor Cyan
if (Test-Path $tempSqlFile) {
    Remove-Item $tempSqlFile -Force
    Write-Host "Temporary SQL file removed." -ForegroundColor Green
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

