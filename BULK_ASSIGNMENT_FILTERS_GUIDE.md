# Bulk Assignment Wizards - Filter Usage Guide

## ✅ Confirmation: Filters are WORKING

Both **Bulk Assign to Project** and **Bulk Assign to Marketing** wizards have fully functional filters that dynamically update the product list based on your selection.

---

## 📋 Available Filters

### 1. Filter by Store
**Field:** `Filter by Store`  
**Type:** Dropdown selection  
**Purpose:** Shows only products from a specific store

### 2. Filter Products
**Field:** `Filter Products`  
**Type:** Radio buttons / Selection  
**Options:**
- **All Products** - Shows all products (no filtering)
- **Products Without Project** - Shows only unassigned products
- **Products Without Complete Assignment** - Shows products with partial or no assignment

---

## 🎯 How to Use the Filters

### Bulk Assign to Project Wizard

**Access:** MySDB Dashboard → Tools → Bulk Assign to Project

#### Step-by-Step Instructions:

1. **Open the Wizard**
   - Click on "MySDB Dashboard" menu
   - Navigate to "Tools" → "Bulk Assign to Project"
   - A popup form will appear

2. **Select Target Project**
   - In the "Target" section, select the project you want to assign products to
   - This is a **required** field

3. **Apply Filters** (Optional but Recommended)
   
   **Option A: Filter by Store**
   - Click on the "Filter by Store" dropdown
   - Select a store (e.g., "Store A", "Store B")
   - **Effect:** The product list below will automatically update to show only products from that store
   - **Benefit:** Prevents store mismatch errors (products and project must be from the same store)

   **Option B: Filter by Assignment Status**
   - Look at the "Filter Products" field
   - Choose one of:
     - **"All Products"** - Shows every product in the system
     - **"Products Without Project"** ⭐ (Default) - Shows only products not yet assigned to any project
     - **"Products Without Complete Assignment"** - Shows products that are missing either project OR marketing assignment
   - **Effect:** The product list updates immediately

   **Option C: Combine Both Filters**
   - Select a store: "Store A"
   - Select filter: "Products Without Project"
   - **Result:** Shows only unassigned products from Store A

4. **Select Products**
   - Scroll through the filtered product list in the "Products to Assign" tab
   - Click checkboxes next to products you want to assign
   - The "Products Selected" counter updates in real-time
   - You can select multiple products at once

5. **Choose Assignment Behavior** (Optional)
   - Check "Replace Existing Project Assignment" if you want to:
     - **Replace** existing project assignments
   - Leave unchecked (default) to:
     - **Skip** products that already have a project assigned

6. **Execute Assignment**
   - Click the "Assign to Project" button at the bottom
   - System validates store consistency
   - Shows success notification with results:
     - Created: X (new assignments)
     - Updated: X (replaced assignments)
     - Skipped: X (already assigned)

---

### Bulk Assign to Marketing Wizard

**Access:** MySDB Dashboard → Tools → Bulk Assign to Marketing

#### Step-by-Step Instructions:

1. **Open the Wizard**
   - Click on "MySDB Dashboard" menu
   - Navigate to "Tools" → "Bulk Assign to Marketing"
   - A popup form will appear

2. **Select Target Marketing Account**
   - In the "Target" section, select the marketing account
   - This is a **required** field

3. **Apply Filters** (Same as Project Wizard)

   **Option A: Filter by Store**
   - Click "Filter by Store" dropdown
   - Select a store
   - **Effect:** Shows only products from that store

   **Option B: Filter by Assignment Status**
   - Choose from "Filter Products":
     - **"All Products"** - Shows all products
     - **"Products Without Marketing"** ⭐ (Default) - Shows only products not assigned to any marketing account
     - **"Products Without Complete Assignment"** - Shows products missing project OR marketing assignment
   - **Effect:** Product list updates automatically

   **Option C: Combine Both Filters**
   - Select store + assignment status
   - **Result:** Highly targeted product list

4. **Select Products**
   - Review the filtered product list
   - Select products using checkboxes
   - "Products Selected" counter shows your selection

5. **Execute Assignment**
   - Click "Assign to Marketing" button
   - Shows success notification with:
     - Created: X (new assignments)
     - Skipped: X (already assigned to this account)

---

## 🔍 Filter Behavior Details

### How Filters Work

**Dynamic Filtering:**
- Filters use `@api.onchange` decorator
- Product list updates **instantly** when you change filter values
- No need to click "Apply" or "Search" - it's automatic!

**Filter Logic:**

```python
# Store Filter
if store_id selected:
    Show only products where product.store_id = selected_store

# Assignment Filter = "Products Without Project"
Show products where has_project = False

# Assignment Filter = "Products Without Complete Assignment"
Show products where assignment_status in ['partial', 'none']

# Both Filters Combined (AND logic)
Show products that match BOTH conditions
```

### Filter Field Mappings

| Filter Option | Database Condition | Description |
|---------------|-------------------|-------------|
| **All Products** | (no filter) | Shows everything |
| **Products Without Project** | `has_project = False` | No project relation exists |
| **Products Without Marketing** | `has_marketing = False` | No marketing relation exists |
| **Products Without Complete Assignment** | `assignment_status IN ('partial', 'none')` | Missing one or both assignments |

---

## 💡 Best Practices & Tips

### Recommended Workflow

1. **Always use Store filter first**
   - Prevents store mismatch errors
   - Reduces product list to manageable size
   - Ensures data consistency

2. **Use "Products Without..." filters**
   - Focuses on products that need attention
   - Avoids trying to assign already-assigned products
   - Faster selection process

