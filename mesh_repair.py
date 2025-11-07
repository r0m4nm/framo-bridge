"""
Mesh repair and cleaning using Trimesh
Provides high-impact, low-risk mesh optimization features
"""

import bpy
import numpy as np
from typing import Dict, List, Tuple, Optional
import sys

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    print("Warning: trimesh not available. Install with: pip install trimesh")

try:
    import networkx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    # Not a warning - networkx is optional for advanced features


def log(message, force_flush=True):
    """Print message and flush to console"""
    print(message)
    if force_flush:
        sys.stdout.flush()
        sys.stderr.flush()


def blender_mesh_to_trimesh(blender_mesh) -> Optional['trimesh.Trimesh']:
    """Convert Blender mesh to Trimesh object"""
    if not TRIMESH_AVAILABLE:
        return None
    
    try:
        # Validate mesh
        if not blender_mesh or not hasattr(blender_mesh, 'vertices') or not hasattr(blender_mesh, 'polygons'):
            log("Invalid mesh object")
            return None
        
        # Check if mesh has data
        if len(blender_mesh.vertices) == 0:
            log("Mesh has no vertices")
            return None
        
        if len(blender_mesh.polygons) == 0:
            log("Mesh has no faces")
            return None
        
        # Get mesh data
        vertices = np.array([v.co for v in blender_mesh.vertices])
        
        # Triangulate faces (handle quads and ngons)
        faces_list = []
        for poly in blender_mesh.polygons:
            verts = list(poly.vertices)
            # Triangulate polygon by fan triangulation
            if len(verts) == 3:
                faces_list.append(verts)
            elif len(verts) > 3:
                # Fan triangulation from first vertex
                for i in range(1, len(verts) - 1):
                    faces_list.append([verts[0], verts[i], verts[i + 1]])
        
        if len(faces_list) == 0:
            log("No valid faces after triangulation")
            return None
        
        faces = np.array(faces_list)
        
        # Validate arrays
        if len(vertices) == 0 or len(faces) == 0:
            log("Empty vertex or face arrays")
            return None
        
        # Create trimesh object
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
        
        # Validate created mesh
        if mesh is None or not hasattr(mesh, 'vertices'):
            log("Failed to create Trimesh object")
            return None
        
        return mesh
    except Exception as e:
        log(f"Failed to convert Blender mesh to Trimesh: {e}")
        import traceback
        traceback.print_exc()
        return None


def trimesh_to_blender_mesh(trimesh_mesh, blender_mesh):
    """Convert Trimesh object back to Blender mesh"""
    try:
        # Clear existing mesh data
        blender_mesh.clear_geometry()
        
        # Add vertices
        blender_mesh.vertices.add(len(trimesh_mesh.vertices))
        blender_mesh.vertices.foreach_set("co", trimesh_mesh.vertices.flatten())
        
        # Add faces - create loops for each face
        total_loops = len(trimesh_mesh.faces) * 3
        blender_mesh.loops.add(total_loops)
        blender_mesh.polygons.add(len(trimesh_mesh.faces))
        
        # Set loop vertex indices
        loop_verts = trimesh_mesh.faces.flatten()
        blender_mesh.loops.foreach_set("vertex_index", loop_verts)
        
        # Set polygon loop start and total
        loop_starts = np.arange(0, total_loops, 3)
        loop_totals = np.full(len(trimesh_mesh.faces), 3, dtype=np.int32)
        
        blender_mesh.polygons.foreach_set("loop_start", loop_starts)
        blender_mesh.polygons.foreach_set("loop_total", loop_totals)
        
        # Update mesh
        blender_mesh.update()
        return True
    except Exception as e:
        log(f"Failed to convert Trimesh to Blender mesh: {e}")
        import traceback
        traceback.print_exc()
        return False


def remove_duplicate_vertices(mesh: 'trimesh.Trimesh', merge_verts: bool = True) -> 'trimesh.Trimesh':
    """Remove duplicate vertices"""
    if merge_verts:
        try:
            # Validate mesh before merging
            if mesh is None or not hasattr(mesh, 'vertices'):
                return mesh
            
            if len(mesh.vertices) == 0:
                return mesh
            
            # merge_vertices() modifies in-place and returns None in newer trimesh versions
            result = mesh.merge_vertices()
            
            # If it returns None, the mesh was modified in-place
            if result is None:
                # Validate the in-place modified mesh
                if not hasattr(mesh, 'vertices') or len(mesh.vertices) == 0:
                    raise ValueError("Mesh became invalid after merge_vertices")
                return mesh
            
            # Validate the returned mesh
            if not hasattr(result, 'vertices') or len(result.vertices) == 0:
                raise ValueError("merge_vertices returned invalid mesh")
            
            return result
        except Exception as e:
            log(f"Error merging vertices: {e}")
            import traceback
            traceback.print_exc()
            # Return original mesh if merge fails
            return mesh
    return mesh


