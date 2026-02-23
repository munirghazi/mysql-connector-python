# 🔄 Bulk Period Creation Wizard - Workflow Diagram

## Visual Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    BULK PERIOD CREATION WIZARD                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: SELECT TARGET                                          │
├─────────────────────────────────────────────────────────────────┤
│  ○ Project          ○ Marketing Account                         │
│  [Select Project ▼]  or  [Select Marketing Account ▼]          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: SELECT PERIODS                                         │
├─────────────────────────────────────────────────────────────────┤
│  Year: [2026 ▼]                                                 │
│  ☑ Create Yearly Period (202600)                               │
│  ☑ Create Monthly Periods (202601-202612)                      │
│     └─ ☐ Select Specific Months                                │
│         [Jan] [Feb] [Mar] [Apr] [May] [Jun]                    │
│         [Jul] [Aug] [Sep] [Oct] [Nov] [Dec]                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: FINANCIAL VALUES                                       │
├─────────────────────────────────────────────────────────────────┤
│  Target Amount: [____________]                                  │
│  Distribution:  ○ Same Value  ○ Distribute Evenly             │
│                                                                 │
│  Cost Calculation:  ○ Percentage  ○ Manual Entry              │
│                                                                 │
│  IF Percentage:                 IF Manual:                     │
│    Cost %: [20.00]                Cost Amount: [______]       │
│    ↓ auto-calc                                                 │
│    Cost: 20,000                                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PREVIEW                                                        │
├─────────────────────────────────────────────────────────────────┤
│  For: Water Distribution Project                                │
│  Year: 2026                                                     │
│                                                                 │
│  Will create 13 period record(s):                              │
│                                                                 │
│  • 2026-00 (Yearly): Target 92,308 | Cost 18,462              │
│  • 2026-01 (Jan): Target 92,308 | Cost 18,462                 │
│  • 2026-02 (Feb): Target 92,308 | Cost 18,462                 │
│    ... and 10 more month(s)                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  ACTION                                                         │
├─────────────────────────────────────────────────────────────────┤
│  [Create Periods]  [Cancel]                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PROCESSING                                                     │
├─────────────────────────────────────────────────────────────────┤
│  1. Check existing periods                                      │
│  2. Skip duplicates                                             │
│  3. Create new periods                                          │
│  4. Calculate amounts                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  RESULT                                                         │
├─────────────────────────────────────────────────────────────────┤
│  ✓ Period Creation Complete!                                   │
│                                                                 │
│  Created: 13 period(s)                                         │
│  Skipped: 0 (already exist)                                    │
│                                                                 │
│  Target per period: 92,308                                     │
│  Cost per period: 18,462                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Decision Tree

```
START
  ↓
┌─────────────────────┐
│ Select Target Type  │
└─────────────────────┘
  ↓
  ├─→ Project?         → Select Project
  └─→ Marketing?       → Select Marketing Account
  ↓
┌─────────────────────┐
│ Select Year         │
└─────────────────────┘
  ↓
┌─────────────────────┐
│ Period Options?     │
└─────────────────────┘
  ↓
  ├─→ Yearly Only?     → Create 1 period (YYYY00)
  ├─→ Monthly Only?    → Create 12 periods (YYYY01-12)
  └─→ Both?            → Create 13 periods
  ↓
  │ If Monthly...
  └─→ All months?      → All 12
      └─→ Specific?    → Select individual months
  ↓
┌─────────────────────┐
│ Enter Target Amount │
└─────────────────────┘
  ↓
┌─────────────────────┐
│ Distribution?       │
└─────────────────────┘
  ↓
  ├─→ Same Value?      → Each period gets full amount
  └─→ Distribute?      → Split amount evenly
  ↓
┌─────────────────────┐
│ Cost Calculation?   │
└─────────────────────┘
  ↓
  ├─→ Percentage?      → Auto-calculate from target
  │    ↓
  │    Enter %         → Cost = Target × %
  │
  └─→ Manual?          → Enter exact cost amount
  ↓
┌─────────────────────┐
│ Review Preview      │
└─────────────────────┘
  ↓
  OK? ─No→ Adjust settings
  ↓ Yes
┌─────────────────────┐
│ Create Periods      │
└─────────────────────┘
  ↓
  For each period:
    ├─→ Already exists? → Skip
    └─→ New?            → Create with calculated values
  ↓
┌─────────────────────┐
│ Show Results        │
└─────────────────────┘
  ↓
END
```

## Cost Calculation Logic

