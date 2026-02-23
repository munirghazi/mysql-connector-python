# Troubleshooting Guide - MySDB Connector v2.0

## 🚨 Common Upgrade Errors & Solutions

---

## Error 1: "External ID not found" or "ValueError: External ID not found in the system"

### **Symptom:**
```
ValueError: External ID not found in the system: odoo_mysql_connector.action_mysdb_XXX
```

### **Cause:**
- Action referenced in menu/view before it's defined
- Forward reference in XML files

### **Solution:**
✅ **FIXED** - We already fixed this by moving the action definition before the reference.

If you still see this error:
1. Check which action is missing from the error message
2. Search for the action definition in view files
3. Move the definition BEFORE any references to it

---

## Error 2: "KeyError" or Model Not Found

### **Symptom:**
```
KeyError: 'ir.model.data'
or
Model 'mysdb.project.income.report' not found
```

### **Cause:**
- Model not properly registered
- Python file not loaded

### **Solution:**
1. Check `models/__init__.py` includes all model files:
```python
from . import mysdb_data_models
```

2. Restart Odoo service completely
3. Try upgrade again

---

## Error 3: "Field does not exist" or "Unknown field"

### **Symptom:**
```
Unknown field 'mysdb.period_target_cost.profit'
or
Field 'roi' does not exist
```

### **Cause:**
- Database schema not updated
- Computed fields not created

### **Solution:**
1. **Run upgrade in update mode:**
```powershell
python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE --stop-after-init
```

2. **If that doesn't work, force recreation:**
```sql
-- Connect to PostgreSQL database
-- Drop the view and let Odoo recreate it
DROP VIEW IF EXISTS mysdb_project_income_report CASCADE;
DROP VIEW IF EXISTS mysdb_marketing_income_report CASCADE;
DROP VIEW IF EXISTS mysdb_data_audit CASCADE;
```

3. **Then upgrade again**

---

## Error 4: "psycopg2.errors.DuplicateObject" or "already exists"

### **Symptom:**
```
DuplicateObject: view "mysdb_project_income_report" already exists
```

### **Cause:**
- Odoo trying to create view that already exists
- Incomplete previous upgrade

### **Solution:**
```sql
-- Connect to your database
DROP VIEW IF EXISTS mysdb_project_income_report CASCADE;
DROP VIEW IF EXISTS mysdb_marketing_income_report CASCADE;
DROP VIEW IF EXISTS mysdb_data_audit CASCADE;
```

Then upgrade again.

---

## Error 5: XML Parse Error

### **Symptom:**
```
ParseError: while parsing file:...
```

### **Cause:**
- Invalid XML syntax
- Unclosed tags
- Special characters not escaped

### **Solution:**
1. **Run validation script:**
```powershell
cd "C:\Program Files\Odoo 17.0.20250906\server\odoo\custom_addon\odoo_mysql_connector"
python validate_files.py
```

2. **Check the specific file and line mentioned in error**

3. **Common fixes:**
   - Ensure all tags are closed: `<field name="x"/>`
   - Escape special characters: `&lt;` for `<`, `&gt;` for `>`
   - Check for unmatched quotes

---

## Error 6: "Access Denied" or Permission Error

### **Symptom:**
```
AccessError: You are not allowed to access 'Project Income Report'
```

### **Cause:**
- Security access rules not loaded

### **Solution:**
1. **Check security file is in manifest:**
```python
'data': [
    'security/security_rules.xml',
    ...
]
```

2. **Update module:**
```powershell
python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE --stop-after-init
```

3. **Clear cache and restart Odoo**

---

## Error 7: Import Error in Python

### **Symptom:**
```
ImportError: cannot import name 'X' from 'odoo'
or
ModuleNotFoundError: No module named 'calendar'
```

### **Cause:**
- Missing Python imports
- Wrong import statements

### **Solution:**
Check `models/mysdb_data_models.py` has these imports at the top:
```python
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import calendar
from datetime import datetime
```

If still failing, check Python version:
```powershell
python --version
```
Should be Python 3.8+

---

## Error 8: Database Connection Error

### **Symptom:**
```
OperationalError: FATAL: database "YOUR_DATABASE" does not exist
```

### **Cause:**
- Wrong database name
- Database not accessible

### **Solution:**
1. **Check database exists:**
```sql
psql -U odoo -l
```

2. **Use correct database name in upgrade command**

3. **Check PostgreSQL is running:**
```powershell
Get-Service -Name postgresql*
```

---

## Error 9: "Module not found" or "No module named odoo_mysql_connector"

### **Symptom:**
```
Module odoo_mysql_connector not found
```

### **Cause:**
- Module not in addons path
- Odoo can't find the module

### **Solution:**
1. **Check module is in correct location:**
```
C:\Program Files\Odoo 17.0.20250906\server\odoo\custom_addon\odoo_mysql_connector\
```

2. **Check `odoo.conf` has correct addons_path**

3. **Update apps list in Odoo:**
   - Apps → Update Apps List

---

## Error 10: Views Not Showing After Upgrade

### **Symptom:**
- Upgrade successful but new menus don't appear
- Reports not visible

### **Cause:**
- Browser cache
- User permissions
- Views not activated

### **Solution:**
1. **Clear browser cache:** Ctrl+Shift+Delete or Ctrl+F5

2. **Check you're logged in as Admin**

