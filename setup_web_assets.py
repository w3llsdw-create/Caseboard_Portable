#!/usr/bin/env python3
"""Setup script to prepare web assets for the Caseboard web dashboard."""

import shutil
from pathlib import Path

def setup_web_assets():
    """Copy PNG assets to web/static/pngs directory."""
    
    base_dir = Path(__file__).parent
    source_dir = base_dir / "pngs"
    target_dir = base_dir / "web" / "static" / "pngs"
    
    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print("Setting up web assets...")
    
    # Copy all PNG files from source to target
    if source_dir.exists():
        copied_count = 0
        for png_file in source_dir.rglob("*.png"):
            target_file = target_dir / png_file.name
            if not target_file.exists():
                shutil.copy2(png_file, target_file)
                copied_count += 1
                print(f"  Copied: {png_file.name}")
        
        if copied_count == 0:
            print("  All PNG files already present in web/static/pngs/")
        else:
            print(f"  ✓ Copied {copied_count} PNG files to web/static/pngs/")
    else:
        print(f"  Warning: Source directory {source_dir} not found")
    
    # Check for required branded files
    required_files = [
        "McMathWoods_M_Brandmark_Copper.png",
        "McMathWoods_Seal_Copper.png"
    ]
    
    missing_files = [f for f in required_files if not (target_dir / f).exists()]
    
    if missing_files:
        print("\n  Note: The following branded files are referenced in the web dashboard")
        print("        but not found in the pngs directory:")
        for f in missing_files:
            print(f"        - {f}")
        print("\n  To use proper branding, rename appropriate PNG files from the pngs/")
        print("  directory to match these names, or update web/static/index.html")
    else:
        print("\n  ✓ All required branded files are present")
    
    print("\n✓ Web asset setup complete!")

if __name__ == "__main__":
    setup_web_assets()
