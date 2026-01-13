# MySDB Connector - Production Deployment Checklist

## 📋 Pre-Deployment Checklist

### Phase 1: Code Cleanup ✅
```powershell
# Run from module directory
.\CLEANUP_MODULE.bat
```

**Verifies:**
- [ ] Remove backup files (mysdp_data_models.py)
- [ ] Remove temporary Python files
- [ ] Validate all XML files
- [ ] Check model consistency
- [ ] Verify security rules

---

### Phase 2: Database Cleanup ✅
```powershell
# Run from module directory
.\CLEANUP_MENUS.bat
```

**Actions:**
- [ ] Remove duplicate menu entries
- [ ] Clean up orphaned actions
- [ ] Reset view priorities
- [ ] Clear cache entries

**Required:** Database name (e.g., odoo_db)

---

### Phase 3: Odoo Service Management ✅

#### Stop Odoo Service
```powershell
# Windows Service
Stop-Service "Odoo 17.0"

# Or if running from command line
# Press Ctrl+C in the terminal running Odoo
```

#### Clear Odoo Cache
```powershell
# Navigate to Odoo session directory
cd "C:\Users\[USERNAME]\AppData\Local\OpenERP S.A\Odoo"
Remove-Item -Recurse -Force *

# Or clear Python cache in module
cd "C:\Program Files\Odoo 17.0.20250906\server\odoo\custom_addon\odoo_mysql_connector"
Remove-Item -Recurse -Force models\__pycache__
```

#### Start Odoo Service
```powershell
# Windows Service
Start-Service "Odoo 17.0"

# Or from command line with upgrade flag
cd "C:\Program Files\Odoo 17.0.20250906\server"
.\odoo-bin -u odoo_mysql_connector -d [DB_NAME]
```

- [ ] Service stopped successfully
- [ ] Cache cleared
- [ ] Service started successfully
- [ ] No errors in logs

---

### Phase 4: Module Upgrade ✅

**Option A: From Odoo UI (Recommended)**
1. Log in as Administrator
2. Go to: Apps → Search "MySDB"
3. Click "Upgrade" button
4. Wait for completion
5. Refresh browser (Ctrl+F5)

**Option B: Command Line**
```powershell
cd "C:\Program Files\Odoo 17.0.20250906\server\odoo\custom_addon\odoo_mysql_connector"
.\UPGRADE_NOW.bat
```

**Verification:**
- [ ] Upgrade completed without errors
- [ ] Module version shows 17.0.2.0.0
- [ ] All menus visible
- [ ] No duplicate dashboards

---

### Phase 5: Data Import & Validation ✅

#### Import Data from MySQL
1. Go to: MySDB Dashboard → Configuration → MySQL Credentials
2. Verify connection settings
3. Go to: MySDB Dashboard → Configuration → MySQL Connector
4. Click "Sync Data" for each table:
   - [ ] Stores
   - [ ] Orders
   - [ ] Order Details
   - [ ] Products
   - [ ] POS Data

#### Run Data Audit
1. Go to: MySDB Dashboard → Reporting → Data Maintenance Audit
2. Review audit results:
   - [ ] Check "Missing Products" count
   - [ ] Check "Unassigned to Project" count
   - [ ] Check "Unassigned to Marketing" count
   - [ ] Check "Incomplete Assignment" count

#### Assign Products (if needed)
1. Go to: MySDB Dashboard → Tools → Bulk Assign to Project
2. Select products and project
3. Click "Assign to Project"
4. Repeat for marketing assignments

---

### Phase 6: Report Validation ✅

#### Test Project Income Report
1. Go to: MySDB Dashboard → Reporting → Project Income Analysis
2. Select period (year/month)
3. Verify data displays correctly:
   - [ ] Total Income
   - [ ] Order Count
   - [ ] Product Count
   - [ ] Target Amount
   - [ ] Cost Amount
   - [ ] Achievement %
   - [ ] Profit
   - [ ] ROI

#### Test Marketing Income Report
1. Go to: MySDB Dashboard → Reporting → Marketing Income Analysis
2. Select period (year/month)
3. Verify data displays correctly:
   - [ ] All metrics same as above
   - [ ] Marketing channel breakdown
   - [ ] Account-level details

#### Test Period Target/Cost Management
1. Go to: MySDB Dashboard → Master Data → Period Targets & Costs
2. Create test period:
   - [ ] Yearly period (e.g., 202600)
   - [ ] Monthly period (e.g., 202601)
3. Verify:
   - [ ] Actual income calculates correctly
   - [ ] Achievement % shows
   - [ ] Variance calculates

---

### Phase 7: User Acceptance Testing ✅

#### End User Tests
- [ ] User can view all menus
- [ ] User can filter and search data
- [ ] User can switch between view types (tree/pivot/graph)
- [ ] User can export data (if needed)
- [ ] User understands navigation