3. **Verify module version:**
   - Apps → Search "MySDB Connector"
   - Should show version 17.0.2.0.0

4. **Check menus exist:**
   - Settings → Technical → User Interface → Menu Items
   - Search for "Project Income Analysis"

5. **Force refresh:**
```powershell
# Restart Odoo completely
# Clear browser completely
# Login again
```

---

## Error 11: Computed Fields Showing Zero or Empty

### **Symptom:**
- `actual_income`, `profit`, `roi` showing as 0
- `achievement_percent` empty

### **Cause:**
- No paid orders in system
- Products not assigned to projects/marketing
- Period targets not set

### **Solution:**
1. **Check you have paid orders:**
   - Data Management → Orders
   - Filter: Payment Status = paid

2. **Check products are assigned:**
   - Data Management → Products
   - Verify "Assignment Status" column

3. **Set period targets:**
   - Relations & Targets → Period Target Costs
   - Create targets for current period

4. **Force recompute:**
   - Edit a period target record
   - Change any value and save
   - Should trigger recomputation

---

## Error 12: Wizard Not Opening

### **Symptom:**
- Clicking "Bulk Assign to Project" does nothing
- Wizard menu appears but no form opens

### **Cause:**
- JavaScript error
- Wizard view not found
- Action misconfigured

### **Solution:**
1. **Check browser console for errors:**
   - F12 → Console tab
   - Look for red errors

2. **Clear Odoo assets:**
```powershell
# In Odoo
Settings → Technical → Database Structure → Views
Search: "assets"
Click "Regenerate Assets Bundles"
```

3. **Check wizard view exists:**
   - Settings → Technical → User Interface → Views
   - Search: "mysdb.bulk.assign.project.wizard"

---

## 🔧 General Debugging Steps

### **1. Check Odoo Logs**
```powershell
# Log file location
C:\Program Files\Odoo 17.0.20250906\server\odoo.log

# Or run Odoo in foreground to see live logs
python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE
```

### **2. Run Validation Script**
```powershell
cd "C:\Program Files\Odoo 17.0.20250906\server\odoo\custom_addon\odoo_mysql_connector"
python validate_files.py
```

### **3. Check Database Directly**
```sql
-- Check if views exist
SELECT * FROM information_schema.views WHERE table_name LIKE 'mysdb%';

-- Check if models registered
SELECT * FROM ir_model WHERE model LIKE 'mysdb%';

-- Check if actions exist
SELECT * FROM ir_act_window WHERE name LIKE '%Income%';
```

### **4. Nuclear Option (Last Resort)**
If nothing works:

```powershell
# 1. Uninstall module
python odoo-bin -d YOUR_DATABASE
# In Odoo: Apps → MySDB Connector → Uninstall

# 2. Restart Odoo

# 3. Install fresh
# In Odoo: Apps → Update Apps List → Search → Install
```

⚠️ **WARNING:** Uninstalling will delete all data! Backup first!

---

## 📝 Before Asking for Help

If you need support, gather this information:

1. **Error Message** (full traceback)
2. **Odoo Version:** 17.0.20250906
3. **Module Version:** Check in Apps
4. **What you were doing** when error occurred
5. **Odoo log file** (last 50 lines)
6. **Validation script output**

```powershell
# Get log tail
Get-Content "C:\Program Files\Odoo 17.0.20250906\server\odoo.log" -Tail 50

# Run validation
python validate_files.py > validation_output.txt
```

---

## ✅ Successful Upgrade Checklist

After upgrade completes successfully, verify:

- [ ] Module version shows 17.0.2.0.0
- [ ] **Reporting** menu has 4 items (including 2 new)
- [ ] **Tools** menu exists with 2 wizards
- [ ] Can open "Project Income Analysis"
- [ ] Can open "Marketing Income Analysis"
- [ ] Can open "Data Maintenance Audit" with colors
- [ ] Can open "Bulk Assign to Project" wizard
- [ ] Can open "Bulk Assign to Marketing" wizard
- [ ] Products show "Assignment Status" column
- [ ] Period dropdown shows dynamic years (2024-2028)
- [ ] Period targets show new fields (Profit, ROI)

---

## 🚀 Quick Fix Commands

### **Complete Clean Restart**
```powershell
# Stop Odoo service
# Drop and recreate views
psql -U odoo -d YOUR_DATABASE -c "DROP VIEW IF EXISTS mysdb_project_income_report CASCADE;"
psql -U odoo -d YOUR_DATABASE -c "DROP VIEW IF EXISTS mysdb_marketing_income_report CASCADE;"
psql -U odoo -d YOUR_DATABASE -c "DROP VIEW IF EXISTS mysdb_data_audit CASCADE;"

# Upgrade module
cd "C:\Program Files\Odoo 17.0.20250906\server"
python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE --stop-after-init

# Start Odoo service
# Clear browser cache (Ctrl+Shift+Delete)
# Login and verify
```

### **Force Module Reload**
```powershell
python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE --stop-after-init --log-level=debug
```

### **Check What Changed**
```sql
-- See what was updated
SELECT name, write_date FROM ir_module_module WHERE name = 'odoo_mysql_connector';

-- See new models
SELECT model FROM ir_model WHERE model LIKE 'mysdb%' ORDER BY create_date DESC LIMIT 10;
```

---

*Last Updated: January 2026*
*For MySDB Connector v2.0 (17.0.2.0.0)*

