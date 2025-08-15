# Framo Web GLB Exporter

A powerful Blender addon for one-click export of optimized 3D models directly to web applications with advanced compression, mesh decimation, and texture baking capabilities.

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

1. **In Blender:**
   - Edit → Preferences → Add-ons
   - Click "Install..."
   - Navigate to the addon folder and select `__init__.py`
   - Enable "Import-Export: Framo Web GLB Exporter"

2. **Verify Installation:**
   - In 3D Viewport, press `N` to open sidebar
   - Look for "Framo Export" tab
   - You should see "Server Status: Running"

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
- `GET http://localhost:8080/latest-model` - Get latest GLB model
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

- Texture baking system for procedural materials
- Ambient occlusion baking
- Material optimization
- Batch processing capabilities
- Cloud processing integration

## Version History

- **v0.2.0**: Added mesh decimation and advanced compression
- **v0.1.0**: Initial MVP with basic export and compression

## License

Proprietary - All rights reserved

## Author

Roman Moor

---

**Status**: Active Development  
**Latest Version**: 0.2.0