# Odoo 17 Syntax Changes - Quick Reference

## Overview

Odoo 17 deprecated the `attrs` and `states` attributes in XML views. This document shows the old vs. new syntax.

## Key Changes

### 1. The `attrs` Attribute is Removed

**Odoo 16 and Earlier:**
```xml
<field name="field_name" attrs="{'invisible': [('other_field', '=', False)]}"/>
```

**Odoo 17:**
```xml
<field name="field_name" invisible="not other_field"/>
```

## Syntax Conversion Guide

### Invisible Attribute

| Odoo 16 (OLD) | Odoo 17 (NEW) |
|---------------|---------------|
| `attrs="{'invisible': [('field', '=', False)]}"` | `invisible="not field"` |
| `attrs="{'invisible': [('field', '=', True)]}"` | `invisible="field"` |
| `attrs="{'invisible': [('field', '!=', 'value')]}"` | `invisible="field != 'value'"` |
| `attrs="{'invisible': [('field', '=', 'value')]}"` | `invisible="field == 'value'"` |
| `attrs="{'invisible': ['|', ('a', '=', False), ('b', '=', False)]}"` | `invisible="not a or not b"` |
| `attrs="{'invisible': [('a', '=', False), ('b', '=', False)]}"` | `invisible="not a and not b"` |

### Required Attribute

| Odoo 16 (OLD) | Odoo 17 (NEW) |
|---------------|---------------|
| `attrs="{'required': [('field', '=', True)]}"` | `required="field"` |
| `attrs="{'required': [('field', '=', 'value')]}"` | `required="field == 'value'"` |
| `attrs="{'required': [('field', '!=', False)]}"` | `required="field"` |

### Readonly Attribute

| Odoo 16 (OLD) | Odoo 17 (NEW) |
|---------------|---------------|
| `attrs="{'readonly': [('field', '=', True)]}"` | `readonly="field"` |
| `attrs="{'readonly': [('field', '=', 'value')]}"` | `readonly="field == 'value'"` |
| `attrs="{'readonly': [('field', '!=', False)]}"` | `readonly="field"` |

## Logical Operators

### AND Operator

**Odoo 16:**
```xml
attrs="{'invisible': [('field_a', '=', False), ('field_b', '=', False)]}"
```

**Odoo 17:**
```xml
invisible="not field_a and not field_b"
```

### OR Operator

**Odoo 16:**
```xml
attrs="{'invisible': ['|', ('field_a', '=', False), ('field_b', '=', False)]}"
```

**Odoo 17:**
```xml
invisible="not field_a or not field_b"
```

### Complex Conditions

**Odoo 16:**
```xml
attrs="{'invisible': ['|', '&', ('a', '=', True), ('b', '=', False), ('c', '=', 'value')]}"
```

**Odoo 17:**
```xml
invisible="(a and not b) or c == 'value'"
```

## Real Examples from Our Module

### Example 1: Project ID Field

**Before (Odoo 16):**
```xml
<field name="project_id" 
       attrs="{'invisible': [('target_type', '!=', 'project')], 
               'required': [('target_type', '=', 'project')]}"/>
```

**After (Odoo 17):**
```xml
<field name="project_id" 
       invisible="target_type != 'project'" 
       required="target_type == 'project'"/>
```

### Example 2: Marketing Account Field

**Before (Odoo 16):**
```xml
<field name="marketing_account_id" 
       attrs="{'invisible': [('target_type', '!=', 'marketing')], 
               'required': [('target_type', '=', 'marketing')]}"/>
```

**After (Odoo 17):**
```xml
<field name="marketing_account_id" 
       invisible="target_type != 'marketing'" 
       required="target_type == 'marketing'"/>
```

### Example 3: Specific Months Checkbox

**Before (Odoo 16):**
```xml
<field name="select_specific_months" 
       attrs="{'invisible': [('create_monthly', '=', False)]}"/>
```

**After (Odoo 17):**
```xml
<field name="select_specific_months" 
       invisible="not create_monthly"/>
```

### Example 4: Group with Multiple Conditions

**Before (Odoo 16):**
```xml
<group string="Select Specific Months" 
       attrs="{'invisible': ['|', ('create_monthly', '=', False), 
                                 ('select_specific_months', '=', False)]}">
```

**After (Odoo 17):**
```xml
<group string="Select Specific Months" 
       invisible="not create_monthly or not select_specific_months">
```

