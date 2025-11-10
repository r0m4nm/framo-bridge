# Framo Bridge Release Process Guide

This guide explains how to release new versions of Framo Bridge with the auto-update system.

## Overview

Framo Bridge uses an automated release system that:
- Automatically builds addon packages from Git tags
- Publishes releases to GitHub with changelogs
- Enables in-Blender auto-updates for users
- Maintains version synchronization across all files

## Release Workflow

### 1. Update Version Number

**File:** `__init__.py` (line 4)

Change the version tuple:
```python
bl_info = {
    "name": "Framo Bridge",
    "author": "Roman Moor",
    "version": (0, 1, 2),  # <-- Update this (major, minor, patch)
    "blender": (3, 0, 0),
    # ...
}
```

**Version numbering:**
- **Patch** (0.1.X): Bug fixes, minor improvements
- **Minor** (0.X.0): New features, non-breaking changes
- **Major** (X.0.0): Breaking changes, major overhauls

### 2. Update Changelog

**File:** `CHANGELOG.md`

Add a new entry at the top:
```markdown
## [0.1.2] - 2025-01-XX

### Added
- New feature descriptions

### Changed
- Modified functionality descriptions

### Fixed
- Bug fix descriptions
```

**Important:**
- Use the exact format: `## [VERSION] - DATE`
- The version must match `__init__.py`
- This is automatically extracted for release notes

### 3. Commit and Tag

Run this single command to commit, tag, and push:

```bash
git add . && \
git commit -m "Release v0.1.2 - Brief description" && \
git tag v0.1.2 && \
git push origin main && \
git push origin v0.1.2
```

**Tag format:** Always use `v` prefix (e.g., `v0.1.2`, `v1.0.0`)

### 4. Automated Build Process

Once the tag is pushed, GitHub Actions automatically:

1. ✅ Detects the new tag
2. ✅ Extracts version from `__init__.py`
3. ✅ Runs `build_zip.py` to create the addon package
4. ✅ Extracts changelog from `CHANGELOG.md`
5. ✅ Creates GitHub Release with:
   - Title: "Framo Bridge v0.1.2"
   - Body: Installation instructions + changelog
   - Asset: `framo-bridge-v0.1.2.zip`

**Monitor progress:**
- Actions: https://github.com/r0m4nm/framo-bridge/actions
- Releases: https://github.com/r0m4nm/framo-bridge/releases

### 5. User Auto-Update

Users with the addon installed will:
1. Open Blender → Auto-check runs on startup
2. See notification: "Update available: v0.1.2"
3. Click "Update Now" → Downloads in background
4. Restart Blender → New version installed

## Important Files

### Core Release Files

- **`__init__.py`** (line 4): Version number (single source of truth)
- **`CHANGELOG.md`**: Release notes for each version
- **`build_zip.py`**: Builds the addon package (reads version from `__init__.py`)
- **`.github/workflows/release.yml`**: GitHub Actions automation

### Auto-Update System Files

- **`updater.py`**: Update checking and installation logic
- **`__init__.py`** (lines 1698-1880): Update operators and UI
- **`__init__.py`** (lines 2089-2142): Startup handler for pending updates

### Build Configuration

**`build_zip.py` includes:**
```python
INCLUDE_FILES = [
    '__init__.py',
    'updater.py',         # Auto-update system
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
```

**When adding new files:** Update `INCLUDE_FILES` or `INCLUDE_FOLDERS` in `build_zip.py`

## Version Synchronization

The system maintains version consistency:

1. **`__init__.py`**: `"version": (0, 1, 2)` ← Single source of truth
2. **`build_zip.py`**: Auto-reads from `__init__.py` → generates `framo-bridge-v0.1.2.zip`
3. **GitHub tag**: `v0.1.2` ← Must match `__init__.py`
4. **CHANGELOG.md**: `## [0.1.2]` ← Must match for release notes

**The workflow validates:** Tag version matches `__init__.py` version

## Testing the Release

### Local Testing (Before Release)

```bash
# Build locally to verify no errors
python build_zip.py

# Should output:
# Building Framo Bridge v0.1.2...
# ✓ Successfully created framo-bridge-v0.1.2.zip
```

### Production Testing (After Release)

1. Install the **previous version** in Blender
2. Open Blender → Update notification appears
3. Click "Update Now" → Download completes
4. Restart Blender → New version installed
5. Verify version in panel header: "Framo Bridge v0.1.2"

## Troubleshooting

### Issue: GitHub Actions fails with "Version mismatch"

**Cause:** Tag version doesn't match `__init__.py` version

**Fix:**
```bash
# Delete the incorrect tag
git push --delete origin v0.1.2
git tag -d v0.1.2

# Fix version in __init__.py
# Commit changes
git add . && git commit -m "Fix version"

# Recreate tag
git tag v0.1.2
git push origin main
git push origin v0.1.2
```

### Issue: YAML syntax error in workflow

**Cause:** Invalid workflow file syntax

**Fix:**
```bash
# Validate YAML syntax
pip install yamllint
yamllint .github/workflows/release.yml

# Line length warnings are OK, only errors matter
```

### Issue: Build fails - file not found

**Cause:** Missing file in `build_zip.py` include list

**Fix:** Add the file to `INCLUDE_FILES` or `INCLUDE_FOLDERS` in `build_zip.py`

### Issue: Users not seeing update notification

**Possible causes:**
1. Auto-check disabled in preferences → User needs to enable it
2. GitHub API rate limit → Wait 1 hour, limit is 60 req/hour
3. Network issue → Check internet connection
4. Manual check → Edit > Preferences > Add-ons > Framo Bridge > Check for Updates Now

## Quick Reference

### Complete Release Command

```bash
# One command to release everything
git add . && \
git commit -m "Release v0.1.2 - Description" && \
git tag v0.1.2 && \
git push origin main && \
git push origin v0.1.2
```

### Version Update Checklist

- [ ] Update `__init__.py` line 4: `"version": (0, 1, 2)`
- [ ] Add entry to `CHANGELOG.md`: `## [0.1.2] - DATE`
- [ ] Commit with message: `"Release v0.1.2 - Description"`
- [ ] Tag with: `v0.1.2` (matches version)
- [ ] Push commits: `git push origin main`
- [ ] Push tag: `git push origin v0.1.2`
- [ ] Monitor: https://github.com/r0m4nm/framo-bridge/actions
- [ ] Verify: https://github.com/r0m4nm/framo-bridge/releases

## Repository Information

- **Repository:** `r0m4nm/framo-bridge` (private)
- **Releases:** Public (anyone can download)
- **GitHub Actions:** Automated on tag push
- **Auto-update API:** `https://api.github.com/repos/r0m4nm/framo-bridge/releases/latest`

## Notes for AI Coding Agents

When making changes to the codebase:

1. **Never manually edit version numbers** in multiple places
   - Only edit `__init__.py` line 4
   - `build_zip.py` auto-reads the version

2. **Always update CHANGELOG.md** when releasing
   - Use exact format: `## [VERSION] - DATE`
   - Place new entries at the top

3. **New files require build configuration**
   - Add to `INCLUDE_FILES` in `build_zip.py`
   - Test build with `python build_zip.py`

4. **Tag format is critical**
   - Always use `v` prefix: `v0.1.2`
   - Must match `__init__.py` version exactly

5. **Test releases locally first**
   - Run `python build_zip.py` before tagging
   - Verify no errors in build output

---

**Last Updated:** 2025-01-10
**System Version:** v0.1.1
**Auto-Update Status:** ✅ Fully Operational
