"""
Mesh Decimation Module

Unified interface for mesh decimation using Blender's native BMesh.
Uses Blender's Decimate Modifier for reliable results.
Always available, no external dependencies required.
"""

import bpy
import bmesh
from typing import Tuple, List


def _preprocess_mesh_bmesh(bm) -> Tuple[bool, str]:
    """
    Preprocess bmesh to fix common issues before decimation
    
    Returns:
        (success, info_message)
    """
    try:
        issues_fixed = []
        
        # Check for non-manifold geometry FIRST (critical for decimation)
        non_manifold_verts = [v for v in bm.verts if not v.is_manifold]
        non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
        
        if non_manifold_verts or non_manifold_edges:
            issues_fixed.append(f"detected {len(non_manifold_verts)} non-manifold verts, {len(non_manifold_edges)} non-manifold edges")
            
            # STRATEGY 1: Try aggressive merge by distance first
            # Many non-manifold issues are caused by duplicate/near-duplicate vertices
            if non_manifold_verts or non_manifold_edges:
                for merge_dist in [0.001, 0.01, 0.1]:  # Try progressively larger distances
                    try:
                        removed = bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=merge_dist)
                        removed_count = len(removed.get('verts', [])) if removed else 0
                        
                        if removed_count > 0:
                            # Check if this fixed the non-manifold issues
                            non_manifold_after = sum(1 for e in bm.edges if not e.is_manifold)
                            
                            if non_manifold_after == 0:
                                issues_fixed.append(f"merged {removed_count} vertices (distance: {merge_dist}) - fixed all non-manifold issues")
                                non_manifold_edges = []  # Clear for next checks
                                non_manifold_verts = []
                                break
                            elif non_manifold_after < len(non_manifold_edges):
                                issues_fixed.append(f"merged {removed_count} vertices (distance: {merge_dist}) - reduced non-manifold edges to {non_manifold_after}")
                                # Update lists
                                non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
                                non_manifold_verts = [v for v in bm.verts if not v.is_manifold]
                                break
                    except Exception as e:
                        print(f"  Warning: Merge by distance {merge_dist} failed: {e}")
            
            # STRATEGY 2: Handle remaining non-manifold edges
            if non_manifold_edges:
                # Separate boundary edges (1 face) from interior non-manifold edges (3+ faces)
                boundary_edges = [e for e in non_manifold_edges if len(e.link_faces) == 1]
                interior_edges = [e for e in non_manifold_edges if len(e.link_faces) > 2]
                
                # Handle interior non-manifold edges (3+ faces) - dissolve them
                if interior_edges:
                    try:
                        bmesh.ops.dissolve_edges(bm, edges=interior_edges, use_verts=True, use_face_split=False)
                        issues_fixed.append(f"dissolved {len(interior_edges)} interior non-manifold edges")
                    except Exception as e:
                        print(f"  Warning: Could not dissolve interior non-manifold edges: {e}")
                
                # Handle boundary edges (1 face) - DELETE the connected faces
                # This is more conservative than filling holes - just removes problematic geometry
                if boundary_edges:
                    try:
                        # Get faces connected to boundary edges
                        faces_to_delete = set()
                        for e in boundary_edges:
                            faces_to_delete.update(e.link_faces)
                        
                        if faces_to_delete:
                            bmesh.ops.delete(bm, geom=list(faces_to_delete), context='FACES')
                            issues_fixed.append(f"removed {len(faces_to_delete)} faces with boundary edges (non-manifold)")
                    except Exception as e:
                        print(f"  Warning: Could not delete boundary faces: {e}")
            
            # Remove remaining non-manifold vertices (loose verts with no faces)
            non_manifold_verts_remaining = [v for v in bm.verts if not v.is_manifold and not v.link_faces]
            if non_manifold_verts_remaining:
                try:
                    bmesh.ops.delete(bm, geom=non_manifold_verts_remaining, context='VERTS')
                    issues_fixed.append(f"removed {len(non_manifold_verts_remaining)} non-manifold vertices")
                except Exception as e:
                    print(f"  Warning: Could not remove non-manifold vertices: {e}")
        
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
        
        # Store current selection state using NAMES (safer - objects might change)
        previous_selected_names = [o.name for o in bpy.context.selected_objects]
        previous_active_name = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None

        # Manage visibility
        was_hidden = obj.hide_viewport
        if was_hidden:
            obj.hide_viewport = False

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

        # Restore full selection state using names
        bpy.ops.object.select_all(action='DESELECT')
        for obj_name in previous_selected_names:
            if obj_name in bpy.data.objects:
                try:
                    bpy.data.objects[obj_name].select_set(True)
                except Exception:
                    pass
        if previous_active_name and previous_active_name in bpy.data.objects:
            try:
                bpy.context.view_layer.objects.active = bpy.data.objects[previous_active_name]
            except Exception:
                pass
            
        # Restore visibility
        if was_hidden:
            obj.hide_viewport = True
        
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


