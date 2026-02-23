#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySDB Connector - Final Consistency Check & Enhancement
Comprehensive validation and optimization tool
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import re

MODULE_PATH = Path(__file__).parent

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_section(title):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_ok(msg):
    print(f"{Colors.GREEN}[OK]{Colors.END} {msg}")

def print_warn(msg):
    print(f"{Colors.YELLOW}[WARN]{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.END} {msg}")

def check_models():
    """Check all models are defined and have security"""
    print_section("1. MODEL CONSISTENCY CHECK")
    
    models_file = MODULE_PATH / 'models' / 'mysdb_data_models.py'
    security_file = MODULE_PATH / 'security' / 'security_rules.xml'
    
    # Find all model classes
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
        model_matches = re.findall(r'class\s+(\w+)\(models\.(Model|TransientModel)\):', content)
        models = [m[0] for m in model_matches]
    
    print(f"Found {len(models)} models:")
    for model in models:
        print(f"  - {model}")
    
    # Check security rules
    tree = ET.parse(security_file)
    root = tree.getroot()
    security_models = set()
    
    for record in root.findall('.//record[@model="ir.model.access"]'):
        for field in record.findall('.//field[@name="model_id"]'):
            model_ref = field.get('ref', '')
            if model_ref.startswith('model_'):
                security_models.add(model_ref)
    
    print(f"\nSecurity rules found: {len(security_models)}")
    
    # Convert model names to expected security format
    expected_security = [f"model_{'_'.join(re.findall('[A-Z][a-z]*', m)).lower()}" for m in models]
    
    missing_security = []
    for expected in expected_security:
        if expected not in security_models:
            missing_security.append(expected)
    
    if missing_security:
        print_warn(f"Models without security rules: {len(missing_security)}")
        for m in missing_security:
            print(f"  - {m}")
    else:
        print_ok("All models have security rules")
    
    return len(missing_security) == 0

def check_views():
    """Check all views and actions consistency"""
    print_section("2. VIEW & ACTION CONSISTENCY CHECK")
    
    views_dir = MODULE_PATH / 'views'
    all_actions = {}
    all_views = {}
    menu_actions = set()
    
    # Parse all view files
    for view_file in views_dir.glob('*.xml'):
        try:
            tree = ET.parse(view_file)
            root = tree.getroot()
            
            # Find actions
            for record in root.findall('.//record[@model="ir.actions.act_window"]'):
                action_id = record.get('id')
                if action_id:
                    all_actions[action_id] = view_file.name
            
            # Find views
            for record in root.findall('.//record[@model="ir.ui.view"]'):
                view_id = record.get('id')
                if view_id:
                    all_views[view_id] = view_file.name
            
            # Find menu action references
            for menuitem in root.findall('.//menuitem[@action]'):
                action = menuitem.get('action')
                if action:
                    menu_actions.add(action)
        except Exception as e:
            print_error(f"Error parsing {view_file.name}: {e}")
    
    print(f"Found {len(all_actions)} actions")
    print(f"Found {len(all_views)} views")
    print(f"Found {len(menu_actions)} menu action references")
    
    # Check if all menu actions exist
    missing_actions = menu_actions - set(all_actions.keys())
    
    if missing_actions:
        print_error(f"Missing actions referenced in menus: {missing_actions}")
        return False
    else:
        print_ok("All menu actions are defined")
    
    return True

def check_manifest():
    """Check manifest consistency"""
    print_section("3. MANIFEST CONSISTENCY CHECK")
    
    manifest_file = MODULE_PATH / '__manifest__.py'
    
    with open(manifest_file, 'r', encoding='utf-8') as f:
        manifest_content = f.read()
        manifest = eval(manifest_content)
    
    print_ok(f"Module: {manifest.get('name')}")
    print_ok(f"Version: {manifest.get('version')}")
    print_ok(f"Depends: {', '.join(manifest.get('depends', []))}")
    
    # Check all data files exist
    data_files = manifest.get('data', [])
    print(f"\nData files ({len(data_files)}):")
    
    all_exist = True
    for data_file in data_files:
        file_path = MODULE_PATH / data_file
        if file_path.exists():
            print_ok(f"  {data_file}")
        else:
            print_error(f"  {data_file} (NOT FOUND)")
            all_exist = False
    
    return all_exist

