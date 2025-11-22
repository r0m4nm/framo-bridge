"""
UV Unwrapping Module

Provides automatic UV unwrapping for meshes that don't have UV maps.
Uses Blender's Smart UV Project for intelligent automatic unwrapping.
"""

import bpy
import bmesh


def has_uv_map(obj) -> bool:
    """
    Check if an object has any UV map
    
    Args:
        obj: Blender object
    
    Returns:
        True if object has at least one UV map, False otherwise
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        return False
    
    return len(obj.data.uv_layers) > 0


def smart_uv_unwrap(obj, angle_limit: float = 66.0, island_margin: float = 0.02, verbose: bool = True) -> bool:
    """
    Apply Smart UV Project to an object
    
    Args:
        obj: Blender object
        angle_limit: Max angle between faces in same island (degrees)
        island_margin: Margin between UV islands (0.0-1.0)
        verbose: Print progress messages
    
    Returns:
        Success status
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        if verbose:
            print(f"❌ Invalid object for UV unwrapping")
        return False
    
    try:
        # Store current state
        previous_active = bpy.context.view_layer.objects.active
        previous_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
        previous_selection = [o for o in bpy.context.selected_objects]
        
        # Manage visibility
        was_hidden = obj.hide_viewport
        if was_hidden:
            obj.hide_viewport = False
        
        # Select only this object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Ensure object mode
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Create UV map if none exists
        if len(obj.data.uv_layers) == 0:
            obj.data.uv_layers.new(name="UVMap")
            if verbose:
                print(f"  → Created new UV map for {obj.name}")
        
        # Switch to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        # Select all faces
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Apply Smart UV Project
        bpy.ops.uv.smart_project(
            angle_limit=angle_limit,
            island_margin=island_margin,
            area_weight=0.0,
            correct_aspect=True,
            scale_to_bounds=False
        )
        
        if verbose:
            print(f"○ Smart UV unwrapped: {obj.name}")
        
        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Restore previous state
        bpy.ops.object.select_all(action='DESELECT')
        for o in previous_selection:
            if o.name in bpy.data.objects:
                o.select_set(True)
        
        if previous_active and previous_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = previous_active
            
        # Restore visibility
        if was_hidden:
            obj.hide_viewport = True
        
        return True
        
    except Exception as e:
        if verbose:
            print(f"❌ UV unwrapping failed for {obj.name}: {e}")
            import traceback
            traceback.print_exc()
        
        # Try to restore object mode
        try:
            if bpy.context.object and bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass
        
        return False


def auto_unwrap_objects(objects, angle_limit: float = 66.0, island_margin: float = 0.02, verbose: bool = True) -> dict:
    """
    Automatically unwrap multiple objects that don't have UV maps
    
    Args:
        objects: List of Blender objects
        angle_limit: Max angle between faces in same island (degrees)
        island_margin: Margin between UV islands (0.0-1.0)
        verbose: Print progress messages
    
    Returns:
        Dictionary with stats: {'unwrapped': count, 'skipped': count, 'failed': count}
    """
    stats = {
        'unwrapped': 0,
        'skipped': 0,
        'failed': 0
    }
    
    mesh_objects = [obj for obj in objects if obj.type == 'MESH']
    
    if verbose and mesh_objects:
        print(f"\n{'='*60}")
        print(f"AUTO UV UNWRAPPING")
        print(f"{'='*60}")
    
    for obj in mesh_objects:
        if has_uv_map(obj):
            if verbose:
                print(f"○ Skipping {obj.name}: Already has UV map")
            stats['skipped'] += 1
        else:
            if verbose:
                print(f"  → Unwrapping {obj.name}...")
            
            success = smart_uv_unwrap(obj, angle_limit, island_margin, verbose)
            
            if success:
                stats['unwrapped'] += 1
            else:
                stats['failed'] += 1
    
    if verbose and mesh_objects:
        print(f"{'='*60}")
        print(f"UV Unwrapping complete: {stats['unwrapped']} unwrapped, {stats['skipped']} skipped, {stats['failed']} failed")
        print(f"{'='*60}\n")
    
    return stats


# Module metadata
__all__ = [
    'has_uv_map',
    'smart_uv_unwrap',
    'auto_unwrap_objects',
]

if __name__ != "__main__":
    print("○ UV unwrapping module loaded")

