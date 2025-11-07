"""
Direct test script for decimation debugging
Run this in Blender's Scripting workspace to test decimation on selected object
"""

import bpy
import sys
import importlib

# Access addon modules through bpy
addon_prefs = bpy.context.preferences.addons
addon_name = None
for mod in addon_prefs:
    if 'framo' in mod.module.lower():
        addon_name = mod.module
        break

if not addon_name:
    addon_name = 'framo-exporter'

# Import the addon module
if addon_name in sys.modules:
    addon_module = sys.modules[addon_name]
    fast_decimation = addon_module.fast_decimation
    # Reload it
    importlib.reload(fast_decimation)
    print(f"✓ Reloaded {addon_name}.fast_decimation")
else:
    print(f"ERROR: Addon '{addon_name}' not loaded. Please enable the addon first.")
    raise ImportError(f"Addon {addon_name} not found in sys.modules")

# Now we have access to fast_decimation module

print("=" * 80)
print("DECIMATION TEST - Starting")
print("=" * 80)

# Get selected object
obj = bpy.context.active_object

if not obj:
    print("ERROR: No object selected. Please select an object first.")
else:
    print(f"\nTesting decimation on object: {obj.name}")
    print(f"Object type: {obj.type}")
    
    if obj.type != 'MESH':
        print(f"ERROR: Object is not a mesh (type: {obj.type})")
    else:
        mesh = obj.data
        print(f"Initial mesh: {len(mesh.polygons)} faces, {len(mesh.vertices)} vertices")
        
        # Diagnose
        print("\n" + "-" * 80)
        print("DIAGNOSIS:")
        diagnosis = fast_decimation.diagnose_mesh_issues(obj)
        print(f"  {diagnosis}")
        
        # Test decimation with 50% ratio
        print("\n" + "-" * 80)
        print("DECIMATION TEST (50% ratio):")
        print("-" * 80)
        
        success, faces_before, faces_after, error_details = fast_decimation.fast_decimate_object(
            obj,
            target_ratio=0.5,
            method='bmesh',
            preserve_uv_seams=False,
            preserve_sharp_edges=False
        )
        
        print("\n" + "-" * 80)
        print("RESULT:")
        print(f"  Success: {success}")
        print(f"  Faces before: {faces_before}")
        print(f"  Faces after: {faces_after}")
        if error_details:
            print(f"  Error: {error_details}")
        print("=" * 80)
        print("DECIMATION TEST - Complete")
        print("=" * 80)

