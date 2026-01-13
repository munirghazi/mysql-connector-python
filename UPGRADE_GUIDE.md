# Upgrade Guide - MySDB Connector v2.0

## 🎯 Overview
This guide will help you upgrade the MySDB Connector module to version 2.0 with all the enhanced features including:
- Project & Marketing Income Reports
- Enhanced Data Quality Audit
- Bulk Assignment Wizards
- Dynamic Period Management
- ROI & Profit Tracking

---

## ✅ Pre-Upgrade Checklist

Before upgrading, ensure:
- [ ] You have a **backup** of your database
- [ ] You have admin/system access to Odoo
- [ ] All users are logged out (recommended)
- [ ] No sync jobs are currently running

---

## 🚀 Upgrade Methods

### **Method 1: Odoo Apps Interface (Recommended)**

1. **Restart Odoo Service**
   ```powershell
   # Stop Odoo
   # (Use your Odoo service manager or restart the service)
   ```

2. **Login to Odoo**
   - Login as Administrator
   - Navigate to: **Apps**

3. **Update Apps List**
   - Click the **three dots** menu (⋮) in top right
   - Select **"Update Apps List"**
   - Click **"Update"** in the confirmation dialog
   - Wait for the process to complete

4. **Upgrade the Module**
   - Remove the "Apps" filter in the search bar
   - Search for: **"Odoo MySDB Connector"**
   - You should see version **17.0.2.0.0**
   - Click the **"Upgrade"** button
   - Wait for upgrade to complete (may take 1-2 minutes)

5. **Verify Upgrade**
   - Check that the version shows **17.0.2.0.0**
   - Navigate to **MySDB Dashboard**
   - You should see new menu items:
     - **Reporting** section has 2 new reports
     - **Tools** section (new) with 2 wizards

---

### **Method 2: Command Line (Alternative)**

If you prefer command line or the UI method doesn't work:

```powershell
# Navigate to Odoo directory
cd "C:\Program Files\Odoo 17.0.20250906\server"

# Run upgrade command (replace YOUR_DATABASE with your database name)
python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE --stop-after-init

# Restart Odoo service normally after upgrade completes
```

**Example:**
```powershell
python odoo-bin -u odoo_mysql_connector -d production_db --stop-after-init
```

---

## 🔍 Post-Upgrade Verification

### **1. Check New Menu Items**

Navigate to: **MySDB Dashboard**

You should see:

**✅ Reporting Section:**
- Orders Analysis (Joined) ← *existing*
- **Project Income Analysis** ← *NEW*
- **Marketing Income Analysis** ← *NEW*
- Data Maintenance Audit ← *enhanced*

**✅ Tools Section:** ← *NEW SECTION*
- **Bulk Assign to Project** ← *NEW*
- **Bulk Assign to Marketing** ← *NEW*

### **2. Verify Data Audit Enhancements**

1. Go to: **Reporting → Data Maintenance Audit**
2. Check for new columns:
   - Revenue (Total Order Value)
   - Orders (Order Count)
   - Priority (High/Medium/Low)
3. Apply filter: **High Priority**
4. Records should be color-coded:
   - Red = High priority
   - Orange = Medium priority
   - Grey = Low priority

### **3. Test Income Reports**

**Project Income Report:**
1. Go to: **Reporting → Project Income Analysis**
2. Should show columns:
   - Period, Project, Section, Store
   - Income, Target, Achievement %
   - Cost, Profit, ROI %
3. Try switching views: Tree, Graph, Pivot
4. Apply filter: **Current Year**

**Marketing Income Report:**
1. Go to: **Reporting → Marketing Income Analysis**
2. Should show columns:
   - Period, Account, Channel, Type
   - Income, Target, Achievement %
   - Cost, Profit, ROI %
3. Try channel filters (WhatsApp, SnapChat, etc.)

### **4. Test Bulk Assignment Wizards**

