-- ========================================
-- MySDB Connector - Remove Duplicate Menus
-- ========================================
--
-- This script removes duplicate MySDB Dashboard menus
-- caused by failed upgrade attempts
--
-- HOW TO USE:
-- 1. Stop Odoo completely
-- 2. Connect to your database:
--    psql -U odoo -d YOUR_DATABASE
-- 3. Copy and paste this entire script
-- 4. Start Odoo
-- 5. Clear browser cache
-- 6. Login and verify (should see only ONE MySDB Dashboard)
--
-- ========================================

BEGIN;

-- Show current MySDB menus (for reference)
SELECT id, name, complete_name, parent_id 
FROM ir_ui_menu 
WHERE name LIKE '%MySDB%' OR name LIKE '%mysdb%'
ORDER BY complete_name;

-- Remove duplicate MySDB Dashboard root menus
-- Keep only the one from odoo_mysql_connector module
DELETE FROM ir_ui_menu 
WHERE name = 'MySDB Dashboard' 
AND id NOT IN (
    SELECT res_id 
    FROM ir_model_data 
    WHERE module = 'odoo_mysql_connector' 
    AND model = 'ir.ui.menu' 
    AND name = 'menu_mysdb_dashboard_root'
);

-- Remove orphaned submenus (menus without valid parent)
DELETE FROM ir_ui_menu 
WHERE parent_id IN (
    SELECT id FROM ir_ui_menu WHERE name = 'MySDB Dashboard'
) AND id NOT IN (
    SELECT res_id 
    FROM ir_model_data 
    WHERE module = 'odoo_mysql_connector' 
    AND model = 'ir.ui.menu'
);

-- Verify cleanup - should show only valid menus now
SELECT id, name, complete_name, parent_id 
FROM ir_ui_menu 
WHERE name LIKE '%MySDB%' OR name LIKE '%mysdb%'
ORDER BY complete_name;

-- Count result
SELECT COUNT(*) as "MySDB Root Menus (should be 1)" 
FROM ir_ui_menu 
WHERE name = 'MySDB Dashboard';

COMMIT;

-- Done! Now:
-- 1. Type: \q (to exit psql)
-- 2. Start Odoo
-- 3. Clear browser cache (Ctrl+Shift+Delete)
-- 4. Login and verify

