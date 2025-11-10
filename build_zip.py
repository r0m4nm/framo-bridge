#!/usr/bin/env python3
"""
Build script to create the Framo Bridge addon distribution zip file.
Creates a zip with framo-bridge/ as the root folder.
"""

import os
import zipfile
from pathlib import Path

# Files and folders to include
INCLUDE_FILES = [
    '__init__.py',
    'decimation.py',
    'dependencies.py',
    'material_analyzer.py',
    'texture_analyzer.py',
    'uv_unwrap.py',
    'README.md',
    'CHANGELOG.md',
    'INSTALL.md',
    'LICENSE',
    'test_viewer.html',
]

INCLUDE_FOLDERS = [
    'icons',
]

EXCLUDE_PATTERNS = [
    '__pycache__',
    '*.pyc',
    '*.pyo',
    '.git',
    '.gitignore',
    'build_zip.py',
    'framo-bridge-*.zip',
    'framo-exporter-*.zip',
    'builds',
]

def should_exclude(file_path):
    """Check if a file should be excluded from the zip."""
    path_str = str(file_path)
    
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    
    return False

def create_zip():
    """Create the distribution zip file."""
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Create builds directory if it doesn't exist
    builds_dir = project_root / 'builds'
    builds_dir.mkdir(exist_ok=True)
    
    # Output zip file name
    zip_filename = 'framo-bridge-v0.2.1.zip'
    zip_path = builds_dir / zip_filename
    
    # Remove existing zip if it exists
    if zip_path.exists():
        print(f"Removing existing {zip_filename}...")
        zip_path.unlink()
    
    print(f"Creating {zip_filename}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add individual files
        for filename in INCLUDE_FILES:
            file_path = project_root / filename
            if file_path.exists():
                arcname = f'framo-bridge/{filename}'
                zipf.write(file_path, arcname)
                print(f"  Added: {arcname}")
            else:
                print(f"  Warning: {filename} not found, skipping")
        
        # Add folders and their contents
        for folder_name in INCLUDE_FOLDERS:
            folder_path = project_root / folder_name
            if folder_path.exists() and folder_path.is_dir():
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file() and not should_exclude(file_path):
                        # Get relative path from folder
                        rel_path = file_path.relative_to(folder_path)
                        arcname = f'framo-bridge/{folder_name}/{rel_path}'
                        zipf.write(file_path, arcname)
                        print(f"  Added: {arcname}")
            else:
                print(f"  Warning: {folder_name} folder not found, skipping")
    
    # Get file size
    file_size = zip_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    
    print(f"\n✓ Successfully created {zip_filename}")
    print(f"  Size: {size_mb:.2f} MB ({file_size:,} bytes)")
    print(f"  Location: {zip_path.absolute()}")

if __name__ == '__main__':
    create_zip()