```
┌─────────────────────────────────────────────────────┐
│  COST CALCULATION FLOW                              │
└─────────────────────────────────────────────────────┘

IF cost_calculation_type == 'percentage':
  ↓
  cost_amount = target_amount × (cost_percentage / 100)
  ↓
  Example: 100,000 × (20 / 100) = 20,000
  ↓
  [Auto-updated when target or % changes]

ELSE IF cost_calculation_type == 'manual':
  ↓
  cost_amount = [User enters directly]
  ↓
  Example: User types 15,000
  ↓
  [No auto-calculation]
```

## Distribution Logic

```
┌─────────────────────────────────────────────────────┐
│  DISTRIBUTION CALCULATION                           │
└─────────────────────────────────────────────────────┘

IF distribution_type == 'same':
  ↓
  per_period_target = target_amount (full amount)
  per_period_cost = cost_amount (full amount)
  ↓
  Example:
    Target: 50,000
    Cost: 10,000
    → Each of 12 periods: 50,000 target, 10,000 cost
    Total: 600,000 target, 120,000 cost

ELSE IF distribution_type == 'distribute':
  ↓
  per_period_target = target_amount / number_of_periods
  per_period_cost = cost_amount / number_of_periods
  ↓
  Example:
    Target: 600,000
    Cost: 120,000
    Periods: 12
    → Each period: 50,000 target, 10,000 cost
    Total: 600,000 target, 120,000 cost
```

## Period Format Logic

```
┌─────────────────────────────────────────────────────┐
│  PERIOD CODE GENERATION                             │
└─────────────────────────────────────────────────────┘

Yearly Period:
  Format: YYYY00
  Example: 202600
  ↓
  year = "2026"
  period = year + "00"

Monthly Period:
  Format: YYYYMM
  Example: 202601 (January 2026)
  ↓
  year = "2026"
  month = 1..12
  period = year + month.toString().padStart(2, '0')
  ↓
  Results:
    202601 → January
    202602 → February
    ...
    202612 → December
```

## Example Scenarios

### Scenario 1: Annual Budget Split Monthly
```
Input:
  Target: Project "Water 2026"
  Year: 2026
  Periods: Monthly Only (all 12)
  Target: 1,200,000
  Cost: 20% → 240,000
  Distribution: Distribute Evenly

Output:
  12 periods created:
  202601: 100,000 / 20,000
  202602: 100,000 / 20,000
  ...
  202612: 100,000 / 20,000
```

### Scenario 2: Consistent Monthly Targets
```
Input:
  Target: Marketing "Facebook Ads"
  Year: 2026
  Periods: Monthly Only (all 12)
  Target: 50,000
  Cost: Manual → 8,000
  Distribution: Same Value

Output:
  12 periods created:
  202601: 50,000 / 8,000
  202602: 50,000 / 8,000
  ...
  202612: 50,000 / 8,000
  Total: 600,000 / 96,000
```

### Scenario 3: Seasonal Campaign
```
Input:
  Target: Project "Ramadan 2026"
  Year: 2026
  Periods: Monthly (Mar, Apr, May only)
  Target: 300,000
  Cost: 15% → 45,000
  Distribution: Distribute Evenly

Output:
  3 periods created:
  202603: 100,000 / 15,000
  202604: 100,000 / 15,000
  202605: 100,000 / 15,000
```

## Data Validation

```
Before Creating Periods:

1. ✓ Target selected?
   → Project OR Marketing Account must be chosen

2. ✓ At least one period type?
   → Yearly OR Monthly must be checked

3. ✓ If specific months, any selected?
   → At least one month if "Select Specific Months" is checked

4. ✓ Target > 0?
   → Target amount must be positive

5. ✓ Cost makes sense?
   → If percentage: 0-100 range
   → If manual: >= 0

6. ✓ Check for duplicates
   → Skip existing (target_object + period) combinations
```

## Technical Implementation

```
Database Schema:
  Table: mysdb_period_target_cost
  Fields:
    - period (Char 6): YYYYMM format
    - target_object (Reference): project or marketing account
    - target (Float): Target amount
    - cost (Float): Cost amount

Wizard Model:
  Name: mysdb.bulk.period.creation.wizard
  Type: TransientModel (temporary)
  
Key Methods:
  - _compute_cost_amount(): Auto-calc cost from percentage
  - _compute_preview_count(): Count periods to create
  - _compute_preview_text(): Generate preview display
  - action_create_periods(): Main creation logic

UI Components:
  - Radio buttons for target type
  - Dropdowns for selection
  - Checkboxes for period options
  - Dynamic month selector grid
  - Real-time preview panel
  - Action buttons
```

---

**Quick Reference**: See `BULK_PERIOD_CREATION_GUIDE.md` for detailed user instructions.