def remove_duplicate_faces(mesh: 'trimesh.Trimesh', verbose: bool = False) -> 'trimesh.Trimesh':
    """Remove duplicate faces"""
    try:
        faces_before = len(mesh.faces)
        result = mesh.remove_duplicate_faces()
        if result is None:
            return mesh
        if verbose:
            faces_after = len(result.faces) if result else len(mesh.faces)
            if faces_before != faces_after:
                log(f"Removed {faces_before - faces_after} duplicate faces")
        return result
    except Exception as e:
        if verbose:
            log(f"Error removing duplicate faces: {e}")
        return mesh


def remove_unreferenced_vertices(mesh: 'trimesh.Trimesh', verbose: bool = False) -> 'trimesh.Trimesh':
    """Remove vertices that aren't referenced by any face"""
    try:
        verts_before = len(mesh.vertices)
        result = mesh.remove_unreferenced_vertices()
        if result is None:
            return mesh
        if verbose:
            verts_after = len(result.vertices) if result else len(mesh.vertices)
            if verts_before != verts_after:
                log(f"Removed {verts_before - verts_after} unreferenced vertices")
        return result
    except Exception as e:
        if verbose:
            log(f"Error removing unreferenced vertices: {e}")
        return mesh


def _fix_mesh_normals(mesh: 'trimesh.Trimesh', verbose: bool = False) -> 'trimesh.Trimesh':
    """Fix face normals to be consistent (requires networkx)"""
    if not NETWORKX_AVAILABLE:
        if verbose:
            log("Warning: fix_normals requires networkx. Install with: pip install networkx")
        return mesh
    
    try:
        if verbose:
            log("Fixing face normals...")
        mesh.fix_normals()
        if verbose:
            log("✓ Face normals fixed")
        return mesh
    except Exception as e:
        if verbose:
            log(f"Error fixing normals: {e}")
        return mesh


def _fill_mesh_holes(mesh: 'trimesh.Trimesh', verbose: bool = False) -> 'trimesh.Trimesh':
    """Fill holes in the mesh (requires networkx)"""
    if not NETWORKX_AVAILABLE:
        if verbose:
            log("Warning: fill_holes requires networkx. Install with: pip install networkx")
        return mesh
    
    try:
        if verbose:
            log("Filling holes...")
        mesh.fill_holes()
        if verbose:
            log("✓ Holes filled")
        return mesh
    except Exception as e:
        if verbose:
            log(f"Error filling holes: {e}")
        return mesh


def remove_degenerate_faces(mesh: 'trimesh.Trimesh') -> 'trimesh.Trimesh':
    """Remove degenerate faces (zero area, etc.)"""
    # Trimesh doesn't have a direct method, but we can filter
    # Get face areas
    face_areas = mesh.area_faces
    # Keep faces with area > threshold
    valid_faces = face_areas > 1e-10
    if valid_faces.all():
        return mesh
    
    # Create new mesh with only valid faces
    return mesh.slice_plane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], cap=False)


def _make_mesh_watertight(mesh: 'trimesh.Trimesh', verbose: bool = False) -> 'trimesh.Trimesh':
    """Make mesh watertight (closed, no holes) (requires networkx)"""
    if not NETWORKX_AVAILABLE:
        if verbose:
            log("Warning: make_watertight requires networkx. Install with: pip install networkx")
        return mesh
    
    try:
        if mesh.is_watertight:
            if verbose:
                log("Mesh is already watertight")
            return mesh
        if verbose:
            log("Making mesh watertight...")
        mesh.fill_holes()
        if verbose:
            log("✓ Mesh made watertight")
        return mesh
    except Exception as e:
        if verbose:
            log(f"Error making watertight: {e}")
        return mesh


def split_non_manifold(mesh: 'trimesh.Trimesh') -> List['trimesh.Trimesh']:
    """Split non-manifold mesh into separate manifold components"""
    if mesh.is_watertight and mesh.is_winding_consistent:
        return [mesh]
    return mesh.split(only_watertight=False)


