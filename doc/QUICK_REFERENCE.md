# MySDB Connector v2.0 - Quick Reference Card

## 📍 Menu Locations

### **Reporting** (MySDB Dashboard → Reporting)
| Report | What It Shows | Best For |
|--------|--------------|----------|
| **Project Income Analysis** | Income, targets, ROI by project & period | Project performance tracking |
| **Marketing Income Analysis** | Income, targets, ROI by marketing account & period | Campaign effectiveness |
| **Data Maintenance Audit** | Products needing attention (prioritized) | Data quality management |
| Orders Analysis | Combined order data with relations | Detailed order analysis |

### **Tools** (MySDB Dashboard → Tools)
| Tool | Purpose | Use When |
|------|---------|----------|
| **Bulk Assign to Project** | Assign multiple products to a project | Setting up projects or fixing unassigned products |
| **Bulk Assign to Marketing** | Assign multiple products to marketing account | Setting up campaigns or fixing incomplete data |

---

## 🎯 Common Tasks

### **Task 1: Check Data Quality Issues**
```
Path: MySDB Dashboard → Reporting → Data Maintenance Audit
Filter: High Priority + Has Revenue
Action: Fix high-value issues first
```

### **Task 2: Review Monthly Performance**
```
Path: MySDB Dashboard → Reporting → Project Income Analysis
Filter: Current Month
Sort: By Achievement %
Action: Identify underperforming projects
```

### **Task 3: Analyze Marketing ROI**
```
Path: MySDB Dashboard → Reporting → Marketing Income Analysis
Filter: Current Year
Group By: Channel Type
Action: Compare ROI across channels
```

### **Task 4: Bulk Assign Products**
```
Path: MySDB Dashboard → Tools → Bulk Assign to Project
Steps:
1. Select target project
2. Filter: Products Without Project
3. Select products
4. Click: Assign Products
```

### **Task 5: Set Period Targets**
```
Path: MySDB Dashboard → Relations & Targets → Period Target Costs
Steps:
1. Click: Create
2. Select: Period (e.g., 2026-01)
3. Select: Target Object (Project/Marketing Account)
4. Enter: Target amount
5. Enter: Cost amount
6. Save (metrics auto-calculate)
```

---

## 🔢 Period Format Guide

| Format | Example | Meaning |
|--------|---------|---------|
| YYYY00 | 202600 | Yearly target for 2026 |
| YYYYMM | 202601 | January 2026 |
| YYYYMM | 202612 | December 2026 |

**Auto-generates:** 2024 to (Current Year + 2)

---

## 📊 Key Metrics Explained

### **Achievement %**
```
Formula: (Actual Income / Target) × 100
Good: ≥ 100% (green)
Warning: 70-99% (orange)
Poor: < 70% (red)
```

### **ROI (Return on Investment) %**
```
Formula: ((Income - Cost) / Cost) × 100
Example: Income=150k, Cost=50k → ROI=200%
High ROI: > 100%
Low ROI: < 50%
```

### **Profit**
```
Formula: Income - Cost
Example: Income=150k, Cost=50k → Profit=100k
```

### **Variance**
```
Formula: Actual Income - Target
Positive: Exceeding target
Negative: Below target
```

---

## 🎨 Color Coding

### **Data Audit**
- 🔴 **Red:** High priority (recent orders, high revenue)
- 🟠 **Orange:** Medium priority (orders in last 90 days)
- ⚫ **Grey:** Low priority (old or no orders)

### **Income Reports**
- 🟢 **Green:** Achievement ≥ 100%
- 🟠 **Orange:** Achievement 70-99%
- 🔴 **Red:** Achievement < 70%

### **Product Assignment Status**
- 🟢 **Complete:** Has both project AND marketing
- 🟠 **Partial:** Has only project OR marketing
- 🔴 **None:** No assignments

---

## 🔍 Useful Filters

### **Data Audit Filters**
- `High Priority` - Critical issues
- `Has Revenue` - Impacting sales
- `No Project` - Missing project assignment
- `Incomplete Assignment` - Needs both project & marketing

### **Income Report Filters**
- `Current Year` - This year's data
- `Last 3 Months` - Recent trends
- `Achieving Target` - Meeting goals
- `Underperforming (<70%)` - Needs attention
- `Profitable` - Positive profit
- `High ROI (>100%)` - Great returns

### **Product Filters**
- `No Project` - Products without project
- `No Marketing` - Products without marketing
- `Incomplete Assignment` - Missing one relation

