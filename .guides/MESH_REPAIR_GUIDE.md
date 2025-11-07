# Mesh Repair & Cleaning Guide

## Overview

The addon now includes **mesh repair and cleaning** features using Trimesh. This helps fix common mesh issues before export, ensuring better compatibility with web viewers and GLB format.

## Features

### Basic Cleaning (Safe - Recommended)
- ✅ **Remove Duplicate Vertices** - Merge vertices at the same location
- ✅ **Remove Duplicate Faces** - Remove identical faces
- ✅ **Remove Unreferenced Vertices** - Clean up orphaned vertices
- ✅ **Fix Normals** - Ensure consistent face normals
- ✅ **Remove Degenerate Faces** - Remove zero-area and invalid faces

### Advanced Repair (May Change Geometry)
- ⚠️ **Fill Holes** - Fill holes in the mesh (may add geometry)
- ⚠️ **Make Watertight** - Close all holes to make mesh watertight (significant changes)

## How to Use

### 1. Enable Mesh Repair

1. Open Blender's 3D Viewport
2. Press `N` to open the sidebar
3. Go to **"Framo Export"** tab
4. Find **"Mesh Repair & Cleaning"** section
5. Check **"Enable Mesh Repair"**

### 2. Configure Options

**Basic Options (Safe):**
- ✅ Remove Duplicate Vertices (default: ON)
- ✅ Remove Duplicate Faces (default: ON)
- ✅ Remove Unreferenced Vertices (default: ON)
- ✅ Fix Normals (default: ON)
- ✅ Remove Degenerate Faces (default: ON)

**Advanced Options (Use with caution):**
- ⚠️ Fill Holes (default: OFF)
- ⚠️ Make Watertight (default: OFF)

### 3. Test Before Export

**Always test first!**

1. Select your mesh objects
2. Configure repair options
3. Click **"Test Mesh Repair"** button
4. Check the **console output** (Window → Toggle System Console)
5. Review the analysis and repair results

### 4. Export

Once tested and satisfied:
1. Keep repair options enabled
2. Click **"Send to Web App"**
3. Mesh repair runs automatically before export

## Testing Workflow

### Step 1: Analyze
The test function analyzes all selected objects and reports:
- Vertex and face counts
- Watertight status
- Winding consistency
- Duplicate vertices/faces
- Holes
- Degenerate faces

### Step 2: Test Repair
Tests repair on the first selected object and shows:
- Before/after statistics
- Vertices/faces removed
- Issues fixed

### Step 3: Verify
- Check the mesh in Blender viewport
- Verify geometry looks correct
- Check console for detailed stats

## Common Use Cases

### CAD Imports
**Problem:** CAD files often have duplicate vertices, non-manifold edges, holes

**Solution:**
- Enable all basic cleaning options
- Test first to see what issues exist
- Use "Fill Holes" if needed (test first!)

### Scanned Meshes
**Problem:** 3D scans often have holes and non-manifold geometry

**Solution:**
- Enable basic cleaning
- Consider "Fill Holes" for small holes
- Use "Make Watertight" only if absolutely necessary

### Game Assets
**Problem:** Need clean, optimized meshes

**Solution:**
- Enable all basic options
- Usually don't need "Fill Holes" or "Make Watertight"
- Focus on removing duplicates and fixing normals

## Best Practices

1. **Always test first** - Use the test button before enabling for export
2. **Start conservative** - Enable only basic options first
3. **Check results** - Verify geometry after repair
4. **Save backups** - Keep original files before repair
5. **Use advanced options carefully** - They can significantly change geometry

## Troubleshooting

### "Mesh repair not available"
- Install Trimesh: `pip install trimesh` in Blender's Python
- See `DECIMATION_SETUP.md` for installation instructions

### "Repair failed"
- Check console for error details
- May indicate severe mesh issues
- Try enabling options one at a time

### Geometry looks wrong after repair
- Disable "Fill Holes" and "Make Watertight"
- These can add unwanted geometry
- Use only basic cleaning options

### No changes after repair
- Mesh may already be clean
- Check console output for details
- Some meshes don't need repair

## Integration with Export

Mesh repair runs **before** decimation in the export pipeline:

1. **Mesh Repair** (if enabled)
2. **Mesh Decimation** (if enabled)
3. **GLB Export**

This ensures:
- Clean meshes are decimated
- Better decimation results
- Fewer export errors
- Smaller file sizes

## Performance

- **Fast**: Basic cleaning is very fast (< 1 second for most meshes)
- **Moderate**: Fill holes can take a few seconds for complex meshes
- **Slow**: Make watertight can be slow for very complex meshes

## Technical Details

### What Gets Fixed

**Duplicate Vertices:**
- Vertices at the same location are merged
- Reduces vertex count
- Improves mesh quality

**Duplicate Faces:**
- Identical faces are removed
- Reduces face count
- Prevents rendering issues

**Unreferenced Vertices:**
- Vertices not used by any face are removed
- Reduces memory usage
- Cleans up mesh data

**Normals:**
- Face normals are made consistent
- Ensures proper shading
- Fixes flipped faces

**Degenerate Faces:**
- Zero-area faces are removed
- Invalid faces are removed
- Prevents export errors

**Holes:**
- Small holes are filled with new geometry
- May change mesh topology
- Use with caution

**Watertight:**
- All holes are closed
- Mesh becomes fully closed
- Significant geometry changes possible

## Console Output Example

```
============================================================
MESH REPAIR ANALYSIS
============================================================

Object: Cube
  Vertices: 8
  Faces: 12
  Watertight: True
  Winding consistent: True
  Has duplicate vertices: False
  Has duplicate faces: False
  Has holes: False
  Degenerate faces: 0

============================================================
TESTING REPAIR ON: Cube
============================================================
Fixed normals

Repair Results:
  Vertices: 8 -> 8
  Faces: 12 -> 12
  Vertices removed: 0
  Faces removed: 0

After repair:
  Watertight: True
  Winding consistent: True
  Degenerate faces: 0

============================================================
```

## Next Steps

After testing mesh repair, consider:
- Enabling mesh decimation for further optimization
- Adjusting compression settings
- Testing export to web viewer

See `DECIMATION_SETUP.md` for decimation setup and `README.md` for general usage.

