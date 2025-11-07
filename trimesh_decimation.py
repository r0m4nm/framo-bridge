"""
Trimesh-Based Mesh Decimation Module

Provides high-performance mesh decimation using the Trimesh library.
10-50x faster than modifier-based decimation for large meshes.

Requires: pip install trimesh
"""

import numpy as np
from typing import Tuple

# Check library availability
try:
    import trimesh
    TRIMESH_AVAILABLE = True
    TRIMESH_VERSION = trimesh.__version__
except ImportError:
    TRIMESH_AVAILABLE = False
    TRIMESH_VERSION = None


def is_available() -> bool:
    """Check if Trimesh library is available"""
    return TRIMESH_AVAILABLE


def get_version() -> str:
    """Get Trimesh library version"""
    return TRIMESH_VERSION if TRIMESH_AVAILABLE else "Not installed"


def _blender_to_numpy(mesh) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract mesh data as numpy arrays (triangulates if needed)
    
    Args:
        mesh: Blender mesh data
    
    Returns:
        (vertices, faces) as numpy arrays
    """
    vertices = np.zeros((len(mesh.vertices), 3), dtype=np.float64)
    mesh.vertices.foreach_get("co", vertices.ravel())
    
    # Check if all faces are triangles
    all_tris = all(len(p.vertices) == 3 for p in mesh.polygons)
    
    if all_tris:
        # Fast path for triangulated meshes
        faces = np.zeros((len(mesh.polygons), 3), dtype=np.int32)
        mesh.polygons.foreach_get("vertices", faces.ravel())
    else:
        # Triangulate non-triangular faces
        print(f"⚠ Mesh has non-triangular faces, triangulating...")
        faces_list = []
        for poly in mesh.polygons:
            verts = list(poly.vertices)
            # Simple fan triangulation
            for i in range(1, len(verts) - 1):
                faces_list.append([verts[0], verts[i], verts[i + 1]])
        faces = np.array(faces_list, dtype=np.int32)
    
    return vertices, faces


def _numpy_to_blender(mesh, vertices: np.ndarray, faces: np.ndarray):
    """
    Write numpy arrays back to Blender mesh
    
    Args:
        mesh: Blender mesh data
        vertices: Vertex positions (N, 3)
        faces: Face indices (M, 3)
    """
    mesh.clear_geometry()
    
    # Add vertices
    mesh.vertices.add(len(vertices))
    mesh.vertices.foreach_set("co", vertices.ravel())
    
    # Add faces and loops
    mesh.polygons.add(len(faces))
    mesh.loops.add(len(faces) * 3)
    
    # Set polygon data
    loop_starts = np.arange(0, len(faces) * 3, 3, dtype=np.int32)
    loop_totals = np.full(len(faces), 3, dtype=np.int32)
    
    mesh.polygons.foreach_set("loop_start", loop_starts)
    mesh.polygons.foreach_set("loop_total", loop_totals)
    mesh.polygons.foreach_set("vertices", faces.ravel())
    
    mesh.update()


def decimate_with_trimesh(
    mesh, 
    target_ratio: float, 
    aggression: int = 7,
    preserve_border: bool = True,
    verbose: bool = True
) -> bool:
    """
    Decimate using Trimesh library (fast, requires external library)
    
    Args:
        mesh: Blender mesh data
        target_ratio: Face reduction ratio (0.0-1.0)
        aggression: Decimation aggression level (1-10)
            Lower values (1-3): Conservative, preserves features better
            Medium values (4-7): Balanced quality/reduction (recommended: 7)
            Higher values (8-10): Aggressive, may alter geometry
        preserve_border: Preserve border edges during decimation
        verbose: Print progress messages
    
    Returns:
        Success status
    """
    if not TRIMESH_AVAILABLE:
        if verbose:
            print("❌ Trimesh not available. Install with: pip install trimesh")
        return False
    
    try:
        # Extract mesh data
        vertices, faces = _blender_to_numpy(mesh)
        
        initial_faces = len(faces)
        
        # Validate extracted data
        if len(vertices) == 0:
            if verbose:
                print(f"❌ Trimesh decimation failed: no vertices")
            return False
        
        if len(faces) == 0:
            if verbose:
                print(f"❌ Trimesh decimation failed: no faces")
            return False
        
        if verbose:
            print(f"  → Converting to Trimesh format...")
        
        # Create Trimesh object with preprocessing
        tm_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
        
        # TODO: Future enhancement - detect and mark important edges
        # - Sharp edges (angle > threshold)
        # - UV seam edges
        # - Material boundary edges
        # This would require additional logic to identify these edges from Blender
        # and potentially weight them differently in the decimation algorithm
        
        # Additional preprocessing (with error handling)
        if verbose:
            print(f"  → Preprocessing mesh...")
        
        try:
            # Remove degenerate faces
            if hasattr(tm_mesh, 'remove_degenerate_faces'):
                tm_mesh.remove_degenerate_faces()
        except Exception as e:
            if verbose:
                print(f"  ⚠ Degenerate face removal failed: {e}")
        
        try:
            # Merge duplicate vertices
            tm_mesh.merge_vertices()
        except Exception as e:
            if verbose:
                print(f"  ⚠ Vertex merging failed: {e}")
        
        try:
            # Remove unreferenced vertices
            tm_mesh.remove_unreferenced_vertices()
        except Exception as e:
            if verbose:
                print(f"  ⚠ Unreferenced vertex removal failed: {e}")
        
        try:
            # Fix normals
            if hasattr(tm_mesh, 'fix_normals'):
                tm_mesh.fix_normals()
        except Exception as e:
            if verbose:
                print(f"  ⚠ Normal fixing failed: {e}")
        
        if verbose:
            print(f"○ Preprocessed: {initial_faces} → {len(tm_mesh.faces)} faces")
        
        # Validate we still have a valid mesh
        if len(tm_mesh.faces) == 0:
            if verbose:
                print(f"❌ No faces left after preprocessing")
            return False
        
        # Calculate target face count
        target_faces = max(4, int(len(tm_mesh.faces) * target_ratio))
        
        if verbose:
            print(f"  → Running quadric decimation (target: {target_faces} faces)...")
        
        # Perform quadric edge collapse decimation
        try:
            # Check if the function accepts aggression parameter (varies by trimesh version)
            import inspect
            sig = inspect.signature(tm_mesh.simplify_quadric_decimation)
            params = sig.parameters
            
            decimation_kwargs = {'face_count': target_faces}
            
            # Add optional parameters if supported by this trimesh version
            if 'aggression' in params:
                decimation_kwargs['aggression'] = aggression
                if verbose:
                    print(f"  → Using aggression level: {aggression}")
            
            if 'preserve_border' in params and preserve_border:
                decimation_kwargs['preserve_border'] = True
                if verbose:
                    print(f"  → Border edge preservation: enabled")
            
            simplified = tm_mesh.simplify_quadric_decimation(**decimation_kwargs)
            
            # Validate result
            if simplified is None or len(simplified.vertices) == 0 or len(simplified.faces) == 0:
                if verbose:
                    print(f"❌ Simplification produced invalid mesh")
                return False
            
            if verbose:
                print(f"○ Quadric decimation: {len(tm_mesh.faces)} → {len(simplified.faces)} faces")
            
            # Write back to Blender
            if verbose:
                print(f"  → Converting back to Blender format...")
            _numpy_to_blender(mesh, simplified.vertices, simplified.faces)
            
            return True
            
        except Exception as e:
            if verbose:
                print(f"❌ Quadric decimation failed: {e}")
            
            # Try to at least return the preprocessed mesh
            if len(tm_mesh.faces) < initial_faces:
                if verbose:
                    print(f"○ Using preprocessed mesh: {initial_faces} → {len(tm_mesh.faces)} faces")
                _numpy_to_blender(mesh, tm_mesh.vertices, tm_mesh.faces)
                return True
            
            return False
        
    except Exception as e:
        if verbose:
            print(f"❌ Trimesh decimation failed: {e}")
            import traceback
            traceback.print_exc()
        return False


def decimate_trimesh(
    obj, 
    target_ratio: float, 
    aggression: int = 7,
    preserve_border: bool = True,
    verbose: bool = True
) -> Tuple[bool, int, int]:
    """
    Main entry point for Trimesh-based decimation
    
    Args:
        obj: Blender object with mesh data
        target_ratio: Face reduction ratio (0.0-1.0)
        aggression: Decimation aggression (1-10), lower=better quality
        preserve_border: Preserve border edges
        verbose: Print progress messages
    
    Returns:
        (success, faces_before, faces_after)
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        if verbose:
            print("❌ Invalid object for decimation")
        return False, 0, 0
    
    if not TRIMESH_AVAILABLE:
        if verbose:
            print("❌ Trimesh library not installed")
            print("   Install with: pip install trimesh")
        return False, 0, 0
    
    mesh = obj.data
    faces_before = len(mesh.polygons)
    
    # Decimate
    success = decimate_with_trimesh(
        mesh, 
        target_ratio, 
        aggression=aggression,
        preserve_border=preserve_border,
        verbose=verbose
    )
    
    faces_after = len(mesh.polygons)
    
    return success, faces_before, faces_after


# Module metadata
__all__ = [
    'decimate_trimesh',
    'decimate_with_trimesh',
    'is_available',
    'get_version',
    'TRIMESH_AVAILABLE',
]

if __name__ != "__main__":
    if TRIMESH_AVAILABLE:
        print(f"✓ Trimesh {TRIMESH_VERSION} available for fast decimation")
    else:
        print("○ Trimesh not available - install with: pip install trimesh")