3. **Check the "Products Selected" counter**
   - Verifies you've selected the right number
   - Prevents accidental bulk operations
   - Gives preview before committing

### Common Use Cases

#### Use Case 1: Assign all unassigned products from Store A to Project X
```
Steps:
1. Select Target Project: "Project X"
2. Filter by Store: "Store A"
3. Filter Products: "Products Without Project"
4. Select All visible products
5. Click "Assign to Project"
```

#### Use Case 2: Fix products with partial assignments
```
Steps:
1. Filter Products: "Products Without Complete Assignment"
2. Review each product's status
3. Assign to appropriate project/marketing
4. Re-run filter to verify completion
```

#### Use Case 3: Reassign products to different project
```
Steps:
1. Filter by Store: Select relevant store
2. Filter Products: "All Products" (to see already assigned ones)
3. Select products to reassign
4. Check "Replace Existing Project Assignment"
5. Click "Assign to Project"
```

---

## 🚨 Important Notes

### Store Consistency Validation

**For Project Assignment:**
- System validates that product.store_id matches project.store_id
- If mismatch detected, shows error:
  ```
  Store Mismatch!
  Product 'ABC' belongs to Store: STORE_A
  Project 'XYZ' belongs to Store: STORE_B
  Please ensure all products belong to the same store as the project.
  ```
- **Solution:** Use Store filter to avoid this issue

**For Marketing Assignment:**
- No strict store validation (marketing can be cross-store)
- But recommended to keep consistent for reporting

### Assignment Behavior

**Project Assignment:**
- Default: Skip products with existing project
- With "Replace Existing": Updates the project relation
- Creates new relation if none exists

**Marketing Assignment:**
- Always skips if product-account combination already exists
- One product can have multiple marketing accounts
- No "replace" option (not needed for many-to-many relation)

---

## 🐛 Troubleshooting

### Filter Not Working?

**Issue:** Product list doesn't update when changing filters

**Solutions:**
1. **Check Odoo version:** Ensure you're on Odoo 17.0+
2. **Clear browser cache:** Press Ctrl+F5
3. **Check module upgrade:** Ensure module is upgraded to v17.0.2.0.0
4. **Check JavaScript console:** Look for errors (F12 in browser)

### No Products Showing?

**Issue:** Filter shows 0 products

**Possible Reasons:**
1. **All products already assigned** - Try "All Products" filter
2. **Wrong store selected** - Try different store or no store filter
3. **No products exist** - Import products from MySQL first
4. **Data audit needed** - Run Data Maintenance Audit report

### Store Mismatch Error?

**Issue:** Error when trying to assign

**Solutions:**
1. **Use Store filter** - Select the same store as your project
2. **Check project store** - Go to Projects menu, verify store
3. **Check product store** - Go to Products menu, verify store
4. **Fix data** - Update product or project store if incorrect

---

## 📊 Filter Performance

### Expected Performance

| Data Size | Filter Response Time |
|-----------|---------------------|
| < 1,000 products | Instant (<100ms) |
| 1,000 - 10,000 products | Fast (<500ms) |
| 10,000 - 100,000 products | Good (<2s) |
| > 100,000 products | May need optimization |

### Performance Tips

1. **Use Store filter first** - Reduces dataset size
2. **Use assignment filters** - Further reduces list
3. **Select in batches** - Don't try to assign 10,000 products at once
4. **Close other browser tabs** - Frees up memory
5. **Use pagination** - Odoo automatically paginates large lists

---

## 🎓 Advanced Tips

### Keyboard Shortcuts

- **Ctrl+Click** - Select multiple non-consecutive products
- **Shift+Click** - Select range of products
- **Ctrl+A** - Select all visible products (if list focused)

### Data Audit Integration

Use the Data Maintenance Audit report to identify products needing assignment:

1. Go to: MySDB Dashboard → Reporting → Data Maintenance Audit
2. Filter by: "Unassigned to Project" or "Unassigned to Marketing"
3. Sort by: "Priority" (shows highest-value products first)
4. Click product name → Opens product form
5. Use "Products" menu in product form to bulk assign

### Bulk Re-assignment Strategy

To reassign many products efficiently:

1. **Export current assignments** (optional backup)
2. **Use "All Products" filter** to see current state
3. **Filter by Store** to ensure consistency
4. **Select products** to reassign
5. **Check "Replace Existing"** option
6. **Assign to new project**
7. **Verify in Data Audit** report

---

## 📞 Support

If filters are not working as expected:

1. **Check this guide** - Ensure you're using filters correctly
2. **Run consistency check** - Execute `FINAL_CONSISTENCY_CHECK.py`
3. **Check module version** - Must be v17.0.2.0.0+
4. **Review TROUBLESHOOTING.md** - Common issues and solutions
5. **Check Odoo logs** - Look for errors in odoo.log

---

## ✅ Quick Reference Card

### Bulk Assign to Project

| What I Want | Store Filter | Product Filter | Replace Option |
|-------------|--------------|----------------|----------------|
| Assign new products | Specific Store | Products Without Project | OFF |
| Reassign existing | Specific Store | All Products | ON |
| Fix partial assigns | Any | Without Complete Assignment | OFF |
| Bulk reassignment | Specific Store | All Products | ON |

### Bulk Assign to Marketing

| What I Want | Store Filter | Product Filter |
|-------------|--------------|----------------|
| Assign new products | Specific Store | Products Without Marketing |
| Add 2nd marketing | Any | All Products |
| Fix partial assigns | Any | Without Complete Assignment |

---

**Module Version:** 17.0.2.0.0  
**Last Updated:** January 13, 2026  
**Status:** Fully Functional ✅