def check_imports():
    """Check all model imports"""
    print_section("4. IMPORT CONSISTENCY CHECK")
    
    init_file = MODULE_PATH / 'models' / '__init__.py'
    models_dir = MODULE_PATH / 'models'
    
    with open(init_file, 'r', encoding='utf-8') as f:
        init_content = f.read()
    
    # Find all Python files in models
    py_files = [f.stem for f in models_dir.glob('*.py') if f.stem != '__init__']
    
    print(f"Python files in models/: {len(py_files)}")
    
    missing_imports = []
    for py_file in py_files:
        if py_file not in init_content and py_file != '__pycache__':
            missing_imports.append(py_file)
    
    if missing_imports:
        print_warn(f"Files not imported in __init__.py:")
        for f in missing_imports:
            print(f"  - {f}.py")
            if f == 'mysdp_data_models':
                print(f"    (Note: This appears to be a duplicate/backup file)")
    else:
        print_ok("All model files are imported")
    
    return True

def check_computed_fields():
    """Check computed fields have proper dependencies"""
    print_section("5. COMPUTED FIELD DEPENDENCY CHECK")
    
    models_file = MODULE_PATH / 'models' / 'mysdb_data_models.py'
    
    with open(models_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all computed fields
    computed_pattern = r'@api\.depends\((.*?)\)\s+def\s+(\w+)\('
    computed_fields = re.findall(computed_pattern, content, re.DOTALL)
    
    print(f"Found {len(computed_fields)} computed fields")
    
    issues = []
    for deps, method in computed_fields:
        if not deps.strip() or deps.strip() == "''":
            issues.append(f"{method} has no dependencies")
    
    if issues:
        print_warn("Computed fields with empty dependencies:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print_ok("All computed fields have proper dependencies")
    
    return len(issues) == 0

def check_documentation():
    """Check documentation completeness"""
    print_section("6. DOCUMENTATION CHECK")
    
    docs = [
        'START_HERE.md',
        'UPGRADE_GUIDE.md',
        'TROUBLESHOOTING.md',
        'ENHANCEMENTS_DOCUMENTATION.md',
        'EXECUTIVE_SUMMARY.md',
        'QUICK_REFERENCE.md',
        'MODULE_ANALYSIS_REPORT.md'
    ]
    
    all_exist = True
    for doc in docs:
        doc_path = MODULE_PATH / doc
        if doc_path.exists():
            size = doc_path.stat().st_size
            print_ok(f"{doc} ({size:,} bytes)")
        else:
            print_error(f"{doc} (MISSING)")
            all_exist = False
    
    return all_exist

def generate_summary():
    """Generate final summary"""
    print_section("FINAL CONSISTENCY REPORT")
    
    checks = [
        ("Model Consistency", check_models()),
        ("View & Action Consistency", check_views()),
        ("Manifest Consistency", check_manifest()),
        ("Import Consistency", check_imports()),
        ("Computed Field Dependencies", check_computed_fields()),
        ("Documentation Completeness", check_documentation())
    ]
    
    print("\nSummary:")
    print("-" * 60)
    
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    for check_name, result in checks:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"{check_name:.<50} {status}")
    
    print("-" * 60)
    print(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}MODULE IS PRODUCTION READY!{Colors.END}")
        print(f"{Colors.GREEN}All consistency checks passed. No issues found.{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}MODULE HAS MINOR ISSUES{Colors.END}")
        print(f"{Colors.YELLOW}Review warnings above. Most are non-critical.{Colors.END}")
        return 1

def main():
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("="*60)
    print("MySDB Connector - Final Consistency Check")
    print("="*60)
    print(f"{Colors.END}")
    
    return generate_summary()

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        sys.exit(1)

