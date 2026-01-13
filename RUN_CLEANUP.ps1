# MySDB Connector - Menu Cleanup
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "MySDB Duplicate Menu Cleanup Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$dbname = Read-Host "Enter your database name"

if ([string]::IsNullOrWhiteSpace($dbname)) {
    Write-Host "Error: Database name is required!" -ForegroundColor Red
    pause
    exit 1
}

Write-Host ""
Write-Host "Database: $dbname" -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Continue? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "Cancelled." -ForegroundColor Yellow
    pause
    exit 0
}

Write-Host ""
Write-Host "Creating SQL script..." -ForegroundColor Cyan

$sqlScript = @"
DELETE FROM ir_ui_menu 
WHERE name = 'MySDB Dashboard' 
AND id NOT IN (
    SELECT res_id FROM ir_model_data 
    WHERE module = 'odoo_mysql_connector' 
    AND model = 'ir.ui.menu' 
    AND name = 'menu_mysdb_dashboard_root'
);

SELECT COUNT(*) as remaining FROM ir_ui_menu WHERE name = 'MySDB Dashboard';
"@

$tempSqlFile = "$env:TEMP\mysdb_cleanup.sql"
$sqlScript | Out-File -FilePath $tempSqlFile -Encoding UTF8

Write-Host ""
Write-Host "Executing cleanup..." -ForegroundColor Cyan
Write-Host ""

psql -U odoo -d $dbname -f $tempSqlFile

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Cleanup completed!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Start Odoo" -ForegroundColor White
    Write-Host "2. Clear browser cache" -ForegroundColor White
    Write-Host "3. Login and verify" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "ERROR: SQL execution failed" -ForegroundColor Red
    Write-Host "Check database name and try again" -ForegroundColor Yellow
    Write-Host ""
}

Remove-Item $tempSqlFile -Force -ErrorAction SilentlyContinue
pause

