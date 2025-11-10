# Framo Web GLB Exporter

A powerful Blender addon for one-click export of optimized 3D models directly to web applications with advanced compression and mesh decimation capabilities.

## Features

### ✅ **Core Export Features**
- One-click GLB export from Blender to web viewer
- Built-in HTTP server (localhost:8080)
- Real-time model viewing in browser with Three.js
- Support for selected objects or full scene export
- Automatic file size reporting in MB

### ✅ **Advanced Compression**
- **Draco Mesh Compression** with quality presets
- **Custom compression settings** for position, normal, and UV quantization
- **Automatic compression presets**: None, Low, Medium, High, Custom
- Typically achieves 50-90% file size reduction

### ✅ **Mesh Optimization**
- **Smart Decimation** with multiple algorithms (Collapse, Un-Subdivide, Planar)
- **Adaptive decimation** based on mesh complexity
- **Feature preservation** (sharp edges, UV seams)
- **Real-time polygon count reporting**

### ✅ **Web-Ready Features**
- **HDRI environment lighting** for realistic presentation
- **Draco decompression** support in web viewer
- **Professional studio lighting** setup
- **Auto-centering and scaling** of imported models
- **Real-time statistics** (file size, triangle count)

## Installation

### 1. Install Addon

1. **In Blender:**
   - Edit → Preferences → Add-ons
   - Click "Install..."
   - Navigate to the addon folder and select `__init__.py`
   - Enable "Import-Export: Framo Web GLB Exporter"

### 2. Install Dependencies (Required for Texture Optimization)

The addon requires Python packages for texture optimization:
- **Pillow** - Image processing library
- **numpy** - Numerical computing backend

**Automatic Installation:**
1. After enabling the addon, look for the **"Install Dependencies"** button
2. Click it and wait 1-2 minutes
3. **Restart Blender** when installation completes

**Manual Installation (if automatic fails):**
```powershell
# Windows
cd "C:\Program Files\Blender Foundation\Blender 4.4\4.4\python\bin"
.\python.exe -m pip install Pillow numpy

# macOS
cd /Applications/Blender.app/Contents/Resources/4.4/python/bin
./python3.11 -m pip install Pillow numpy

# Linux
cd /usr/share/blender/4.4/python/bin
./python3.11 -m pip install Pillow numpy
```

**Note:** Without dependencies, texture optimization features will be unavailable, but mesh decimation and export will still work.

### 3. Verify Installation

1. In 3D Viewport, press `N` to open sidebar
2. Look for "Framo Export" tab
3. Check "Dependencies" section shows all packages as ✓ Installed
4. Server Status should show "Running"

## Usage

### Basic Export:

1. **Select objects** you want to export (or select nothing for entire scene)
2. **Open the "Framo Export" tab** in 3D Viewport sidebar (press `N`)
3. **Configure settings** as needed:
   - **Compression Preset**: Choose quality level
   - **Mesh Optimization**: Enable decimation if needed
4. **Click "Send to Web App"**
5. **Open `test_viewer.html`** in your browser to see the result

### Advanced Settings:

#### **Compression Options:**
- **No Compression**: Original quality, larger files
- **Low Compression**: Minimal compression, high quality
- **Medium Compression**: Balanced (recommended for web)
- **High Compression**: Maximum compression, smaller files
- **Custom**: Manual control over all parameters

#### **Mesh Optimization:**
- **Decimate Ratio**: 0.5 = 50% face reduction
- **Decimate Type**: 
  - Collapse (best for most cases)
  - Un-Subdivide (for over-subdivided models)
  - Planar (for architectural models)
- **Adaptive Decimation**: Automatically adjusts based on complexity

## Server Endpoints

- `GET http://localhost:8080/ping` - Health check
- `GET http://localhost:8080/latest-model` - Get latest GLB model (binary)
- `GET http://localhost:8080/latest-model-info` - Get model metadata (JSON)
- `POST http://localhost:8080/upload-model` - Upload GLB data (internal)

