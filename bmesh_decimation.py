"""
BMesh-Based Mesh Decimation Module

Uses Blender's Decimate Modifier for reliable mesh decimation.
Always available, no external dependencies required.

Performance: Slower than Trimesh but works in all cases.
"""

import bpy
import bmesh
from typing import Tuple


def _preprocess_mesh_bmesh(bm) -> Tuple[bool, str]:
    """
    Preprocess bmesh to fix common issues before decimation
    
    Returns:
        (success, info_message)
    """
    try:
        issues_fixed = []
        
        # Triangulate non-triangular faces (quads, ngons)
        non_tris = [f for f in bm.faces if len(f.verts) > 3]
        if non_tris:
            result = bmesh.ops.triangulate(bm, faces=non_tris)
            if result.get('faces'):
                issues_fixed.append(f"triangulated {len(non_tris)} faces")
        
        # Remove degenerate geometry (zero area faces, edges, etc.)
        try:
            degenerate_dissolved = bmesh.ops.dissolve_degenerate(bm, dist=0.0001, edges=bm.edges[:])
            if degenerate_dissolved and degenerate_dissolved.get('edges'):
                issues_fixed.append(f"removed {len(degenerate_dissolved['edges'])} degenerate edges")
        except:
            pass  # dissolve_degenerate may not return anything
        
        # Remove loose vertices and edges (not connected to faces)
        loose_verts = [v for v in bm.verts if not v.link_faces]
        loose_edges = [e for e in bm.edges if not e.link_faces]
        
        if loose_verts:
            bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')
            issues_fixed.append(f"removed {len(loose_verts)} loose vertices")
        
        if loose_edges:
            bmesh.ops.delete(bm, geom=loose_edges, context='EDGES')
            issues_fixed.append(f"removed {len(loose_edges)} loose edges")
        
        # Merge duplicate vertices
        try:
            removed = bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0001)
            if removed and removed.get('verts'):
                issues_fixed.append(f"merged {len(removed['verts'])} duplicate vertices")
        except:
            pass  # remove_doubles may not return anything
        
        # Recalculate normals
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        
        info = ", ".join(issues_fixed) if issues_fixed else "no issues"
        return True, info
        
    except Exception as e:
        return False, f"preprocessing failed: {e}"


def preprocess_mesh(obj) -> Tuple[bool, str]:
    """
    Preprocess mesh to fix common issues that prevent decimation
    
    Args:
        obj: Blender object with mesh data
    
    Returns:
        (success, info_message)
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        return False, "Invalid object"
    
    try:
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        # Run preprocessing
        success, info = _preprocess_mesh_bmesh(bm)
        
        if success:
            # Write back to mesh
            bm.to_mesh(mesh)
            mesh.update()
        
        bm.free()
        
        return success, info
        
    except Exception as e:
        return False, f"Preprocessing failed: {e}"


def decimate_with_modifier(obj, target_ratio: float, verbose: bool = True) -> bool:
    """
    Decimate using Blender's Decimate Modifier (always available, reliable)
    
    Args:
        obj: Blender object
        target_ratio: Face reduction ratio (0.0-1.0)
        verbose: Print progress messages
    
    Returns:
        Success status
    """
    try:
        if verbose:
            print(f"  → Using Decimate Modifier method...")
        
        # Validate inputs
        if not obj or obj.type != 'MESH':
            if verbose:
                print(f"❌ Invalid object for decimation")
            return False
        
        # Clamp ratio
        target_ratio = max(0.0, min(1.0, target_ratio))
        
        # Add decimate modifier
        modifier = obj.modifiers.new(name="TempDecimate", type='DECIMATE')
        modifier.ratio = target_ratio
        modifier.decimate_type = 'COLLAPSE'
        
        # Apply the modifier
        mesh_before = len(obj.data.polygons)
        
        # Store current selection state
        previous_selection = bpy.context.view_layer.objects.active
        previous_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
        
        # Select and make active
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Ensure object mode
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Apply modifier
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        
        mesh_after = len(obj.data.polygons)
        
        # Restore selection
        if previous_selection:
            bpy.context.view_layer.objects.active = previous_selection
        
        if verbose:
            reduction_pct = ((mesh_before - mesh_after) / mesh_before * 100) if mesh_before > 0 else 0
            print(f"○ Modifier decimation: {mesh_before} → {mesh_after} faces ({reduction_pct:.1f}% reduction)")
        
        return True
        
    except Exception as e:
        if verbose:
            print(f"❌ Modifier decimation failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        # Try to remove modifier if it exists
        try:
            if 'modifier' in locals() and modifier.name in obj.modifiers:
                obj.modifiers.remove(modifier)
        except:
            pass
        
        return False


def decimate_bmesh(obj, target_ratio: float, preprocess: bool = True, verbose: bool = True) -> Tuple[bool, int, int]:
    """
    Main entry point for BMesh-based (modifier) decimation
    
    Args:
        obj: Blender object with mesh data
        target_ratio: Face reduction ratio (0.0-1.0)
        preprocess: Run mesh preprocessing before decimation
        verbose: Print progress messages
    
    Returns:
        (success, faces_before, faces_after)
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        if verbose:
            print("❌ Invalid object for decimation")
        return False, 0, 0
    
    faces_before = len(obj.data.polygons)
    
    # Optional preprocessing
    if preprocess:
        if verbose:
            print(f"  → Preprocessing mesh...")
        success, info = preprocess_mesh(obj)
        if verbose:
            if success:
                print(f"○ Preprocessing: {info}")
            else:
                print(f"⚠ Preprocessing issues: {info}")
    
    # Decimate
    success = decimate_with_modifier(obj, target_ratio, verbose)
    
    faces_after = len(obj.data.polygons)
    
    return success, faces_before, faces_after


# Module metadata
__all__ = [
    'decimate_bmesh',
    'decimate_with_modifier',
    'preprocess_mesh',
]

if __name__ != "__main__":
    print("○ BMesh decimation module loaded (modifier-based)")

