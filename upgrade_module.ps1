# MySDB Connector Module Upgrade Script
# This script will upgrade the module and show any errors

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MySDB Connector v2.0 Upgrade Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get database name from user
$dbname = Read-Host "Enter your database name"

if ([string]::IsNullOrWhiteSpace($dbname)) {
    Write-Host "Error: Database name is required!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Database: $dbname" -ForegroundColor Yellow
Write-Host "Module: odoo_mysql_connector" -ForegroundColor Yellow
Write-Host ""

# Confirm
$confirm = Read-Host "Continue with upgrade? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Upgrade cancelled." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting upgrade..." -ForegroundColor Green
Write-Host ""

# Change to Odoo directory
Set-Location "C:\Program Files\Odoo 17.0.20250906\server"

# Run upgrade command
Write-Host "Running: python odoo-bin -u odoo_mysql_connector -d $dbname --stop-after-init" -ForegroundColor Cyan
Write-Host ""

try {
    python odoo-bin -u odoo_mysql_connector -d $dbname --stop-after-init 2>&1 | Tee-Object -FilePath "upgrade_log.txt"
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Upgrade completed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Log saved to: upgrade_log.txt" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Start Odoo service normally" -ForegroundColor White
    Write-Host "2. Login and verify new menus appear" -ForegroundColor White
    Write-Host "3. Check: MySDB Dashboard -> Reporting (3 new reports)" -ForegroundColor White
    Write-Host "4. Check: MySDB Dashboard -> Tools (2 new wizards)" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Upgrade failed with error:" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Log saved to: upgrade_log.txt" -ForegroundColor Yellow
    Write-Host "Please check the log file for details." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

