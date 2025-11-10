# Changelog

All notable changes to Framo Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-09

### Added
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

[0.2.0]: https://github.com/r0m4nm/framo-bridge/releases/tag/v0.2.0
[0.1.0]: https://github.com/r0m4nm/framo-bridge/releases/tag/v0.1.0
