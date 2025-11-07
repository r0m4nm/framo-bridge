"""
Fast Mesh Decimation Module

Unified interface for mesh decimation with automatic method selection.
Routes to the best available decimation method:
- Trimesh: Fast quadric decimation (10-50x faster, requires library)
- BMesh: Modifier-based decimation (slower but always available)
"""

import bpy
import bmesh
from typing import Tuple, List

# Import decimation implementations
from . import bmesh_decimation
from . import trimesh_decimation


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
    
    # Check for non-manifold geometry
    non_manifold_verts = sum(1 for v in bm.verts if not v.is_manifold)
    non_manifold_edges = sum(1 for e in bm.edges if not e.is_manifold)
    
    if non_manifold_verts > 0:
        issues.append(f"{non_manifold_verts} non-manifold vertices")
    if non_manifold_edges > 0:
        issues.append(f"{non_manifold_edges} non-manifold edges")
    
    bm.free()
    
    if not issues:
        return f"{len(mesh.polygons)} faces, {len(mesh.vertices)} vertices, no obvious issues"
    
    return f"{len(mesh.polygons)} faces, {len(mesh.vertices)} vertices - Issues: {', '.join(issues)}"


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


def fast_decimate_object(
    obj,
    target_ratio: float,
    method: str = 'auto',
    preserve_uv_seams: bool = True,
    preserve_sharp_edges: bool = True,
    aggression: int = 7,
    preserve_border: bool = True,
    verbose: bool = True
) -> Tuple[bool, int, int, str]:
    """
    High-performance mesh decimation with automatic method selection
    
    Args:
        obj: Blender object with mesh data
        target_ratio: Face reduction ratio (0.0-1.0)
        method: Decimation method
            'auto' - Use trimesh if available, else bmesh modifier (recommended)
            'trimesh' - Fast quadric decimation (requires trimesh library)
            'bmesh' - Slower but always available (uses Decimate Modifier)
        preserve_uv_seams: Preserve UV seams (bmesh only)
        preserve_sharp_edges: Preserve sharp edges (bmesh only)
        aggression: Decimation aggression for trimesh (1-10, lower=better quality)
        preserve_border: Preserve border edges for trimesh
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
    
    # Auto-select best available method
    if method == 'auto':
        if trimesh_decimation.is_available():
            method = 'trimesh'
            if verbose:
                print(f"○ Auto-selected TRIMESH method (fast)")
        else:
            method = 'bmesh'
            if verbose:
                print(f"○ Auto-selected BMESH method (modifier-based)")
    
    if verbose:
        print(f"○ Starting decimation with {method.upper()} method (target ratio: {target_ratio:.2%})")
    
    # Execute decimation
    success = False
    error_details = ""
    faces_after = faces_before
    
    if method == 'trimesh':
        if not trimesh_decimation.is_available():
            error_details = "Trimesh library not installed"
            if verbose:
                print(f"❌ {error_details}")
            return False, faces_before, faces_before, error_details
        
        success, faces_before, faces_after = trimesh_decimation.decimate_trimesh(
            obj, 
            target_ratio, 
            aggression=aggression,
            preserve_border=preserve_border,
            verbose=verbose
        )
        
    elif method == 'bmesh':
        success, faces_before, faces_after = bmesh_decimation.decimate_bmesh(
            obj, target_ratio, preprocess=True, verbose=verbose
        )
        
    else:
        error_details = f"Unknown decimation method: '{method}'"
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


def get_available_decimation_methods() -> List[str]:
    """
    Get list of available decimation methods
    
    Returns:
        List of method names
    """
    methods = []
    
    if trimesh_decimation.is_available():
        methods.append('trimesh')
    
    methods.append('bmesh')  # Always available
    
    return methods


def get_decimation_info() -> dict:
    """
    Get information about available decimation methods
    
    Returns:
        Dictionary with method information
    """
    return {
        'available_methods': get_available_decimation_methods(),
        'trimesh_available': trimesh_decimation.is_available(),
        'trimesh_version': trimesh_decimation.get_version(),
        'bmesh_available': True,  # Always available
        'recommended_method': 'trimesh' if trimesh_decimation.is_available() else 'bmesh'
    }


# Module metadata
__all__ = [
    'fast_decimate_object',
    'get_available_decimation_methods',
    'get_decimation_info',
    'diagnose_mesh_issues',
]

# Print availability on import
if __name__ != "__main__":
    info = get_decimation_info()
    methods_str = ', '.join(info['available_methods'])
    print(f"Fast decimation methods available: {methods_str}")
    if info['trimesh_available']:
        print(f"  Recommended: TRIMESH (version {info['trimesh_version']})")
    else:
        print(f"  Recommended: BMESH (install trimesh for faster decimation)")