### Example 5: Cost Percentage Field

**Before (Odoo 16):**
```xml
<field name="cost_percentage" 
       attrs="{'invisible': [('cost_calculation_type', '!=', 'percentage')], 
               'required': [('cost_calculation_type', '=', 'percentage')]}"
       widget="percentage"/>
```

**After (Odoo 17):**
```xml
<field name="cost_percentage" 
       invisible="cost_calculation_type != 'percentage'" 
       required="cost_calculation_type == 'percentage'"
       widget="percentage"/>
```

### Example 6: Cost Amount Field (Readonly)

**Before (Odoo 16):**
```xml
<field name="cost_amount" 
       widget="monetary"
       attrs="{'readonly': [('cost_calculation_type', '=', 'percentage')]}"/>
```

**After (Odoo 17):**
```xml
<field name="cost_amount" 
       widget="monetary"
       readonly="cost_calculation_type == 'percentage'"/>
```

## Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal to | `field == 'value'` |
| `!=` | Not equal to | `field != 'value'` |
| `>` | Greater than | `field > 100` |
| `<` | Less than | `field < 100` |
| `>=` | Greater or equal | `field >= 100` |
| `<=` | Less or equal | `field <= 100` |
| `in` | In list | `field in ['a', 'b']` |
| `not in` | Not in list | `field not in ['a', 'b']` |

## Boolean Fields

For boolean fields, use simple references:

| Condition | Odoo 17 Syntax |
|-----------|----------------|
| Field is True | `invisible="field"` |
| Field is False | `invisible="not field"` |
| Field is checked | `required="field"` |
| Field is unchecked | `required="not field"` |

## String Comparisons

```xml
<!-- Check if field equals a string -->
<field name="example" invisible="my_field == 'draft'"/>

<!-- Check if field is in a list -->
<field name="example" invisible="my_field in ['draft', 'pending']"/>
```

## Numeric Comparisons

```xml
<!-- Greater than -->
<field name="example" invisible="amount > 1000"/>

<!-- Less than or equal -->
<field name="example" required="quantity <= 10"/>

<!-- Between values -->
<field name="example" readonly="price >= 100 and price <= 500"/>
```

## Tips and Best Practices

1. **Use parentheses** for complex conditions: `(a and b) or c`
2. **Quote string values**: `field == 'value'`
3. **Use `not` for negation**: `not field` instead of `field == False`
4. **Combine conditions clearly**: `field1 and field2` is more readable than complex nesting
5. **Test thoroughly**: Syntax errors in these attributes can break forms

## Common Mistakes

### ❌ Wrong
```xml
<!-- Old Odoo 16 syntax -->
<field name="example" attrs="{'invisible': [('field', '=', False)]}"/>
```

### ✅ Correct
```xml
<!-- New Odoo 17 syntax -->
<field name="example" invisible="not field"/>
```

### ❌ Wrong
```xml
<!-- Missing quotes around string value -->
<field name="example" invisible="field == draft"/>
```

### ✅ Correct
```xml
<!-- Quotes around string value -->
<field name="example" invisible="field == 'draft'"/>
```

### ❌ Wrong
```xml
<!-- Using old domain syntax -->
<field name="example" invisible="[('field', '=', True)]"/>
```

### ✅ Correct
```xml
<!-- Simple boolean reference -->
<field name="example" invisible="field"/>
```

## Migration Checklist

When migrating from Odoo 16 to 17:

- [ ] Search for all `attrs=` in XML files
- [ ] Convert `invisible` conditions
- [ ] Convert `required` conditions
- [ ] Convert `readonly` conditions
- [ ] Test all dynamic field visibility
- [ ] Test all required field validation
- [ ] Test all readonly field behavior

## Error Messages

If you see this error:
```
Since 17.0, the "attrs" and "states" attributes are no longer used.
```

You have an unconverted `attrs` or `states` attribute in your XML view.

## Tools for Migration

Use find/replace patterns:
- Find: `attrs="{'invisible':`
- Review each occurrence
- Convert to new syntax manually (automated conversion is risky)

## References

- [Odoo 17 Official Documentation](https://www.odoo.com/documentation/17.0/)
- [Odoo 17 Upgrade Notes](https://github.com/odoo/odoo/blob/17.0/UPGRADE.md)

---

**Last Updated:** January 2026  
**Module:** odoo_mysql_connector  
**Odoo Version:** 17.0

