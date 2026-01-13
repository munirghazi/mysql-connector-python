#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySDB Connector - File Validation Script
This script validates all files before upgrade to catch common errors
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")

# Get module path
MODULE_PATH = Path(__file__).parent

def validate_python_syntax():
    """Validate Python files for syntax errors"""
    print_header("Validating Python Files")
    
    python_files = [
        MODULE_PATH / 'models' / 'mysdb_data_models.py',
        MODULE_PATH / 'models' / 'mysdb_connector.py',
        MODULE_PATH / 'models' / 'mysdb_credential.py',
    ]
    
    errors = []
    for py_file in python_files:
        if py_file.exists():
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    compile(f.read(), py_file.name, 'exec')
                print_success(f"{py_file.name} - Syntax OK")
            except SyntaxError as e:
                errors.append(f"{py_file.name}: {e}")
                print_error(f"{py_file.name} - Syntax Error: {e}")
        else:
            print_warning(f"{py_file.name} - File not found")
    
    return errors

def validate_xml_syntax():
    """Validate XML files for syntax errors"""
    print_header("Validating XML Files")
    
    xml_files = [
        MODULE_PATH / 'views' / 'mysdb_data_views.xml',
        MODULE_PATH / 'views' / 'mysdb_enhanced_views.xml',
        MODULE_PATH / 'views' / 'mysdb_menus.xml',
        MODULE_PATH / 'views' / 'mysdb_credential_views.xml',
        MODULE_PATH / 'views' / 'mysdb_connector_views.xml',
        MODULE_PATH / 'security' / 'security_rules.xml',
    ]
    
    errors = []
    for xml_file in xml_files:
        if xml_file.exists():
            try:
                ET.parse(xml_file)
                print_success(f"{xml_file.name} - Syntax OK")
            except ET.ParseError as e:
                errors.append(f"{xml_file.name}: {e}")
                print_error(f"{xml_file.name} - Parse Error: {e}")
        else:
            print_warning(f"{xml_file.name} - File not found")
    
    return errors

def check_manifest():
    """Check __manifest__.py"""
    print_header("Validating Manifest")
    
    manifest_file = MODULE_PATH / '__manifest__.py'
    
    if not manifest_file.exists():
        print_error("__manifest__.py not found!")
        return ["Manifest file not found"]
    
    try:
        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest_content = f.read()
            manifest_dict = eval(manifest_content)
        
        print_success("Manifest syntax OK")
        print_info(f"Module Name: {manifest_dict.get('name')}")
        print_info(f"Version: {manifest_dict.get('version')}")
        print_info(f"Data files: {len(manifest_dict.get('data', []))}")
        
        # Check if enhanced_views.xml is in data
        data_files = manifest_dict.get('data', [])
        if 'views/mysdb_enhanced_views.xml' in data_files:
            print_success("Enhanced views file is in manifest")
        else:
            print_error("Enhanced views file NOT in manifest!")
            return ["Enhanced views not in manifest"]
        
        return []
        
    except Exception as e:
        print_error(f"Manifest error: {e}")
        return [f"Manifest error: {e}"]

def check_action_references():
    """Check that all action references in menus exist in views"""
    print_header("Validating Action References")
    
    # Parse menus file
    menus_file = MODULE_PATH / 'views' / 'mysdb_menus.xml'
    if not menus_file.exists():
        print_warning("Menus file not found")
        return []
    
    try:
        tree = ET.parse(menus_file)
        root = tree.getroot()
        
        # Get all action references from menuitem elements
        actions_in_menus = set()
        for menuitem in root.findall('.//menuitem[@action]'):
            action = menuitem.get('action')
            if action:
                actions_in_menus.add(action)
        
        print_info(f"Found {len(actions_in_menus)} action references in menus")
        
        # Parse all view files to find action definitions
        view_files = [
            MODULE_PATH / 'views' / 'mysdb_data_views.xml',
            MODULE_PATH / 'views' / 'mysdb_enhanced_views.xml',
            MODULE_PATH / 'views' / 'mysdb_credential_views.xml',
            MODULE_PATH / 'views' / 'mysdb_connector_views.xml',
        ]
        
        defined_actions = set()
        for view_file in view_files:
            if view_file.exists():
                try:
                    tree = ET.parse(view_file)
                    root = tree.getroot()
                    for record in root.findall('.//record[@model="ir.actions.act_window"]'):
                        action_id = record.get('id')
                        if action_id:
                            defined_actions.add(action_id)
                except Exception as e:
                    print_warning(f"Could not parse {view_file.name}: {e}")
        
        print_info(f"Found {len(defined_actions)} action definitions")
        
        # Check for missing actions
        missing_actions = actions_in_menus - defined_actions
        
        if missing_actions:
            print_error(f"Missing action definitions: {missing_actions}")
            return [f"Missing actions: {', '.join(missing_actions)}"]
        else:
            print_success("All menu actions are defined!")
            return []
            
    except Exception as e:
        print_error(f"Error checking actions: {e}")
        return [f"Action check error: {e}"]

def check_security_access():
    """Check that all models have security access defined"""
    print_header("Validating Security Access")
    
    security_file = MODULE_PATH / 'security' / 'security_rules.xml'
    if not security_file.exists():
        print_warning("Security file not found")
        return []
    
    try:
        tree = ET.parse(security_file)
        root = tree.getroot()
        
        # Get all model access records
        model_accesses = set()
        for record in root.findall('.//record[@model="ir.model.access"]'):
            for field in record.findall('.//field[@name="model_id"]'):
                model_ref = field.get('ref')
                if model_ref:
                    model_accesses.add(model_ref)
        
        print_info(f"Found {len(model_accesses)} model access records")
        
        # Check for new models
        required_models = [
            'model_mysdb_project_income_report',
            'model_mysdb_marketing_income_report',
            'model_mysdb_bulk_assign_project_wizard',
            'model_mysdb_bulk_assign_marketing_wizard',
        ]
        
        missing = []
        for model in required_models:
            if model in model_accesses:
                print_success(f"{model} - Access defined")
            else:
                print_error(f"{model} - Access NOT defined")
                missing.append(model)
        
        if missing:
            return [f"Missing security access for: {', '.join(missing)}"]
        else:
            return []
            
    except Exception as e:
        print_error(f"Error checking security: {e}")
        return [f"Security check error: {e}"]

def main():
    print_header("MySDB Connector v2.0 - File Validation")
    
    all_errors = []
    
    # Run all validations
    all_errors.extend(validate_python_syntax())
    all_errors.extend(validate_xml_syntax())
    all_errors.extend(check_manifest())
    all_errors.extend(check_action_references())
    all_errors.extend(check_security_access())
    
    # Summary
    print_header("Validation Summary")
    
    if all_errors:
        print_error(f"Found {len(all_errors)} error(s):")
        for i, error in enumerate(all_errors, 1):
            print(f"  {i}. {error}")
        print()
        print_error("❌ Validation FAILED - Please fix errors before upgrading")
        return 1
    else:
        print_success("✅ All validations PASSED!")
        print()
        print_info("Module is ready for upgrade.")
        print_info("Run: python odoo-bin -u odoo_mysql_connector -d YOUR_DATABASE")
        return 0

if __name__ == '__main__':
    sys.exit(main())