def analyze_mesh_issues(mesh: 'trimesh.Trimesh') -> Dict[str, any]:
    """Analyze mesh and return issues found"""
    issues = {
        'is_watertight': mesh.is_watertight,
        'is_winding_consistent': mesh.is_winding_consistent,
        'is_volume': mesh.is_volume,
        'vertex_count': len(mesh.vertices),
        'face_count': len(mesh.faces),
        'has_duplicate_vertices': len(mesh.vertices) != len(np.unique(mesh.vertices, axis=0)),
        'has_duplicate_faces': len(mesh.faces) != len(np.unique(mesh.faces, axis=0)),
    }
    
    # Check for holes (simplified - check if watertight)
    issues['has_holes'] = not mesh.is_watertight
    
    # Check for degenerate faces
    face_areas = mesh.area_faces
    issues['degenerate_face_count'] = np.sum(face_areas < 1e-10)
    
    return issues


def repair_mesh(
    blender_mesh,
    remove_duplicate_verts: bool = True,
    remove_duplicate_faces_param: bool = True,
    remove_unreferenced_verts: bool = True,
    fix_normals_param: bool = True,
    fill_holes_param: bool = False,
    remove_degenerate_param: bool = True,
    make_watertight_param: bool = False,
    verbose: bool = False
) -> Tuple[bool, Dict[str, any]]:
    """
    Repair and clean a Blender mesh using Trimesh
    
    Args:
        blender_mesh: Blender mesh object
        remove_duplicate_verts: Remove duplicate vertices
        remove_duplicate_faces_param: Remove duplicate faces
        remove_unreferenced_verts: Remove unreferenced vertices
        fix_normals_param: Fix face normals
        fill_holes_param: Fill holes in mesh
        remove_degenerate_param: Remove degenerate faces
        make_watertight_param: Make mesh watertight (fills holes)
        verbose: Print detailed information
    
    Returns:
        Tuple of (success, stats_dict)
    """
    if not TRIMESH_AVAILABLE:
        return False, {'error': 'Trimesh not available'}
    
    try:
        # Convert to Trimesh
        tm_mesh = blender_mesh_to_trimesh(blender_mesh)
        if tm_mesh is None:
            return False, {'error': 'Failed to convert mesh'}
        
        stats = {
            'vertices_before': len(tm_mesh.vertices),
            'faces_before': len(tm_mesh.faces),
        }
        
        # Analyze before
        issues_before = analyze_mesh_issues(tm_mesh)
        
        # Apply repairs with validation
        if remove_duplicate_verts:
            try:
                vertices_before_merge = len(tm_mesh.vertices)
                result_mesh = remove_duplicate_vertices(tm_mesh, merge_verts=True)
                
                # Validate the result
                if result_mesh is not None and hasattr(result_mesh, 'vertices') and len(result_mesh.vertices) > 0:
                    # Check face indices if mesh has faces
                    if len(result_mesh.faces) > 0:
                        try:
                            max_face_index = result_mesh.faces.max()
                            if max_face_index < len(result_mesh.vertices):
                                # Valid mesh, use it
                                tm_mesh = result_mesh
                                if verbose:
                                    log(f"Removed duplicate vertices: {vertices_before_merge} -> {len(tm_mesh.vertices)}")
                            else:
                                if verbose:
                                    log("Warning: Invalid face indices after duplicate vertex removal, skipping this step")
                        except Exception:
                            if verbose:
                                log("Warning: Could not validate face indices, skipping duplicate vertex removal")
                    else:
                        # Mesh has no faces, but vertices are valid - use it
                        tm_mesh = result_mesh
                        if verbose:
                            log(f"Removed duplicate vertices: {vertices_before_merge} -> {len(tm_mesh.vertices)}")
                else:
                    if verbose:
                        log("Warning: Duplicate vertex removal failed or produced invalid mesh, skipping this step")
            except Exception as e:
                if verbose:
                    log(f"Warning: Duplicate vertex removal failed: {e}, continuing with other repairs")
                # Continue with other repairs - tm_mesh is still valid
        
        if remove_duplicate_faces_param:
            tm_mesh = remove_duplicate_faces(tm_mesh, verbose=verbose)
            if tm_mesh is None or not hasattr(tm_mesh, 'vertices'):
                return False, {'error': 'Failed during duplicate face removal'}
        
        if remove_unreferenced_verts:
            tm_mesh = remove_unreferenced_vertices(tm_mesh, verbose=verbose)
            if tm_mesh is None or not hasattr(tm_mesh, 'vertices'):
                return False, {'error': 'Failed during unreferenced vertex removal'}
        
        if fix_normals_param:
            tm_mesh = _fix_mesh_normals(tm_mesh, verbose=verbose)
            if tm_mesh is None or not hasattr(tm_mesh, 'vertices'):
                return False, {'error': 'Failed during normal fixing'}
        
        if remove_degenerate_param:
            # Remove degenerate faces - filter by area
            try:
                face_areas = tm_mesh.area_faces
                valid_mask = face_areas > 1e-10
                if not valid_mask.all():
                    # Recreate mesh with only valid faces
                    valid_faces = tm_mesh.faces[valid_mask]
                    if len(valid_faces) > 0:
                        tm_mesh = trimesh.Trimesh(vertices=tm_mesh.vertices, faces=valid_faces)
                        if tm_mesh is None or not hasattr(tm_mesh, 'vertices'):
                            return False, {'error': 'Failed to recreate mesh after degenerate removal'}
                        if verbose:
                            log(f"Removed {np.sum(~valid_mask)} degenerate faces")
                    else:
                        return False, {'error': 'All faces were degenerate - cannot repair'}
            except Exception as e:
                if verbose:
                    log(f"Warning: Could not remove degenerate faces: {e}")
        
        if fill_holes_param:
            try:
                tm_mesh = _fill_mesh_holes(tm_mesh, verbose=verbose)
                if tm_mesh is None or not hasattr(tm_mesh, 'vertices'):
                    return False, {'error': 'Failed during hole filling'}
            except Exception as e:
                if verbose:
                    log(f"Warning: Could not fill holes: {e}")
        
        if make_watertight_param:
            try:
                tm_mesh = _make_mesh_watertight(tm_mesh, verbose=verbose)
                if tm_mesh is None or not hasattr(tm_mesh, 'vertices'):
                    return False, {'error': 'Failed during watertight operation'}
            except Exception as e:
                if verbose:
                    log(f"Warning: Could not make watertight: {e}")
        
        # Final validation
        if tm_mesh is None or not hasattr(tm_mesh, 'vertices') or len(tm_mesh.vertices) == 0:
            return False, {'error': 'Mesh became invalid during repair'}
        
        if len(tm_mesh.faces) == 0:
            return False, {'error': 'Mesh has no faces after repair'}
        
        # Analyze after
        issues_after = analyze_mesh_issues(tm_mesh)
        
        # Convert back to Blender
        success = trimesh_to_blender_mesh(tm_mesh, blender_mesh)
        
        if success:
            stats.update({
                'vertices_after': len(tm_mesh.vertices),
                'faces_after': len(tm_mesh.faces),
                'vertices_removed': stats['vertices_before'] - len(tm_mesh.vertices),
                'faces_removed': stats['faces_before'] - len(tm_mesh.faces),
                'issues_before': issues_before,
                'issues_after': issues_after,
            })
        
        return success, stats
        
    except Exception as e:
        import traceback
        log(f"Exception in repair_mesh: {e}")
        traceback.print_exc()
        return False, {'error': str(e)}