**Test Project Assignment:**
1. Go to: **Tools → Bulk Assign to Project**
2. Wizard should open with:
   - Target Project selector
   - Store filter
   - Assignment filter
   - Products list
3. Try selecting filters
4. Cancel (don't assign yet)

**Test Marketing Assignment:**
1. Go to: **Tools → Bulk Assign to Marketing**
2. Similar wizard should open
3. Test filters
4. Cancel

### **5. Verify Product Assignment Status**

1. Go to: **Data Management → Products**
2. Add optional columns (if not visible):
   - Has Project
   - Has Marketing
   - Assignment Status
3. Records should show:
   - ✓/✗ for Has Project/Marketing
   - Badge for Assignment Status (Complete/Partial/None)

### **6. Check Period Target Costs**

1. Go to: **Relations & Targets → Period Target Costs**
2. Click **Create** or edit existing
3. Check period dropdown:
   - Should show years 2024 to 2028
   - Format: YYYY-MM (Month Name) or YYYY-00 (Yearly)
4. Check if existing records show new fields:
   - Profit
   - ROI %
   - Period Year
   - Period Month

---

## 📊 Test with Real Data

### **Scenario 1: Create a Period Target**

1. Go to: **Period Target Costs → Create**
2. Fill in:
   - Period: Select current month (e.g., 2026-01)
   - Target Object: Select a Project
   - Target: 100000
   - Cost: 20000
3. Save
4. Check computed fields:
   - Actual Income (should calculate from orders)
   - Achievement % (should show percentage)
   - Profit (Income - Cost)
   - ROI % (should calculate)

### **Scenario 2: Run Data Audit**

1. Go to: **Reporting → Data Maintenance Audit**
2. Apply filters:
   - High Priority
   - Has Revenue
3. Sort by: Revenue (descending)
4. Should show products needing attention with revenue impact

### **Scenario 3: Bulk Assign Products**

1. Go to: **Data Maintenance Audit**
2. Note products with "No Project" or "Incomplete Assignment"
3. Go to: **Tools → Bulk Assign to Project**
4. Select:
   - Target: Choose a project
   - Filter: Products Without Project
5. Select a few test products
6. Click: **Assign Products**
7. Should show success notification with counts
8. Verify: Check products list - should now show assignment

### **Scenario 4: View Income Reports**

1. Ensure you have:
   - Some paid orders in the system
   - Products assigned to projects
   - Period targets set
2. Go to: **Reporting → Project Income Analysis**
3. Should populate with data showing:
   - Income from paid orders
   - Target comparison
   - Achievement percentage
4. Try Graph view - should show bar charts
5. Try Pivot view - should allow multi-dimensional analysis

---

## 🐛 Troubleshooting

### **Issue: Upgrade button not showing**
**Solution:**
- Click "Update Apps List" first
- Remove all search filters
- Search specifically for "MySDB"

### **Issue: Reports are empty**
**Causes & Solutions:**
- **No paid orders:** Reports only show paid orders data
- **No period targets:** Set some targets in Period Target Costs
- **Products not assigned:** Use bulk wizards to assign products
- **Database views not created:** Restart Odoo service

### **Issue: Wizards not appearing in Tools menu**
**Solution:**
- Refresh browser (Ctrl+F5)
- Clear browser cache
- Re-upgrade module
- Check security access rights

### **Issue: Period selection only shows old years**
**Solution:**
- This shouldn't happen with dynamic selection
- If it does: Restart Odoo service
- Check Python datetime import in models

### **Issue: Computed fields not calculating**
**Solution:**
1. Go to Settings → Technical → Scheduled Actions
2. Find any MySDB-related crons
3. Run manually if needed
4. Or edit a record and save to trigger recomputation

### **Issue: Views showing errors**
**Check Odoo logs:**
```powershell
# Check logs location (usually in):
C:\Program Files\Odoo 17.0.20250906\server\odoo.log
```

**Common errors:**
- Field not found: Model upgrade didn't run properly
- View error: XML syntax issue (shouldn't happen with provided files)
- Access denied: Security rules not loaded

---

## 🔄 Rollback (If Needed)

If something goes wrong and you need to rollback:

1. **Restore from backup** (safest)
   
2. **Or downgrade module:**
   ```powershell
   # Uninstall enhancements (loses new data)
   python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE --stop-after-init
   ```

3. **Restore previous version files:**
   - Replace the new files with your backed-up originals
   - Restart Odoo
   - Update module

---

## 📈 Performance Optimization (Optional)

After upgrade, for large databases (100k+ records):

### **Add Database Indexes** (if needed)

```sql
-- Connect to your PostgreSQL database
-- Run these if reports are slow:

CREATE INDEX IF NOT EXISTS idx_mysdb_order_payment_created 
ON mysdb_order(payment_status, order_created_at);

CREATE INDEX IF NOT EXISTS idx_mysdb_order_detail_sku_store 
ON mysdb_order_detail(product_sku, store_id);

CREATE INDEX IF NOT EXISTS idx_mysdb_product_sku_store 
ON mysdb_product(product_sku, store_id);
```

### **Refresh SQL Views** (if data looks stale)

Go to: **Settings → Technical → Database Structure → Views**
Search for: `mysdb`
Find and click **"Refresh"** on:
- `mysdb_project_income_report`
- `mysdb_marketing_income_report`
- `mysdb_data_audit`

---

## 📋 Upgrade Checklist Summary

- [ ] Backup database
- [ ] Restart Odoo
- [ ] Update Apps List
- [ ] Upgrade module to 17.0.2.0.0
- [ ] Verify new menus appear (Reporting + Tools)
- [ ] Test Data Audit report
- [ ] Test Project Income Report
- [ ] Test Marketing Income Report
- [ ] Test Bulk Assignment Wizards
- [ ] Check Product assignment status fields
- [ ] Verify Period selection is dynamic
- [ ] Create test period target
- [ ] Run test bulk assignment
- [ ] Review income reports with real data
- [ ] Document any issues
- [ ] Train users on new features

---

## 🎓 Next Steps After Upgrade

1. **Review Documentation**
   - Read: `ENHANCEMENTS_DOCUMENTATION.md`
   - Review: `EXECUTIVE_SUMMARY.md`

2. **Set Period Targets**
   - Define targets for current and upcoming periods
   - Input marketing costs

3. **Clean Up Data**
   - Use Data Audit to find issues
   - Use Bulk Wizards to fix assignments

4. **Train Users**
   - Show new reports
   - Demonstrate bulk wizards
   - Explain priority system in audit

5. **Monitor Performance**
   - Check report generation times
   - Review achievement percentages
   - Analyze ROI metrics

---

## 📞 Support

If you encounter issues:

1. **Check Odoo Logs**
   - Location: `C:\Program Files\Odoo 17.0.20250906\server\odoo.log`
   - Look for errors related to `mysdb`

2. **Verify Files**
   - Ensure all new files are present:
     - `views/mysdb_enhanced_views.xml`
     - Updated `security/security_rules.xml`
     - Updated `views/mysdb_menus.xml`
     - Updated `__manifest__.py`

3. **Check Database**
   - Verify SQL views were created:
     ```sql
     SELECT * FROM information_schema.views 
     WHERE table_name LIKE 'mysdb%';
     ```

---

## ✅ Success Indicators

You know the upgrade was successful when:

- ✅ Version shows **17.0.2.0.0**
- ✅ **5 new menu items** visible
- ✅ Data Audit shows **priority colors**
- ✅ Income reports display with **profit and ROI**
- ✅ Bulk wizards open successfully
- ✅ Products show **assignment status**
- ✅ Period selection includes **current year + 2**

---

**Upgrade completed successfully? Welcome to MySDB Connector v2.0! 🎉**

*Last Updated: January 2026*
*Module Version: 17.0.2.0.0*

