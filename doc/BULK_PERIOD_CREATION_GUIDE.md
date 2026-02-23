# 📅 Bulk Period Creation Wizard - User Guide

## Overview

The **Bulk Period Creation Wizard** allows you to quickly create multiple period target/cost records for projects or marketing accounts. This powerful tool eliminates the need for manual entry of each period, saving time and reducing errors.

## 🌟 Key Features

### 1. Flexible Target Selection
- **Project**: Create periods for a specific project
- **Marketing Account**: Create periods for a marketing account

### 2. Smart Period Options
- **Yearly Period**: Creates a period like `202600` (represents full year 2026)
- **Monthly Periods**: Creates 12 periods (`202601` through `202612`)
- **Specific Months**: Select only the months you need

### 3. Cost Calculation Options ⭐
Choose how to calculate costs:

#### Option A: Percentage of Target
- Enter a percentage (e.g., 20%)
- Cost is automatically calculated from target
- Example: Target 10,000 @ 20% = Cost 2,000

#### Option B: Manual Entry
- Enter the exact cost amount directly
- Full control over cost values

### 4. Distribution Methods
- **Same Value**: Each period gets the full target/cost amount
- **Distribute Evenly**: Total target/cost is split across all periods

## 📋 Step-by-Step Guide

### Step 1: Open the Wizard
1. Go to **MySDB Dashboard** > **Tools** > **Bulk Create Periods**
2. A wizard window will open

### Step 2: Select Target
1. Choose **Target Type**:
   - Select "Project" for project-based periods
   - Select "Marketing Account" for marketing periods
2. Select the specific **Project** or **Marketing Account**

### Step 3: Configure Periods
1. **Select Year**: Choose from 2024 to current year + 2
2. **Create Yearly Period**: Check to create annual period (YYYY00)
3. **Create Monthly Periods**: Check to create 12 monthly periods
4. **Select Specific Months** (optional):
   - Check this if you don't want all 12 months
   - Select individual months (Jan, Feb, Mar, etc.)

### Step 4: Set Financial Values
1. **Target Amount**: Enter the target revenue/goal amount
2. **Distribution**:
   - **Same Value**: Each period gets the full amount you entered
   - **Distribute Evenly**: Amount is divided across all periods
3. **Cost Calculation**:
   - **Calculate as % of Target**: Enter percentage (e.g., 20)
     - Cost is auto-calculated
   - **Enter Cost Manually**: Choose this to enter exact cost
     - Enter cost amount directly

### Step 5: Review Preview
- The preview section shows:
  - Number of periods to be created
  - Target object name
  - Example period records with their values
  - Total count of records