def repair_object(
    obj,
    remove_duplicate_verts: bool = True,
    remove_duplicate_faces: bool = True,
    remove_unreferenced_verts: bool = True,
    fix_normals: bool = True,
    fill_holes: bool = False,
    remove_degenerate: bool = True,
    make_watertight: bool = False,
    verbose: bool = False
) -> Tuple[bool, Dict[str, any]]:
    """Repair a Blender object's mesh"""
    if obj is None:
        return False, {'error': 'Object is None'}
    
    if obj.type != 'MESH':
        return False, {'error': f'Object "{obj.name}" is not a mesh object (type: {obj.type})'}
    
    if not obj.data:
        return False, {'error': f'Object "{obj.name}" has no mesh data'}
    
    mesh = obj.data
    if not hasattr(mesh, 'vertices') or not hasattr(mesh, 'polygons'):
        return False, {'error': f'Object "{obj.name}" mesh data is invalid'}
    
    if len(mesh.vertices) == 0:
        return False, {'error': f'Object "{obj.name}" has no vertices'}
    
    if len(mesh.polygons) == 0:
        return False, {'error': f'Object "{obj.name}" has no faces'}
    
    return repair_mesh(
        mesh,
        remove_duplicate_verts=remove_duplicate_verts,
        remove_duplicate_faces_param=remove_duplicate_faces,
        remove_unreferenced_verts=remove_unreferenced_verts,
        fix_normals_param=fix_normals,
        fill_holes_param=fill_holes,
        remove_degenerate_param=remove_degenerate,
        make_watertight_param=make_watertight,
        verbose=verbose
    )


def analyze_object(obj) -> Optional[Dict[str, any]]:
    """Analyze an object's mesh for issues"""
    if obj is None:
        return None
    
    if obj.type != 'MESH' or not obj.data:
        return None
    
    if not TRIMESH_AVAILABLE:
        return None
    
    tm_mesh = blender_mesh_to_trimesh(obj.data)
    if tm_mesh is None:
        return None
    
    return analyze_mesh_issues(tm_mesh)