## Example Export Messages

```
"Exported 0.85MB (Draco: Level 6, Decimated 2 objects (70% reduction)) to web app"
```

## Performance Optimizations

### File Size Reductions:
- **Draco Compression**: 50-80% size reduction
- **Mesh Decimation**: 30-90% polygon reduction
- **Combined**: Often results in 90%+ file size reduction

### Web Performance:
- Optimized for fast loading
- Efficient polygon counts for real-time rendering
- Proper LOD (Level of Detail) support through decimation

## Browser Compatibility

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+
- WebGL 2.0 support required

## Troubleshooting

### Common Issues:

**Server not running:**
- Disable and re-enable the addon in Blender preferences

**Port 8080 in use:**
- Close other applications using port 8080
- Restart Blender

**Model not appearing in browser:**
- Check browser console for errors
- Ensure `test_viewer.html` is opened in a web browser
- Verify server status shows "Connected"

**Export fails:**
- Ensure GLB exporter is enabled in Blender
- Check that objects have valid geometry
- Try with simpler models first

**Very large file sizes:**
- Enable Draco compression
- Use mesh decimation for high-poly models
- Check compression settings

## Technical Requirements

- **Blender**: 3.0+
- **Browser**: Modern browser with WebGL 2.0 support
- **Network**: Local HTTP server (localhost:8080)
- **Python**: 3.7+ (included with Blender)

## Advanced Features

### Compression Details:
- **Position Quantization**: Controls vertex position precision
- **Normal Quantization**: Controls surface normal precision  
- **Texture Coordinate Quantization**: Controls UV precision
- **Compression Levels**: 0-10 (higher = more compression)

### Decimation Details:
- **Collapse Decimation**: Best general-purpose algorithm
- **Feature Preservation**: Maintains sharp edges and UV seams
- **Adaptive Processing**: Different settings for different complexity levels

## Future Enhancements

- Material optimization
- Batch processing capabilities
- Cloud processing integration
- Texture optimization

## Version History

- **v0.2.0**: Added mesh decimation and advanced compression
- **v0.1.0**: Initial MVP with basic export and compression

## Quick Start

1. **Install** the addon (see [INSTALL.md](INSTALL.md))
2. **Select** objects in your scene
3. **Press N** in 3D Viewport → Go to "Framo Export" tab
4. **Click "Send to Framo"**

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## File Structure

When distributing, zip the entire addon folder:

```
framo-exporter/
├── __init__.py              # Main addon file
├── decimation.py            # Mesh decimation module
├── dependencies.py          # Dependency management
├── material_analyzer.py     # Material validation
├── texture_analyzer.py      # Texture optimization
├── uv_unwrap.py            # UV unwrapping utilities
├── test_viewer.html        # Web viewer for testing
├── icons/                  # Custom icons
├── README.md               # This file
├── INSTALL.md              # Installation guide
├── CHANGELOG.md            # Version history
└── LICENSE                 # MIT License
```

## Creating Distribution Zip

To create a distribution-ready zip:

1. **Ensure all files are in a folder named `framo-exporter`**
2. **Zip the entire folder** (not just the contents)
3. The zip should contain `framo-exporter/` as the root folder
4. Users can install directly from this zip in Blender

**Correct structure:**
```
framo-exporter.zip
└── framo-exporter/
    ├── __init__.py
    ├── decimation.py
    └── ... (other files)
```

**Incorrect structure (don't do this):**
```
framo-exporter.zip
├── __init__.py
├── decimation.py
└── ... (files at root)
```

## Contributing

Issues and pull requests welcome at: https://github.com/romanmoor/framo-exporter

## License

MIT License - See [LICENSE](LICENSE) file for details

Copyright (c) 2025 Roman Moor

## Support

- **Issues**: https://github.com/romanmoor/framo-exporter/issues
- **Documentation**: https://github.com/romanmoor/framo-exporter

---

**Status**: Active Development
**Latest Version**: 0.2.0
**Blender**: 3.0+ (4.0+ recommended)