def diagnose_mesh_issues(obj) -> str:
    """
    Diagnose common mesh issues that prevent decimation
    
    Args:
        obj: Blender object
    
    Returns:
        Diagnostic message string
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        return "Invalid object"
    
    mesh = obj.data
    issues = []
    critical_issues = []
    
    # Check face types
    tris = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
    quads = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
    ngons = sum(1 for p in mesh.polygons if len(p.vertices) > 4)
    
    if quads > 0 or ngons > 0:
        issues.append(f"{quads} quads, {ngons} ngons (need triangulation)")
    
    # Check for loose geometry
    bm = bmesh.new()
    bm.from_mesh(mesh)
    
    loose_verts = sum(1 for v in bm.verts if not v.link_faces)
    loose_edges = sum(1 for e in bm.edges if not e.link_faces)
    
    if loose_verts > 0:
        issues.append(f"{loose_verts} loose vertices")
    if loose_edges > 0:
        issues.append(f"{loose_edges} loose edges")
    
    # Check for non-manifold geometry (CRITICAL for decimation)
    non_manifold_verts = sum(1 for v in bm.verts if not v.is_manifold)
    non_manifold_edges = sum(1 for e in bm.edges if not e.is_manifold)
    
    if non_manifold_verts > 0:
        critical_issues.append(f"⚠ CRITICAL: {non_manifold_verts} non-manifold vertices")
    if non_manifold_edges > 0:
        critical_issues.append(f"⚠ CRITICAL: {non_manifold_edges} non-manifold edges (may cause crash)")
    
    # Check for zero-area faces
    zero_area_faces = sum(1 for f in bm.faces if f.calc_area() < 0.000001)
    if zero_area_faces > 0:
        issues.append(f"{zero_area_faces} zero-area faces")
    
    bm.free()
    
    all_issues = critical_issues + issues
    
    if not all_issues:
        return f"{len(mesh.polygons)} faces, {len(mesh.vertices)} vertices, no obvious issues"
    
    return f"{len(mesh.polygons)} faces, {len(mesh.vertices)} vertices - Issues: {', '.join(all_issues)}"


def _validate_mesh(obj) -> Tuple[bool, str]:
    """
    Validate that object has valid mesh data
    
    Returns:
        (is_valid, error_message)
    """
    if not obj:
        return False, "Object is None"
    
    if obj.type != 'MESH':
        return False, f"Object '{obj.name}' is not a mesh (type: {obj.type})"
    
    if not obj.data:
        return False, f"Object '{obj.name}' has no mesh data"
    
    if len(obj.data.polygons) == 0:
        return False, f"Object '{obj.name}' has no faces"
    
    return True, ""


def decimate_object(
    obj,
    target_ratio: float,
    method: str = 'bmesh',
    preserve_uv_seams: bool = True,
    preserve_sharp_edges: bool = True,
    aggression: int = 7,
    preserve_border: bool = True,
    verbose: bool = True
) -> Tuple[bool, int, int, str]:
    """
    Main entry point for mesh decimation
    
    Args:
        obj: Blender object with mesh data
        target_ratio: Face reduction ratio (0.0-1.0)
        method: Decimation method (always 'bmesh')
        preserve_uv_seams: Preserve UV seams (not currently used, kept for compatibility)
        preserve_sharp_edges: Preserve sharp edges (not currently used, kept for compatibility)
        aggression: Not used (kept for compatibility)
        preserve_border: Not used (kept for compatibility)
        verbose: Print progress messages
    
    Returns:
        (success, faces_before, faces_after, error_details)
    """
    # Validate mesh
    is_valid, error_msg = _validate_mesh(obj)
    if not is_valid:
        if verbose:
            print(f"❌ Validation failed: {error_msg}")
        return False, 0, 0, error_msg
    
    # Diagnose mesh issues
    if verbose:
        diagnosis = diagnose_mesh_issues(obj)
        print(f"○ Mesh diagnosis for '{obj.name}': {diagnosis}")
    
    mesh = obj.data
    faces_before = len(mesh.polygons)
    
    # Clamp ratio to valid range
    target_ratio = max(0.0, min(1.0, target_ratio))
    
    # Always use bmesh method
    if method == 'auto' or method == 'trimesh':
        method = 'bmesh'
        if verbose:
            print(f"○ Using BMESH method (modifier-based)")
    
    if verbose:
        print(f"○ Starting decimation with BMESH method (target ratio: {target_ratio:.2%})")
    
    # Execute decimation
    success = False
    error_details = ""
    faces_after = faces_before
    
    if method == 'bmesh':
        success, faces_before, faces_after = decimate_bmesh(
            obj, target_ratio, preprocess=True, verbose=verbose
        )
    else:
        error_details = f"Unknown decimation method: '{method}'. Only 'bmesh' is supported."
        if verbose:
            print(f"❌ {error_details}")
        return False, faces_before, faces_before, error_details
    
    if success:
        if verbose:
            reduction = ((faces_before - faces_after) / faces_before * 100) if faces_before > 0 else 0
            print(f"✓ Decimated '{obj.name}': {faces_before:,} → {faces_after:,} faces ({reduction:.1f}% reduction)")
    else:
        error_details = f"Decimation failed. Check console for details."
        if verbose:
            print(f"❌ Decimation of '{obj.name}' failed")
    
    return success, faces_before, faces_after, error_details


def decimate_bmesh(obj, target_ratio: float, preprocess: bool = True, verbose: bool = True) -> Tuple[bool, int, int]:
    """
    BMesh-based (modifier) decimation
    
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