#### Admin Tests
- [ ] Can create new sections/projects
- [ ] Can create marketing channels/accounts
- [ ] Can assign products to projects
- [ ] Can assign products to marketing
- [ ] Can set period targets/costs
- [ ] Can run data audit

---

### Phase 8: Performance Testing ✅

#### Response Time Tests
```sql
-- Connect to PostgreSQL
psql -U odoo -d [DB_NAME]

-- Test report query performance
EXPLAIN ANALYZE SELECT * FROM mysdb_project_income_report WHERE period = '202601';
EXPLAIN ANALYZE SELECT * FROM mysdb_marketing_income_report WHERE period = '202601';
EXPLAIN ANALYZE SELECT * FROM mysdb_data_audit WHERE issue_type = 'missing_product';
```

**Expected Response Times:**
- [ ] Small dataset (<10K orders): <500ms
- [ ] Medium dataset (10-100K orders): <2s
- [ ] Large dataset (>100K orders): <5s

If slower, consider:
- Adding database indexes
- Optimizing SQL views
- Enabling PostgreSQL query caching

---

### Phase 9: Documentation Review ✅

#### User Documentation
- [ ] START_HERE.md reviewed by end users
- [ ] QUICK_REFERENCE.md accessible to all users
- [ ] TROUBLESHOOTING.md bookmarked for support

#### Technical Documentation
- [ ] UPGRADE_GUIDE.md available for future upgrades
- [ ] ENHANCEMENTS_DOCUMENTATION.md archived
- [ ] MODULE_ANALYSIS_REPORT.md available for developers

---

### Phase 10: Backup & Rollback Plan ✅

#### Create Backup
```powershell
# Backup Odoo database
pg_dump -U odoo -d [DB_NAME] > backup_before_deployment_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Backup module files
cd "C:\Program Files\Odoo 17.0.20250906\server\odoo\custom_addon"
Compress-Archive -Path odoo_mysql_connector -DestinationPath "odoo_mysql_connector_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"
```

- [ ] Database backup created
- [ ] Module backup created
- [ ] Backups stored in safe location

#### Rollback Plan (if needed)
1. Stop Odoo service
2. Restore database:
   ```powershell
   psql -U odoo -d [DB_NAME] < backup_file.sql
   ```
3. Restore module files:
   ```powershell
   Expand-Archive -Path backup.zip -DestinationPath ".." -Force
   ```
4. Restart Odoo service
5. Downgrade module in Odoo UI

---

## 🚀 Go-Live Checklist

### Final Verification
- [ ] All pre-deployment phases completed
- [ ] No errors in Odoo logs
- [ ] All reports show accurate data
- [ ] End users trained
- [ ] Support team briefed
- [ ] Backup verified and accessible

### Communication
- [ ] Notify all users of new features
- [ ] Share QUICK_REFERENCE.md
- [ ] Set up support channel (email/chat)
- [ ] Schedule follow-up meeting (1 week)

### Monitoring (First Week)
- [ ] Daily log review
- [ ] User feedback collection
- [ ] Performance monitoring
- [ ] Data accuracy verification
- [ ] Issue tracking setup

---

## 📞 Support Information

### Self-Service Resources
1. **QUICK_REFERENCE.md** - Daily operations guide
2. **TROUBLESHOOTING.md** - Common issues & solutions
3. **START_HERE.md** - Complete user guide

### Escalation Path
1. **Level 1:** Check TROUBLESHOOTING.md
2. **Level 2:** Review Odoo logs
3. **Level 3:** Database diagnostics
4. **Level 4:** Contact module developer

### Critical Issues
- Database connection failures
- Data import errors
- Permission/access issues
- Performance degradation

---

## ✅ Sign-Off

### Technical Lead
- **Name:** ________________________
- **Date:** ________________________
- **Signature:** ___________________

### Business Owner
- **Name:** ________________________
- **Date:** ________________________
- **Signature:** ___________________

### End User Representative
- **Name:** ________________________
- **Date:** ________________________
- **Signature:** ___________________

---

## 📊 Post-Deployment Metrics

### Week 1 Targets
- [ ] Zero critical issues
- [ ] <3 minor issues
- [ ] 100% user access confirmed
- [ ] 95%+ data accuracy

### Week 2 Targets
- [ ] All minor issues resolved
- [ ] User satisfaction survey completed
- [ ] Performance baseline established
- [ ] Documentation finalized

### Month 1 Targets
- [ ] Full adoption by all users
- [ ] Regular reports being used
- [ ] Data quality maintained
- [ ] No rollback required

---

**Deployment Date:** _________________  
**Module Version:** 17.0.2.0.0  
**Odoo Version:** 17.0.20250906  
**Database:** _________________

---

**Notes:**
- This checklist should be completed sequentially
- Do not skip phases unless explicitly approved
- Document any deviations or issues
- Keep this checklist for audit purposes

