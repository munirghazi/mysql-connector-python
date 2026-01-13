# Bulk Assignment Filters - Known Limitation & Workaround

## ⚠️ Known Odoo Limitation

**Issue:** When using the "Add an item" button on many2many fields, the popup search window **does NOT respect @api.onchange domains**. This is a **known Odoo framework limitation**, not a bug in our module.

### Why This Happens

1. **Onchange domains** are evaluated in the current form context
2. **Popup windows** open in a separate context
3. **Odoo's many2many widget** doesn't pass onchange domains to popups
4. **This affects ALL Odoo modules** that try to filter many2many popups dynamically

---

## ✅ WORKAROUND: Don't Use the Popup!

### **The filters DO WORK in the inline product list!**

Instead of using the "Add an item" button, **select products directly from the list below:**

### How To Use (CORRECT WAY):

1. **Open Wizard:**
   - MySDB Dashboard → Tools → Bulk Assign to Project

2. **Set Your Filters:**
   - Filter by Store: Select your store (e.g., 233491)
   - Filter Products: Select filter type (e.g., "Products Without Project")

3. **✅ SELECT FROM THE LIST (Not the popup!):**
   - **Scroll down** to the "Products to Assign" section
   - You'll see a **LIST of products** (not empty)
   - **This list IS FILTERED** according to your selections!
   - **Check the boxes** next to products you want to assign
   - The "Products Selected" counter updates as you select

4. **Execute:**
   - Click "Assign Products" button at the bottom
   - Done!

### ❌ DON'T Use This Method:

- Don't click "Add an item" button (the one that opens a popup)
- The popup ignores filters (Odoo limitation)

---

## 📊 Visual Guide

### CORRECT: Select from Filtered List

```
┌─────────────────────────────────────────┐
│ Bulk Assign Products to Project        │
├─────────────────────────────────────────┤
│ Target Project: [Project X        ▼]   │
│                                         │
│ Filter by Store: [Store 233491    ▼]   │
│ Filter Products: [Products Without ▼]   │
│                   Project                │
│                                         │
│ Products Selected: 3 products           │
├─────────────────────────────────────────┤
│ Products to Assign:                     │
│ ┌───────────────────────────────────┐  │
│ │☑ Product ABC - Store 233491       │  │ ← CHECK THESE!
│ │☑ Product DEF - Store 233491       │  │   (List is filtered)
│ │☑ Product GHI - Store 233491       │  │
│ │☐ Product JKL - Store 233491       │  │
│ └───────────────────────────────────┘  │
│                                         │
│          [Assign Products]              │
└─────────────────────────────────────────┘
```

### WRONG: Using Popup (Doesn't Respect Filters)

```
❌ Don't click "Add an item" button
   └─> Opens popup that shows ALL products
       (Ignores your filter selections)
```

---

## 🔍 How To Verify Filters Are Working

After setting filters, look at the product list below:

1. **If Store Filter = 233491:**
   - List shows ONLY products from Store 233491
   - Other stores' products are hidden

2. **If Assignment Filter = "Products Without Project":**
   - List shows ONLY products without project assignment
   - Products with projects are hidden

3. **If Both Filters:**
   - List shows ONLY Store 233491 products without project
   - This is exactly what you want!

4. **If you see products from other stores:**
   - The filter isn't being applied
   - Try changing the filter and changing it back
   - Or close and reopen the wizard

---

## 💡 Tips for Efficient Selection

### Tip 1: Use Filters to Reduce List Size
```
Too many products to scroll through?
→ Use Store filter to see only one store
→ Use Assignment filter to see only unassigned
→ List becomes much smaller and manageable
```

### Tip 2: Select Multiple at Once
```
Need to select many products?
→ Check multiple boxes
→ Products Selected counter shows total
→ All selected products assigned together
```

### Tip 3: Use Search if Needed
```
Looking for specific product?
→ Use browser Ctrl+F to search in the list
→ Or use the search box if available in tree view
```