### Step 6: Create Periods
1. Click **"Create Periods"** button
2. System will:
   - Check for existing periods (won't duplicate)
   - Create new period records
   - Show success notification with summary

## 💡 Usage Examples

### Example 1: Annual Project with Percentage Cost
```
Target Type: Project
Project: "Water Distribution 2026"
Year: 2026
Create Yearly: ✓
Create Monthly: ✗
Target Amount: 500,000
Distribution: Same Value
Cost Calculation: Calculate as % of Target
Cost %: 15%

Result: 1 period created
- Period 202600 → Target: 500,000 | Cost: 75,000
```

### Example 2: Monthly Marketing with Manual Cost
```
Target Type: Marketing Account
Account: "Facebook Ads"
Year: 2026
Create Yearly: ✗
Create Monthly: ✓
Select Specific Months: ✗ (all 12 months)
Target Amount: 120,000
Distribution: Distribute Evenly
Cost Calculation: Enter Cost Manually
Cost Amount: 36,000

Result: 12 periods created
- Period 202601 → Target: 10,000 | Cost: 3,000
- Period 202602 → Target: 10,000 | Cost: 3,000
- ... (10 more months)
```

### Example 3: Specific Months Only
```
Target Type: Project
Project: "Ramadan Campaign"
Year: 2026
Create Yearly: ✗
Create Monthly: ✓
Select Specific Months: ✓
  ✓ March
  ✓ April
  ✓ May
Target Amount: 15,000
Distribution: Same Value
Cost Calculation: Percentage (20%)

Result: 3 periods created
- Period 202603 → Target: 15,000 | Cost: 3,000
- Period 202604 → Target: 15,000 | Cost: 3,000
- Period 202605 → Target: 15,000 | Cost: 3,000
```

### Example 4: Both Yearly and Monthly
```
Target Type: Project
Project: "Annual Giving Program"
Year: 2026
Create Yearly: ✓
Create Monthly: ✓
Target Amount: 1,200,000
Distribution: Distribute Evenly
Cost %: 10%

Result: 13 periods created (1 yearly + 12 monthly)
- Period 202600 → Target: 92,308 | Cost: 9,231
- Period 202601 → Target: 92,308 | Cost: 9,231
- ... (11 more months)
```

## ⚠️ Important Notes

### Duplicate Prevention
- The wizard checks for existing periods before creating
- If a period already exists, it will be skipped
- You'll see a summary of created vs. skipped records

### Period Format
- **Yearly**: `YYYY00` (e.g., 202600)
- **Monthly**: `YYYYMM` (e.g., 202601 = January 2026)
- First 4 digits = Year
- Last 2 digits = Month (00 for yearly)

### Cost Calculation
- **Percentage Mode**: Cost updates automatically when you change target or percentage
- **Manual Mode**: You have full control, enter any cost amount
- Switch between modes anytime before creating

### Distribution Logic
- **Same Value**: Good for consistent monthly targets
  - Example: Each month should hit 50,000
- **Distribute Evenly**: Good for total annual targets
  - Example: Annual target of 600,000 → 50,000 per month

## 🎯 Best Practices

1. **Plan Your Periods**
   - Decide if you need yearly, monthly, or both
   - Use yearly for high-level tracking
   - Use monthly for detailed management

2. **Cost Calculation**
   - Use percentage for consistent cost ratios
   - Use manual for special cases or fixed costs

3. **Distribution Strategy**
   - Use "Same Value" for regular operations
   - Use "Distribute Evenly" for annual budgets

4. **Review Before Creating**
   - Always check the preview section
   - Verify the number of periods to be created
   - Confirm the target and cost values

5. **Avoid Duplicates**
   - Check existing periods first
   - The wizard prevents duplicates automatically
   - But better to know what's already there

## 🔍 Troubleshooting

### "Please select a Project/Marketing Account"
- **Cause**: No target selected
- **Solution**: Choose a project or marketing account from the dropdown

### "Please select at least one option: Yearly or Monthly"
- **Cause**: Both yearly and monthly options are unchecked
- **Solution**: Check at least one option

### "Target amount must be greater than zero"
- **Cause**: Target is 0 or negative
- **Solution**: Enter a positive target amount

### No Periods Created (All Skipped)
- **Cause**: All periods already exist for that target and year
- **Solution**: 
  - Check existing period records
  - Use a different year
  - Or delete existing periods if needed

## 📊 After Creation

After creating periods, you can:

1. **View Created Records**
   - Go to **Relations & Targets** > **Period Target Costs**
   - Filter by project/marketing account
   - Filter by year (period starts with year)

2. **Edit Individual Periods**
   - Open any period record
   - Adjust target or cost as needed
   - Track actual income vs. target

3. **Generate Reports**
   - Use **Project Income Report** for project analysis
   - Use **Marketing Income Report** for marketing ROI
   - View achievement percentages and profit calculations

## 🚀 Pro Tips

1. **Create Yearly First**: Create yearly period for overview, then monthly for details
2. **Use Templates**: Set up one project completely, use same values for similar projects
3. **Seasonal Adjustments**: Use specific months for seasonal campaigns
4. **Cost Monitoring**: Start with percentage, adjust manually later if needed
5. **Batch Creation**: Create periods for multiple projects/accounts one at a time

## 📞 Need Help?

If you encounter any issues or need assistance:
- Check the preview before creating
- Verify your target and cost calculations
- Review existing period records
- Contact your system administrator

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Module**: odoo_mysql_connector

