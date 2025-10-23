#!/usr/bin/env python3
"""
Caseboard Health Check Script

Verifies the integrity and setup of the Caseboard application.
"""

import json
import sys
from pathlib import Path
from collections import Counter


def check_python_version():
    """Check Python version is 3.8+"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python version {version.major}.{version.minor} is too old. Need 3.8+")
        return False


def check_data_file():
    """Check cases.json exists and is valid"""
    data_file = Path("data/cases.json")
    
    if not data_file.exists():
        print("✗ data/cases.json does not exist")
        return False
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        schema_version = data.get('schema_version', 1)
        cases = data.get('cases', [])
        
        print(f"✓ data/cases.json is valid JSON")
        print(f"  Schema version: {schema_version}")
        print(f"  Total cases: {len(cases)}")
        
        # Check for duplicate IDs
        ids = [c.get('id') for c in cases if c.get('id')]
        id_counts = Counter(ids)
        duplicates = [id_val for id_val, count in id_counts.items() if count > 1]
        
        if duplicates:
            print(f"  ✗ WARNING: Found {len(duplicates)} duplicate case IDs!")
            for dup_id in duplicates:
                print(f"    - {dup_id} appears {id_counts[dup_id]} times")
            return False
        else:
            print(f"  ✓ All case IDs are unique")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ data/cases.json is corrupted: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading data/cases.json: {e}")
        return False


def check_directories():
    """Check required directories exist"""
    dirs = [
        "data",
        "data/backups",
        "data/migrations",
        "caseboard",
        "web",
        "web/static",
    ]
    
    all_good = True
    for dir_path in dirs:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            print(f"✓ {dir_path}/ exists")
        else:
            print(f"✗ {dir_path}/ missing")
            all_good = False
    
    return all_good


def check_web_assets():
    """Check web assets are setup"""
    web_pngs = Path("web/static/pngs")
    
    if not web_pngs.exists():
        print("✗ web/static/pngs/ directory does not exist")
        print("  Run: python setup_web_assets.py")
        return False
    
    png_files = list(web_pngs.glob("*.png"))
    
    if len(png_files) == 0:
        print("✗ No PNG files found in web/static/pngs/")
        print("  Run: python setup_web_assets.py")
        return False
    
    print(f"✓ web/static/pngs/ contains {len(png_files)} PNG files")
    return True


def check_requirements():
    """Check if requirements.txt exists"""
    req_file = Path("requirements.txt")
    
    if not req_file.exists():
        print("✗ requirements.txt does not exist")
        return False
    
    with open(req_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"✓ requirements.txt exists ({len(lines)} packages)")
    return True


def check_entry_points():
    """Check entry point scripts exist"""
    scripts = [
        "run.py",
        "run_web.py",
        "run_display.py",
    ]
    
    all_good = True
    for script in scripts:
        path = Path(script)
        if path.exists():
            print(f"✓ {script} exists")
        else:
            print(f"✗ {script} missing")
            all_good = False
    
    return all_good


def main():
    """Run all health checks"""
    print("=" * 60)
    print("Caseboard Health Check")
    print("=" * 60)
    print()
    
    checks = [
        ("Python Version", check_python_version),
        ("Data File", check_data_file),
        ("Directory Structure", check_directories),
        ("Web Assets", check_web_assets),
        ("Requirements", check_requirements),
        ("Entry Points", check_entry_points),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        print("-" * 40)
        results.append(check_func())
    
    print()
    print("=" * 60)
    
    if all(results):
        print("✓ All checks passed! Caseboard is ready to use.")
        print()
        print("To start the application:")
        print("  Terminal UI:    python run.py")
        print("  Web Dashboard:  python run_web.py")
        print("  Display Board:  python run_display.py")
        return 0
    else:
        failed = sum(1 for r in results if not r)
        print(f"✗ {failed} check(s) failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