---

## ⚡ Quick Wins

### **Week 1 After Upgrade**
1. ✅ Run Data Audit
2. ✅ Fix high-priority missing products
3. ✅ Set current month targets

### **Week 2**
1. ✅ Use bulk wizards to assign unassigned products
2. ✅ Review project income reports
3. ✅ Identify underperforming projects

### **Week 3**
1. ✅ Analyze marketing ROI by channel
2. ✅ Set quarterly targets
3. ✅ Train team on new features

### **Ongoing**
1. 📅 **Weekly:** Check high-priority audit issues
2. 📅 **Monthly:** Review income reports and set next month's targets
3. 📅 **Quarterly:** Analyze trends and adjust strategies

---

## 🎓 Power User Tips

### **Tip 1: Export to Excel**
All reports have "Export to Excel" button (tree views)
Use for: Presentations, external analysis

### **Tip 2: Pivot Tables**
Income reports have Pivot view
Use for: Multi-dimensional analysis, drill-down

### **Tip 3: Graph Views**
Switch to Graph view for visual analysis
Change chart type: Bar, Line, Pie

### **Tip 4: Save Filters**
- Apply filters you use often
- Click "Save current search"
- Name it and make it default

### **Tip 5: Group By**
Use "Group By" in search filters for:
- Period analysis (by year/month)
- Category analysis (by section/channel)
- Store comparison

---

## 🚨 Common Mistakes to Avoid

| ❌ Don't | ✅ Do Instead |
|---------|-------------|
| Ignore data audit | Check weekly and fix high-priority items |
| Set unrealistic targets | Base on historical data + 10-15% |
| Assign products to wrong store | Wizards validate - but double-check |
| Leave products unassigned | Use bulk wizards immediately |
| Only look at income | Also track ROI and profit |
| Set targets without costs | Always input both for ROI tracking |

---

## 📱 Workflow Examples

### **Morning Check (5 minutes)**
```
1. Open: Data Maintenance Audit
2. Filter: High Priority
3. Note: Top 3 issues
4. Plan: When to fix them
```

### **Month-End Review (15 minutes)**
```
1. Open: Project Income Analysis
2. Filter: Current Month
3. Sort: By Achievement %
4. Export: Top/bottom performers
5. Open: Marketing Income Analysis
6. Group By: Channel Type
7. Compare: ROI across channels
8. Document: Findings for meeting
```

### **Quarterly Planning (30 minutes)**
```
1. Open: Project Income Analysis
2. Filter: Last Quarter
3. Analyze: Trends
4. Open: Period Target Costs
5. Set: Next quarter targets (3 months)
6. Base on: Historical + growth factor
7. Document: Assumptions
```

### **Product Setup (One-time, 30 minutes)**
```
1. Open: Data Audit
2. Filter: No Project
3. Note: Products by store
4. Open: Bulk Assign to Project
5. For each store:
   - Select project
   - Filter by store
   - Assign products
6. Repeat for Marketing
7. Verify: Products show "Complete" status
```

---

## 📞 Help & Documentation

| Question | Where to Find Answer |
|----------|---------------------|
| Detailed feature docs | `ENHANCEMENTS_DOCUMENTATION.md` |
| Business value & ROI | `EXECUTIVE_SUMMARY.md` |
| Upgrade instructions | `UPGRADE_GUIDE.md` |
| Implementation notes | `IMPLEMENTATION_SUMMARY.md` |

---

## 🎯 Success Metrics

Track these to measure improvement:

### **Data Quality**
- **Metric:** % of products with complete assignment
- **Target:** > 95%
- **Check:** Data Audit report

### **Target Achievement**
- **Metric:** % of projects achieving target
- **Target:** > 70%
- **Check:** Project Income Report

### **Marketing Efficiency**
- **Metric:** Average ROI across campaigns
- **Target:** > 150%
- **Check:** Marketing Income Report

### **Time Savings**
- **Metric:** Time spent on monthly reports
- **Before:** 4+ hours
- **After:** < 15 minutes
- **Savings:** 93%

---

## ⌨️ Keyboard Shortcuts (Odoo Standard)

| Action | Shortcut |
|--------|----------|
| Search | `/` |
| Create | `Alt+C` |
| Save | `Alt+S` |
| Discard | `Alt+D` |
| Edit | `Alt+E` |
| Export | `Alt+X` |

---

*Keep this card handy for quick reference!*
*Version: 2.0 | Last Updated: January 2026*