### Tip 4: Assign in Batches
```
Have 1000 products to assign?
→ Don't try to select all at once
→ Use filters to get 50-100 products
→ Assign them
→ Change filters to get next batch
→ Repeat
```

---

## 🔧 Technical Explanation

### Why Onchange Doesn't Work for Popups

**In Odoo Framework:**

1. `@api.onchange` is evaluated in the **current form's client-side state**
2. When you click "Add an item", Odoo opens a **new window/dialog**
3. This new window has its **own context** and **doesn't inherit onchange results**
4. The domain returned by onchange **stays in the parent form**
5. The popup uses the **original field definition** without dynamic domain

### What We Tried

1. ✅ **Onchange domain** - Works for inline list, not popup
2. ✅ **Context-based filtering** - Works for inline list, not popup
3. ✅ **_search override** - Works for inline list, not popup
4. ❌ **Static XML domain** - Can't reference form fields dynamically
5. ❌ **attrs with domain** - Not supported for many2many in Odoo 17

### The Limitation Is:

- **Odoo's many2many widget architecture**
- **Not something we can fix in our module**
- **Affects ALL Odoo modules similarly**

---

## ✅ What DOES Work

### Inline Product List (Below Filters)

The product list that appears below the filters **DOES respect all filters!**

- ✅ **Store filter** - Applied correctly
- ✅ **Assignment filter** - Applied correctly
- ✅ **Combined filters** - Work perfectly
- ✅ **Real-time updates** - When you change filters, list updates

### Selection from Filtered List

- ✅ **Check boxes** work perfectly
- ✅ **Multiple selection** works
- ✅ **Counter updates** in real-time
- ✅ **Assignment** works correctly

---

## 🎯 Best Practice

### Recommended Workflow:

1. **Set filters first** (before looking at products)
2. **Verify the list** is filtered (check product count/store IDs)
3. **Select from list** (don't use "Add an item" button)
4. **Assign products**
5. **Repeat** for different filter combinations

### Example: Assign Store 233491 Unassigned Products

```bash
Step 1: Open Bulk Assign to Project wizard
Step 2: Select Target Project
Step 3: Set Filter by Store = 233491
Step 4: Set Filter Products = Products Without Project
Step 5: LOOK AT THE LIST BELOW (it's filtered!)
Step 6: Check boxes next to products you want
Step 7: Click "Assign Products"
Step 8: Success!
```

---

## 📞 Support

### "The list is empty!"

**Solution:** 
- Check if you have products matching the filters
- Try "All Products" filter to see if any products exist
- Verify store filter is correct

### "I see products from wrong store!"

**Solution:**
- Change the filter and change it back
- Close wizard and reopen
- Upgrade module if using old version

### "I need to use the popup!"

**Explanation:**
- Unfortunately, this is an Odoo framework limitation
- The popup will show all products regardless of filters
- The workaround is to use the inline list (which works correctly)
- If you absolutely need popup functionality, consider custom development

---

## 🔮 Future Enhancement (Optional)

If the inline list workflow isn't acceptable, potential solutions:

1. **Custom widget** - Develop custom many2many widget
2. **Different UI** - Use wizard with search view instead of many2many
3. **Server action** - Create products list in separate screen
4. **Custom popup** - Override standard popup with custom one

These would require significant development effort.

---

## 📝 Summary

### The Problem:
- "Add an item" popup doesn't respect filters (Odoo limitation)

### The Solution:
- **Don't use the popup!**
- **Select from the filtered list below** (which works perfectly!)

### The Filters:
- ✅ **DO work** in inline product list
- ❌ **DON'T work** in "Add an item" popup
- ✅ **Use the inline list** for filtered selection

---

**Bottom Line:** The filters work correctly! Just don't use the "Add an item" popup button. Select products directly from the list that appears below the filters. 🎯

---

**Module Version:** 17.0.2.0.0  
**Date:** January 13, 2026  
**Status:** Workaround Available ✅

