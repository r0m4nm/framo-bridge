#!/usr/bin/env python3
"""
Package script for creating distribution-ready zip of Framo Bridge addon.

Usage:
    python package.py

This will create a 'framo-exporter-v{version}.zip' in the parent directory.
"""

import os
import zipfile
import json
from pathlib import Path

# Files to include in distribution
INCLUDE_FILES = [
    "__init__.py",
    "decimation.py",
    "dependencies.py",
    "material_analyzer.py",
    "texture_analyzer.py",
    "uv_unwrap.py",
    "test_viewer.html",
    "README.md",
    "INSTALL.md",
    "CHANGELOG.md",
    "LICENSE",
]

INCLUDE_DIRS = [
    "icons",
]

# Files/dirs to exclude
EXCLUDE = [
    "__pycache__",
    ".git",
    ".gitignore",
    ".guides",
    ".plans",
    "*.pyc",
    "*.pyo",
    "*.zip",
    "package.py",  # Don't include this script
]

def get_version():
    """Extract version from __init__.py bl_info"""
    init_file = Path(__file__).parent / "__init__.py"
    with open(init_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '"version"' in line:
                # Extract version tuple like (0, 2, 0)
                import re
                match = re.search(r'\((\d+),\s*(\d+),\s*(\d+)\)', line)
                if match:
                    return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
    return "0.0.0"

def should_exclude(path):
    """Check if path should be excluded"""
    path_str = str(path)
    for pattern in EXCLUDE:
        if pattern.startswith("*."):
            if path_str.endswith(pattern[1:]):
                return True
        elif pattern in path_str:
            return True
    return False

def create_package():
    """Create distribution zip package"""
    # Get current directory (addon root)
    addon_dir = Path(__file__).parent
    addon_name = addon_dir.name

    # Get version
    version = get_version()

    # Create zip filename
    zip_filename = f"{addon_name}-v{version}.zip"
    zip_path = addon_dir.parent / zip_filename

    print(f"Creating package: {zip_filename}")
    print(f"Version: {version}")
    print(f"Output: {zip_path}")
    print()

    # Create zip file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        file_count = 0

        # Add individual files
        for filename in INCLUDE_FILES:
            file_path = addon_dir / filename
            if file_path.exists():
                arcname = f"{addon_name}/{filename}"
                zipf.write(file_path, arcname)
                print(f"  + {arcname}")
                file_count += 1
            else:
                print(f"  ! Warning: {filename} not found")

        # Add directories
        for dirname in INCLUDE_DIRS:
            dir_path = addon_dir / dirname
            if dir_path.exists() and dir_path.is_dir():
                for root, dirs, files in os.walk(dir_path):
                    # Filter out excluded directories
                    dirs[:] = [d for d in dirs if not should_exclude(Path(root) / d)]

                    for file in files:
                        file_path = Path(root) / file
                        if not should_exclude(file_path):
                            # Calculate relative path from addon_dir
                            rel_path = file_path.relative_to(addon_dir)
                            arcname = f"{addon_name}/{rel_path}"
                            zipf.write(file_path, arcname)
                            print(f"  + {arcname}")
                            file_count += 1
            else:
                print(f"  ! Warning: Directory {dirname} not found")

    print()
    print(f"✓ Package created successfully!")
    print(f"  Files: {file_count}")
    print(f"  Size: {zip_path.stat().st_size / 1024:.1f} KB")
    print(f"  Path: {zip_path}")
    print()
    print("Next steps:")
    print("  1. Test installation in Blender")
    print("  2. Upload to GitHub releases")
    print("  3. Update documentation with download link")

if __name__ == "__main__":
    create_package()