def get_available_decimation_methods() -> List[str]:
    """
    Get list of available decimation methods
    
    Returns:
        List of method names (always ['bmesh'])
    """
    return ['bmesh']


def get_decimation_info() -> dict:
    """
    Get information about available decimation methods
    
    Returns:
        Dictionary with method information
    """
    return {
        'available_methods': ['bmesh'],
        'bmesh_available': True,
        'recommended_method': 'bmesh'
    }


def get_original_meshes_from_instances(objects: List) -> List:
    """
    Get original mesh objects from collection instances.
    
    When an EMPTY object is a collection instance, it references a collection
    containing mesh objects. This function extracts those original mesh objects
    so they can be processed (e.g., decimated).
    
    Args:
        objects: List of objects (typically EMPTY objects with collection instances)
    
    Returns:
        List of mesh objects found in the instanced collections
    """
    mesh_objects = []
    
    for obj in objects:
        # Check if this is a collection instance
        if obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION' and obj.instance_collection:
            # Get all mesh objects from the instanced collection
            for coll_obj in obj.instance_collection.all_objects:
                if coll_obj.type == 'MESH' and coll_obj.data:
                    # Avoid duplicates
                    if coll_obj not in mesh_objects:
                        mesh_objects.append(coll_obj)
    
    return mesh_objects


# Module metadata
__all__ = [
    'decimate_object',
    'decimate_bmesh',
    'decimate_with_modifier',
    'preprocess_mesh',
    'diagnose_mesh_issues',
    'get_available_decimation_methods',
    'get_decimation_info',
    'get_original_meshes_from_instances',
]

# Print availability on import
if __name__ != "__main__":
    info = get_decimation_info()
    methods_str = ', '.join(info['available_methods'])
    print(f"Decimation module loaded: {methods_str}")
    print(f"  Using: BMESH (Blender native decimation)")

