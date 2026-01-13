# Simple XML validation for Windows
import xml.etree.ElementTree as ET
from pathlib import Path

MODULE_PATH = Path(__file__).parent

print("=" * 60)
print("Quick XML Validation Check")
print("=" * 60)
print()

xml_files = [
    'views/mysdb_data_views.xml',
    'views/mysdb_enhanced_views.xml',
    'views/mysdb_menus.xml',
    'security/security_rules.xml',
]

all_ok = True

for xml_file in xml_files:
    file_path = MODULE_PATH / xml_file
    if file_path.exists():
        try:
            ET.parse(file_path)
            print(f"[OK] {xml_file}")
        except ET.ParseError as e:
            print(f"[ERROR] {xml_file}: {e}")
            all_ok = False
    else:
        print(f"[MISSING] {xml_file}")

print()
if all_ok:
    print("=" * 60)
    print("ALL XML FILES ARE VALID!")
    print("You can proceed with upgrade.")
    print("=" * 60)
else:
    print("=" * 60)
    print("ERRORS FOUND - Please fix before upgrading")
    print("=" * 60)

