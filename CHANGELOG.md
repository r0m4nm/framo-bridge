# Changelog

All notable changes to Framo Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2025-01-11

### Fixed
- **macOS auto-update support** - Fixed auto-update system not working on macOS
  - Added platform-independent addon directory detection
  - New `get_addon_directory()` method finds addon path dynamically
  - No longer assumes hardcoded addon path
  - Works on all platforms: Windows, macOS, Linux
  - Falls back to multiple standard addon locations if needed

### Technical
- Updated `updater.py`: Added `UpdateInstaller.get_addon_directory()` method
- Uses `addon_prefs.module.__file__` to get actual addon location
- Checks multiple possible addon locations (addons/, addons_contrib/)
- Fixes line 371 hardcoded path issue that caused macOS failures

## [0.2.1] - 2025-01-11

### Changed
- **Streamlined update system** - Removed manual update UI from panel
  - Updates now happen silently in background on Blender startup
  - No more "Update Now" button or update notifications in UI
  - Cleaner, less intrusive user experience
  - Auto-update still fully functional - just invisible to user

### Removed
- Manual update notification UI (Update Now button, progress bars, error messages)
- View Changes button for update changelogs
- All update-related UI elements from main panel

### Technical
- Kept automatic update check on startup (`check_pending_update_on_startup`)
- Updates download and install silently without user interaction
- Panel UI simplified by removing lines 1014-1060 (update notification box)

## [0.2.0] - 2025-01-11

### Changed
- **Removed Pillow dependency** - All texture optimization now uses Blender's native functions
- Texture scaling handled by new `texture_scaler.py` module (no external dependencies required)
- WebP compression now exclusively handled by Blender's glTF exporter via `export_image_format: 'WEBP'`
- Export messages now show which method was used (Native/Pillow) for transparency

### Added
- **Native texture scaling** with `texture_scaler.py` module
  - Uses Blender's built-in `image.scale()` function
  - No external dependencies (Pillow, numpy, etc.)
  - Maintains aspect ratios automatically
  - Non-destructive workflow (creates new images, originals preserved)
  - WebP format support detection (Blender 3.0+)
- **Smart fallback system** - Automatically uses native scaler, falls back to Pillow if unavailable
- **Two-stage optimization pipeline**:
  - Stage 1: Pre-export scaling (texture_scaler.py)
  - Stage 2: WebP compression (Blender's glTF exporter)

### Technical
- New file: `texture_scaler.py` - Dependency-free texture scaling module
- Updated: `texture_analyzer.py` - Retained as legacy fallback, added missing `is_webp_available()` function
- Updated: `__init__.py` - Integrated native scaler with smart fallback
- Updated: `build_zip.py` - Includes texture_scaler.py in distribution
- Updated: `README.md` - Documented native approach and two-stage pipeline

### Benefits
- ✅ No installation required - Works out of the box
- ✅ Faster setup - No pip install needed
- ✅ More reliable - No Pillow version conflicts
- ✅ Smaller footprint - No external libraries
- ✅ Easier maintenance - Pure Blender code

## [0.1.1] - 2025-01-10

### Fixed
- Test release to validate auto-update system functionality

## [0.1.0] - 2025-01-10

### Added
- **Auto-Update System**: Seamless updates directly from within Blender
  - Check for updates from GitHub releases
  - One-click download and installation
  - Automatic update check on startup (configurable)
  - View changelog before updating
  - Update notification UI in main panel
  - Restart-based installation for safety
  - Background download with progress indicator
- **Mesh Decimation**: Advanced polygon reduction with multiple algorithms
  - Collapse decimation (edge collapse)
  - Un-Subdivide (remove subdivision levels)
  - Planar decimation (architectural models)
  - Feature preservation (sharp edges, UV seams)
  - Adaptive decimation based on complexity
  - Real-time polygon count reporting
- **Texture Optimization**: Automatic texture scaling and format conversion
  - Scale textures to target size (2K, 1K, 512px, 256px)
  - Automatic WebP conversion via Blender's glTF exporter
  - Material exclusion list for textures that shouldn't be optimized
  - Non-destructive workflow (originals preserved)
  - Real-time texture analysis in UI
- **Material Readiness Analyzer**: Pre-export material validation
  - Detects unsupported shader nodes
  - Identifies missing textures
  - Validates PBR material setup
  - One-click material replacement
  - Opens materials directly in Shading workspace
  - Expandable material issue details
- **Auto UV Unwrapping**: Automatic UV map generation for meshes without UVs
  - Smart UV Project algorithm
  - Configurable angle limits and island margins
  - Statistics reporting
- **Advanced Compression Presets**:
  - None, Low, Medium, High, Custom
  - Custom quantization controls for position/normal/texcoord
- **Dependency Management**: Automatic installation of Python packages
  - One-click Pillow installation
  - Installation status indicators
  - Error handling and fallback options
- **User Connection System**: framo.app integration
  - User authentication display
  - Connect/disconnect status
  - Export blocked until user connects
- **Export Status Indicators**: Real-time export progress
  - Loading indicators during export
  - Detailed status messages
  - Auto-clearing success/error messages
- **Export Metadata**: Rich metadata sent with models
  - Compression settings
  - Decimation statistics
  - Material analysis results
  - Object counts and file sizes

### Changed
- **UI Improvements**:
  - Reorganized export settings into logical sections
  - Material Readiness panel with expandable details
  - Disabled UI sections when no objects selected
  - Better visual hierarchy with boxes and icons
  - Export button only enabled when user connected and materials ready
- **Non-Destructive Workflow**: All optimizations work on temporary copies
  - Original geometry never modified
  - Original textures restored after export
  - Temp objects automatically cleaned up
- **Enhanced Error Handling**:
  - Detailed error messages
  - Graceful fallbacks when modules unavailable
  - User-friendly warnings
- **Export Process**: More robust and informative
  - Better progress reporting
  - Comprehensive metadata
  - Material validation before export

### Fixed
- Server stability improvements
- Better cleanup of temporary data
- Proper handling of missing dependencies
- Material analysis edge cases

## [0.1.0] - 2025-10-XX

### Added
- Initial release
- Basic GLB export functionality
- Draco mesh compression support
- Built-in HTTP server (localhost:8080)
- Web viewer with Three.js
- Real-time model preview in browser
- Basic compression settings
- File size reporting

### Features
- One-click export from Blender to web
- Support for selected objects or full scene
- Automatic file size optimization
- Server endpoints for model retrieval
- Professional studio lighting in viewer
- Auto-centering and scaling

---

## Version Numbering

- **Major version** (X.0.0): Breaking changes, major feature overhauls
- **Minor version** (0.X.0): New features, non-breaking changes
- **Patch version** (0.0.X): Bug fixes, minor improvements

[0.1.0]: https://github.com/r0m4nm/framo-bridge/releases/tag/v0.1.0
