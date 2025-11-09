# Distribution Guide for Framo Bridge

This guide explains how to package and distribute the Framo Bridge addon.

## Quick Distribution (Automated)

### Using the Packaging Script

```bash
python package.py
```

This will create a `framo-exporter-v{version}.zip` in the parent directory, ready for distribution.

The script:
- Reads version from `__init__.py` bl_info
- Includes all necessary files
- Excludes development files (.git, __pycache__, etc.)
- Creates properly structured zip

## Manual Distribution

If you prefer to create the zip manually:

### Step 1: Prepare Files

Ensure these files are present:

**Required:**
- `__init__.py` - Main addon file with bl_info
- `decimation.py` - Mesh decimation
- `dependencies.py` - Dependency management
- `material_analyzer.py` - Material validation
- `texture_analyzer.py` - Texture optimization
- `uv_unwrap.py` - UV utilities
- `README.md` - User documentation
- `INSTALL.md` - Installation guide
- `LICENSE` - MIT license
- `CHANGELOG.md` - Version history

**Optional but Recommended:**
- `test_viewer.html` - Web viewer for testing
- `icons/` - Custom icon directory

### Step 2: Create Zip Structure

The zip must have this structure:

```
framo-exporter.zip
└── framo-exporter/          ← Folder with addon name
    ├── __init__.py
    ├── decimation.py
    ├── dependencies.py
    ├── material_analyzer.py
    ├── texture_analyzer.py
    ├── uv_unwrap.py
    ├── test_viewer.html
    ├── icons/
    │   └── framo_icon.png
    ├── README.md
    ├── INSTALL.md
    ├── CHANGELOG.md
    └── LICENSE
```

**IMPORTANT**: The addon folder name MUST be at the root of the zip.

### Step 3: Exclude Development Files

Do NOT include:
- `__pycache__/` directories
- `.git/` directory
- `.gitignore`
- `.guides/`, `.plans/`
- `*.pyc`, `*.pyo` files
- `package.py`
- `DISTRIBUTION.md` (this file)
- Any `.blend` test files

## Testing the Distribution

Before publishing:

### 1. Test Installation

1. **Uninstall** current version from Blender (if installed)
2. **Restart Blender**
3. Go to Edit → Preferences → Add-ons
4. Click Install and select your zip file
5. Enable "Import-Export: Framo Bridge"
6. Verify all features work

### 2. Test Dependency Installation

1. In 3D Viewport sidebar (N), go to Framo Export tab
2. Click "Install Required Dependencies"
3. Wait for installation
4. Restart Blender
5. Verify dependencies show as installed

### 3. Test Basic Export

1. Create a simple cube
2. Select it
3. Click "Send to Framo"
4. Verify export completes without errors

## Publishing to GitHub Releases

### 1. Update Version

Before creating a release:

1. Update version in `__init__.py` bl_info:
   ```python
   "version": (0, 2, 1),  # Example
   ```

2. Update `CHANGELOG.md` with new version:
   ```markdown
   ## [0.2.1] - 2025-11-10
   ### Fixed
   - Bug fixes...
   ```

3. Commit changes:
   ```bash
   git add __init__.py CHANGELOG.md
   git commit -m "Bump version to 0.2.1"
   git push
   ```

### 2. Create Package

```bash
python package.py
```

This creates `framo-exporter-v0.2.1.zip`

### 3. Create GitHub Release

1. Go to your GitHub repository
2. Click "Releases" → "Create a new release"
3. Create a new tag: `v0.2.1`
4. Release title: `Framo Bridge v0.2.1`
5. Description: Copy from CHANGELOG.md
6. Upload the zip file
7. Check "Set as latest release"
8. Publish release

### 4. Update Documentation

Update README.md download link to point to latest release:

```markdown
Download: [Latest Release](https://github.com/romanmoor/framo-exporter/releases/latest)
```

## Distribution Checklist

Before each release:

- [ ] Version updated in `__init__.py`
- [ ] `CHANGELOG.md` updated with changes
- [ ] All Python files have no syntax errors
- [ ] README.md is up to date
- [ ] INSTALL.md reflects current process
- [ ] LICENSE file present
- [ ] Test installation from zip works
- [ ] Dependencies install correctly
- [ ] Basic export functionality works
- [ ] No development files in zip
- [ ] Zip structure is correct
- [ ] Git committed and pushed
- [ ] GitHub release created
- [ ] Download link tested

## Alternative Distribution Methods

### Blender Extensions Platform (Blender 4.2+)

For the new Blender Extensions system:

1. Create `blender_manifest.toml`:
   ```toml
   schema_version = "1.0.0"
   id = "framo-bridge"
   version = "0.2.0"
   name = "Framo Bridge"
   tagline = "Export optimized GLB models to web"
   maintainer = "Roman Moor <your@email.com>"
   type = "add-on"
   tags = ["Import-Export", "3D View"]
   blender_version_min = "3.0.0"
   license = ["SPDX:MIT"]
   ```

2. Follow Blender Extensions packaging guidelines
3. Submit to extensions.blender.org

### Gumroad / BlenderMarket

For commercial distribution:

1. Create product listing
2. Add screenshots/promotional images
3. Upload zip file
4. Set price (or free)
5. Configure update notifications

## Support After Release

Monitor these channels:

- GitHub Issues: Bug reports
- GitHub Discussions: Questions
- Email: Direct support

Update CHANGELOG.md and create patch releases for bug fixes.

## Version Numbering Strategy

Follow Semantic Versioning (semver):

- **Major (X.0.0)**: Breaking changes
- **Minor (0.X.0)**: New features, backward compatible
- **Patch (0.0.X)**: Bug fixes only

Examples:
- `0.2.0` → `0.2.1`: Bug fixes
- `0.2.1` → `0.3.0`: New features added
- `0.3.0` → `1.0.0`: Major release, breaking changes

## Files Generated

After running `package.py`:

```
parent-directory/
├── framo-exporter/              (your dev folder)
│   ├── __init__.py
│   └── ... (all addon files)
└── framo-exporter-v0.2.0.zip   (generated package)
```

The zip is created in the parent directory to keep your dev folder clean.
