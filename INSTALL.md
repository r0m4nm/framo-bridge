# Framo Bridge - Installation Guide

## Quick Installation (Recommended)

### Step 1: Download the Addon

Download the latest `framo-bridge.zip` from the releases page.

### Step 2: Install in Blender

1. Open Blender
2. Go to **Edit → Preferences → Add-ons**
3. Click **Install...** button (top right)
4. Navigate to the downloaded `framo-bridge.zip` file
5. Select the zip file and click **Install Add-on**
6. Find "Import-Export: Framo Bridge" in the addon list
7. **Check the box** to enable it

### Step 3: Install Dependencies (Required)

The addon needs Python packages for texture optimization:

1. After enabling the addon, open the 3D Viewport sidebar (press `N`)
2. Click on the **Framo Export** tab
3. Look for the **Dependencies** section
4. Click **Install Required Dependencies**
5. Wait 1-2 minutes for installation
6. **Restart Blender** when complete

### Step 4: Verify Installation

1. In 3D Viewport, press `N` to open sidebar
2. Look for **Framo Export** tab
3. You should see:
   - "Connected: [Your Name]" or "Disconnected" status
   - Export Settings section
   - Material Readiness section
   - "Send to Framo" button at the bottom

That's it! You're ready to export.

## Alternative Installation Methods

### Method 2: Install from Folder

If you have the unzipped folder:

1. Copy the entire `framo-bridge` folder to Blender's addons directory:
   - **Windows**: `%APPDATA%\Blender Foundation\Blender\[VERSION]\scripts\addons\`
   - **macOS**: `~/Library/Application Support/Blender/[VERSION]/scripts/addons/`
   - **Linux**: `~/.config/blender/[VERSION]/scripts/addons/`
2. Restart Blender
3. Go to **Edit → Preferences → Add-ons**
4. Search for "Framo Bridge"
5. Enable the addon

### Method 3: Manual Dependency Installation

If automatic dependency installation fails:

**Windows:**
```powershell
cd "C:\Program Files\Blender Foundation\Blender 4.4\4.4\python\bin"
.\python.exe -m pip install Pillow
```

**macOS:**
```bash
cd /Applications/Blender.app/Contents/Resources/4.4/python/bin
./python3.11 -m pip install Pillow
```

**Linux:**
```bash
cd /usr/share/blender/4.4/python/bin
./python3.11 -m pip install Pillow
```

After installation, restart Blender.

## Requirements

- **Blender**: Version 3.0 or higher (Blender 4.0+ recommended)
- **Operating System**: Windows, macOS, or Linux
- **Python**: Included with Blender (3.7+)
- **Internet**: Required for dependency installation

## Troubleshooting

### Addon doesn't appear after installation
- Make sure you extracted/selected the **zip file**, not a subfolder
- Restart Blender
- Check that the addon is enabled in Preferences

### Dependencies won't install
- Check your internet connection
- Try manual installation method above
- Make sure Blender has write permissions to its Python directory
- On some systems, you may need to run Blender as administrator (Windows) or with sudo (Linux/Mac)

### "Server not running" error
- Disable and re-enable the addon in Blender Preferences
- Check if port 8080 is available (close other apps using it)
- Restart Blender

### Cannot find addon folder
Run this command in Blender's Python Console (Scripting workspace):
```python
import bpy
print(bpy.utils.user_resource('SCRIPTS', path="addons"))
```

## Getting Started

After installation:

1. **Select objects** in your scene (or leave empty to export everything)
2. **Open sidebar** (press `N` in 3D Viewport)
3. Go to **Framo Export** tab
4. Configure export settings if needed
5. Click **Send to Framo**

For detailed usage instructions, see [README.md](README.md)

## Support

- **Issues**: https://github.com/r0m4nm/framo-bridge/issues
- **Documentation**: https://github.com/r0m4nm/framo-bridge

## Updating the Addon

To update to a new version:

1. **Download** the new version zip
2. In Blender Preferences → Add-ons, find "Framo Bridge"
3. Click **Remove** to uninstall the old version
4. **Restart Blender**
5. Follow installation steps above with the new zip file

Your settings and preferences will be preserved.
