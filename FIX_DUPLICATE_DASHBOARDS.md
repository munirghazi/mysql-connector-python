# Fix Duplicate MySDB Dashboards

## 🎯 The Situation

You're seeing **TWO** "MySDB Dashboard" menus in Odoo, but you should only see ONE with the Tools section.

## 🔍 Root Cause

During the multiple failed upgrade attempts, Odoo created **duplicate menu entries in the database**. The code only defines ONE dashboard, but the database has old copies.

## ✅ The Solution

There are **3 methods** to fix this, from easiest to most thorough:

---

## 📋 **METHOD 1: Developer Mode Clear (Easiest - Try This First)**

1. **Enable Developer Mode:**
   - Settings → Activate Developer Mode
   - Or add `?debug=1` to your URL

2. **Clear Menu Cache:**
   - Settings → Technical → User Interface → Menu Items
   - Search: "MySDB Dashboard"
   - Delete ALL except one (keep the one with "odoo_mysql_connector" in the reference)

3. **Refresh:**
   - Settings → Technical → Database → Clear Assets/Sessions
   - Logout
   - Clear browser cache (Ctrl+Shift+Delete)
   - Login again

4. **Verify:**
   - Should see only ONE "MySDB Dashboard" with Tools menu

---

## 📋 **METHOD 2: SQL Cleanup (Recommended - Most Reliable)**

### **Step-by-Step:**

1. **Stop Odoo:**
   - Close Odoo completely
   - Verify it's stopped:
   ```powershell
   Get-Process | Where-Object {$_.ProcessName -like "*odoo*"}
   ```
   (Should return nothing)

2. **Connect to Database:**
   ```powershell
   psql -U odoo -d YOUR_DATABASE
   ```
   (Replace YOUR_DATABASE with your actual database name)

3. **Run Cleanup:**
   ```sql
   -- See current MySDB menus
   SELECT id, name, complete_name FROM ir_ui_menu 
   WHERE name LIKE '%MySDB%' 
   ORDER BY complete_name;

   -- Remove duplicates (keep only the official one)
   DELETE FROM ir_ui_menu 
   WHERE name = 'MySDB Dashboard' 
   AND id NOT IN (
       SELECT res_id FROM ir_model_data 
       WHERE module = 'odoo_mysql_connector' 
       AND model = 'ir.ui.menu' 
       AND name = 'menu_mysdb_dashboard_root'
   );

   -- Verify (should show only 1 root menu)
   SELECT COUNT(*) FROM ir_ui_menu WHERE name = 'MySDB Dashboard';
   ```

4. **Exit PostgreSQL:**
   ```sql
   \q
   ```

5. **Start Odoo:**
   - Start Odoo normally

6. **Clear Browser:**
   - Ctrl+Shift+Delete
   - Clear all cache
   - Close browser

7. **Login Fresh:**
   - Open new browser
   - Login
   - Verify: Only ONE "MySDB Dashboard" with Tools

---

## 📋 **METHOD 3: Complete Module Reload (Nuclear Option)**

**⚠️ WARNING:** This will reset all MySDB menus. Use only if Methods 1 & 2 fail!

1. **Backup First!**
   ```powershell
   pg_dump -U odoo YOUR_DATABASE > backup_before_reset.sql
   ```

2. **Stop Odoo**

3. **Clear All Module Data:**
   ```sql
   psql -U odoo -d YOUR_DATABASE
   
   -- Remove ALL MySDB menu entries
   DELETE FROM ir_ui_menu 
   WHERE id IN (
       SELECT res_id FROM ir_model_data 
       WHERE module = 'odoo_mysql_connector' 
       AND model = 'ir.ui.menu'
   );
   
   -- Remove menu references
   DELETE FROM ir_model_data 
   WHERE module = 'odoo_mysql_connector' 
   AND model = 'ir.ui.menu';
   
   \q
   ```

4. **Force Upgrade:**
   ```powershell
   cd "C:\Program Files\Odoo 17.0.20250906\server"
   python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE --stop-after-init
   ```

5. **Start Odoo and verify**

---

## 🎯 **What the CORRECT Menu Should Look Like:**

```
MySDB Dashboard (Root)
├── Data Management
│   ├── Orders
│   ├── Order Details
│   ├── Products
│   ├── Stores
│   └── POS Data
├── Sections & Projects
│   ├── Sections
│   └── Projects
├── Marketing
│   ├── Channels
│   └── Accounts
├── Relations & Targets
│   ├── Product Relations
│   ├── Marketing Relations
│   └── Period Target Costs
├── Reporting
│   ├── Orders Analysis (Joined)
│   ├── Project Income Analysis      ← NEW
│   ├── Marketing Income Analysis    ← NEW
│   └── Data Maintenance Audit
├── Tools                             ← NEW SECTION
│   ├── Bulk Assign to Project        ← NEW
│   └── Bulk Assign to Marketing      ← NEW
└── Configuration
    ├── Connector
    ├── Credentials
    └── Sync Logs
```

---

## 📊 **Quick Diagnosis:**

**How many MySDB Dashboards do you see?**

- **1 Dashboard (without Tools)** → Old version, needs upgrade
- **1 Dashboard (with Tools)** → Perfect! ✅
- **2 Dashboards** → Duplicates in database (use Method 2)
- **2+ Dashboards** → Serious duplication (use Method 3)

---

## 🚀 **After Cleanup:**

Once you have only ONE dashboard with Tools:

1. **Verify Version:**
   - Apps → MySDB Connector
   - Should show: 17.0.2.0.0

2. **Test New Features:**
   - Tools → Bulk Assign to Project ✅
   - Tools → Bulk Assign to Marketing ✅
   - Reporting → Project Income Analysis ✅
   - Reporting → Marketing Income Analysis ✅

3. **Check Data Audit:**
   - Reporting → Data Maintenance Audit
   - Should have color coding (red/orange/grey) ✅

---

## 💡 **Why This Happened:**

During your multiple upgrade attempts:
1. Each attempt created menu entries
2. Some attempts failed partway through
3. Odoo didn't clean up the old entries
4. Result: Duplicate menus in database

**This is normal with failed upgrades!** The cleanup fixes it.

---

## 📝 **SQL Script Provided:**

I've created: **`CLEANUP_DUPLICATE_MENUS.sql`**

This contains the complete SQL commands to run. You can:
- Copy/paste into psql
- Or run as a script

---

## ✅ **Success Checklist:**

After cleanup, verify:
- [ ] Only ONE "MySDB Dashboard" visible
- [ ] Tools section exists
- [ ] 2 items under Tools (Bulk Assign)
- [ ] 4 reports in Reporting section
- [ ] Version shows 17.0.2.0.0
- [ ] No duplicate menus anywhere

---

## 🆘 **Need Help?**

If you're not comfortable with SQL:

**Easy Alternative:**
1. Uninstall module (Apps → Uninstall)
2. Restart Odoo
3. Apps → Update Apps List
4. Install fresh

⚠️ **WARNING:** Uninstall removes data! Backup first!

---

**Recommendation:** Try **Method 2 (SQL Cleanup)** - it's safe, fast, and effective! 🎯

