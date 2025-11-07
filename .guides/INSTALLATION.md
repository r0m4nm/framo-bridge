# Installation Guide

## For End Users

### Installing the Addon

1. **Download** the addon (zip file or folder)
2. **Open Blender** → Edit → Preferences → Add-ons
3. **Click "Install..."** and select the addon file
4. **Enable** "Import-Export: Framo Web GLB Exporter"
5. **Open the panel** (N key → Framo Export tab)

### Installing Dependencies (Automatic)

The addon will **automatically detect** missing dependencies and show installation buttons in the UI.

**First Time Setup:**

1. Open the **Framo Export** panel (N key → Framo Export)
2. Look for the **"Dependencies"** section at the top
3. Click **"Install Required Dependencies"** button
4. Wait for installation (may take 1-2 minutes)
5. **Restart Blender** when prompted

**That's it!** The addon will work after restart.

### Manual Installation (If Auto-Install Fails)

If the automatic installation doesn't work, you can install manually:

**Windows:**
```cmd
"C:\Program Files\Blender Foundation\Blender\4.4\4.4\python\bin\python.exe" -m pip install trimesh
```

**macOS:**
```bash
/Applications/Blender.app/Contents/Resources/4.4/python/bin/python3.10m -m pip install trimesh
```

**Linux:**
```bash
/usr/bin/blender --python-expr "import subprocess, sys; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'trimesh'])"
```

## How It Works

### Dependency Detection

When you open the addon panel, it automatically:
- ✅ Checks if `trimesh` is installed
- ✅ Checks if `open3d` is installed (optional)
- ✅ Shows status indicators
- ✅ Provides install buttons if missing

### Installation Process

When you click "Install Dependencies":
1. Uses Blender's built-in Python
2. Runs `pip install` automatically
3. Shows progress in console
4. Verifies installation
5. Prompts to restart Blender

### After Installation

- **Restart Blender** (required for imports to work)
- Dependencies section will show ✅ checkmarks
- All features will be available

## Features That Require Dependencies

### Required (trimesh)
- ✅ **Mesh Repair & Cleaning** - All repair features
- ✅ **Fast Decimation** - Trimesh-based decimation

### Optional (open3d)
- ⚡ **Faster Decimation** - Open3D is faster than Trimesh for decimation

### No Dependencies Needed
- ✅ **Basic Export** - Works without any dependencies
- ✅ **Draco Compression** - Uses Blender's built-in exporter
- ✅ **Server** - HTTP server works independently

## Troubleshooting

### "Installation Failed"
- Check internet connection
- Try manual installation (see above)
- Check Blender console for error messages
- May need administrator/sudo permissions

### "Dependencies Not Detected After Install"
- **Restart Blender** (required!)
- Check console for import errors
- Verify installation: Open Python console and type `import trimesh`

### "Permission Denied"
- Windows: Run Blender as Administrator
- macOS/Linux: May need `sudo` for manual installation
- Or install to user directory: `pip install --user trimesh`

### "Still Shows Missing After Restart"
- Verify installation manually:
  ```python
  # In Blender Python console:
  import trimesh
  print(trimesh.__version__)
  ```
- If this works, the addon should detect it
- Check addon console for error messages

## For Developers

### Adding New Dependencies

Edit `dependencies.py`:

```python
REQUIRED_DEPENDENCIES = {
    'new_package': {
        'name': 'new_package',
        'description': 'Description here',
        'required_for': ['feature_name'],
        'optional': False  # or True
    }
}
```

### Testing Installation

1. Remove trimesh: `pip uninstall trimesh`
2. Restart Blender
3. Check UI shows "Missing" status
4. Click install button
5. Verify installation works
6. Restart and verify detection

## Security Notes

- Installation uses Blender's Python (isolated)
- Only installs to Blender's Python environment
- Doesn't affect system Python
- Requires user confirmation (button click)
- Shows what will be installed

## Network Requirements

- Internet connection required for installation
- Downloads from PyPI (Python Package Index)
- No data sent to external servers (only downloads)
- Works offline after installation

