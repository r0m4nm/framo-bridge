"""
UV Atlas Module for GLB Export Optimization

This module provides material-based UV atlas packing to reduce draw calls.
Objects sharing the same material are grouped and packed into shared UV atlases,
significantly improving rendering performance in game engines and WebGL.

Strategy:
- Groups objects by shared materials
- Creates temporary joined meshes for each material group
- Uses Lightmap Pack for optimal UV atlas packing
- Preserves original scene (works on copies)
- Falls back to individual unwrapping for small groups or complex cases
"""

import bpy
from typing import List, Dict, Set, Tuple, Optional


def has_uv_map(obj) -> bool:
    """
    Check if an object has any UV map.

    Args:
        obj: Blender object

    Returns:
        True if object has at least one UV map, False otherwise
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        return False

    return len(obj.data.uv_layers) > 0


def get_primary_material(obj) -> Optional[bpy.types.Material]:
    """
    Get the primary (most used) material from an object.

    Args:
        obj: Blender mesh object

    Returns:
        Primary material or None
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        return None

    if not obj.material_slots:
        return None

    # Count material usage by face
    material_usage = {}
    for poly in obj.data.polygons:
        mat_index = poly.material_index
        if mat_index < len(obj.material_slots):
            mat = obj.material_slots[mat_index].material
            if mat:
                material_usage[mat] = material_usage.get(mat, 0) + 1

    if not material_usage:
        # No faces with materials, return first material
        return obj.material_slots[0].material if obj.material_slots[0].material else None

    # Return most used material
    return max(material_usage, key=material_usage.get)


def group_objects_by_material(objects: List[bpy.types.Object],
                              min_group_size: int = 2) -> Dict[bpy.types.Material, List[bpy.types.Object]]:
    """
    Group objects by their primary material.

    Args:
        objects: List of Blender objects
        min_group_size: Minimum objects required to form a group

    Returns:
        Dictionary mapping materials to lists of objects: {material: [obj1, obj2, ...]}
    """
    material_groups: Dict[bpy.types.Material, List[bpy.types.Object]] = {}
    single_objects: List[bpy.types.Object] = []

    for obj in objects:
        if obj.type != 'MESH':
            continue

        # Skip if already has UV map (respect existing UVs)
        if has_uv_map(obj):
            continue

        primary_mat = get_primary_material(obj)

        if primary_mat:
            if primary_mat not in material_groups:
                material_groups[primary_mat] = []
            material_groups[primary_mat].append(obj)
        else:
            # Objects without materials go to individual processing
            single_objects.append(obj)

    # Filter groups by minimum size
    valid_groups = {mat: objs for mat, objs in material_groups.items()
                    if len(objs) >= min_group_size}

    # Add small groups to single objects for individual processing
    for mat, objs in material_groups.items():
        if len(objs) < min_group_size:
            single_objects.extend(objs)

    return valid_groups, single_objects


def create_temp_joined_mesh(objects: List[bpy.types.Object],
                           material_name: str,
                           verbose: bool = True) -> Optional[bpy.types.Object]:
    """
    Create a temporary joined mesh from multiple objects.

    Args:
        objects: List of objects to join
        material_name: Name of the shared material (for naming)
        verbose: Print progress messages

    Returns:
        Joined object or None on failure
    """
    if not objects:
        return None

    try:
        # Store current state using NAMES (safer - objects might change during operation)
        previous_active_name = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
        previous_selection_names = [o.name for o in bpy.context.selected_objects]

        # Create copies of objects (hidden from user view)
        temp_copies = []
        for obj in objects:
            copy = obj.copy()
            copy.data = obj.data.copy()  # Deep copy mesh data
            bpy.context.collection.objects.link(copy)
            temp_copies.append(copy)

        if not temp_copies:
            return None

        # Select all copies for joining
        bpy.ops.object.select_all(action='DESELECT')
        for copy in temp_copies:
            copy.select_set(True)
        bpy.context.view_layer.objects.active = temp_copies[0]

        # Ensure object mode
        if bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        # Join into one mesh
        bpy.ops.object.join()
        joined = bpy.context.active_object
        joined.name = f"UV_Atlas_{material_name}"

        # Note: We don't hide here yet - the object needs to be visible for UV operations
        # It will be hidden after UV packing is complete (by the caller or cleanup)

        if verbose:
            print(f"  → Created joined mesh '{joined.name}' from {len(objects)} objects")

        # Restore selection using names
        bpy.ops.object.select_all(action='DESELECT')
        for obj_name in previous_selection_names:
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

        return joined

    except Exception as e:
        if verbose:
            print(f"❌ Failed to join objects: {e}")
        import traceback
        traceback.print_exc()
        return None


def apply_lightmap_pack(obj: bpy.types.Object,
                       image_size: int = 1024,
                       margin: float = 0.05,
                       verbose: bool = True) -> bool:
    """
    Apply Lightmap Pack UV unwrapping for atlas packing.

    Args:
        obj: Object to unwrap
        image_size: Target texture size in pixels
        margin: Margin between UV islands (0.0-1.0)
        verbose: Print progress messages

    Returns:
        Success status
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        return False

    try:
        # Store current state using NAMES (safer - objects might change)
        previous_active_name = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
        previous_selection_names = [o.name for o in bpy.context.selected_objects]

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

        # Apply Lightmap Pack for optimal atlas packing
        # Note: PREF_IMG_PX_SIZE and PREF_APPLY_IMAGE are not available in Blender 4.4+
        bpy.ops.uv.lightmap_pack(
            PREF_CONTEXT='ALL_FACES',
            PREF_PACK_IN_ONE=True,      # Pack all islands in one UV map
            PREF_NEW_UVLAYER=False,     # Use existing UV layer
            PREF_BOX_DIV=12,            # Quality of packing (higher = better, slower)
            PREF_MARGIN_DIV=margin
        )

        if verbose:
            print(f"○ Lightmap packed UV atlas: {obj.name}")

        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Restore previous state using names
        bpy.ops.object.select_all(action='DESELECT')
        for obj_name in previous_selection_names:
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

        return True

    except Exception as e:
        if verbose:
            print(f"❌ UV atlas packing failed for {obj.name}: {e}")
            import traceback
            traceback.print_exc()

        # Try to restore object mode
        try:
            if bpy.context.object and bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass

        return False


def smart_uv_unwrap_individual(obj: bpy.types.Object,
                               angle_limit: float = 66.0,
                               island_margin: float = 0.02,
                               verbose: bool = True) -> bool:
    """
    Apply Smart UV Project to an individual object (fallback method).

    Args:
        obj: Blender object
        angle_limit: Max angle between faces in same island (degrees)
        island_margin: Margin between UV islands (0.0-1.0)
        verbose: Print progress messages

    Returns:
        Success status
    """
    if not obj or obj.type != 'MESH' or not obj.data:
        return False

    try:
        # Store current state using NAMES (safer - objects might change)
        previous_active_name = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
        previous_selection_names = [o.name for o in bpy.context.selected_objects]

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
            print(f"○ Smart UV unwrapped (individual): {obj.name}")

        # Return to object mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Restore previous state using names
        bpy.ops.object.select_all(action='DESELECT')
        for obj_name in previous_selection_names:
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

        return True

    except Exception as e:
        if verbose:
            print(f"❌ UV unwrapping failed for {obj.name}: {e}")

        try:
            if bpy.context.object and bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
        except:
            pass

        return False


def auto_unwrap_with_atlasing(objects: List[bpy.types.Object],
                              enable_atlasing: bool = True,
                              min_group_size: int = 2,
                              atlas_texture_size: int = 1024,
                              atlas_margin: float = 0.05,
                              fallback_angle_limit: float = 66.0,
                              fallback_island_margin: float = 0.02,
                              verbose: bool = True) -> Dict:
    """
    Automatically unwrap objects with material-based UV atlas optimization.

    Args:
        objects: List of Blender objects to process
        enable_atlasing: Enable material-based atlas grouping
        min_group_size: Minimum objects required to create atlas
        atlas_texture_size: Target texture size for atlas packing
        atlas_margin: Margin between UV islands in atlas
        fallback_angle_limit: Angle limit for individual Smart UV unwrap
        fallback_island_margin: Island margin for individual Smart UV unwrap
        verbose: Print progress messages

    Returns:
        Dictionary with stats: {
            'atlases_created': count,
            'objects_in_atlases': count,
            'atlas_objects': [list of joined atlas objects],
            'atlased_source_objects': [list of original objects grouped into atlases],
            'individual_unwraps': count,
            'skipped': count,
            'failed': count
        }
    """
    stats = {
        'atlases_created': 0,
        'objects_in_atlases': 0,
        'atlas_objects': [],
        'atlased_source_objects': [],  # Original objects that were grouped into atlases
        'individual_unwraps': 0,
        'skipped': 0,
        'failed': 0
    }

    mesh_objects = [obj for obj in objects if obj.type == 'MESH']

    if not mesh_objects:
        return stats

    if verbose:
        print(f"\n{'='*60}")
        print(f"AUTO UV UNWRAPPING WITH MATERIAL-BASED ATLASING")
        print(f"{'='*60}")

    if enable_atlasing:
        # Group objects by material
        material_groups, single_objects = group_objects_by_material(
            mesh_objects,
            min_group_size=min_group_size
        )

        if verbose and material_groups:
            print(f"\n→ Found {len(material_groups)} material groups for atlasing:")
            for mat, objs in material_groups.items():
                print(f"  • Material '{mat.name}': {len(objs)} objects")

        # Create UV atlases for each material group
        for material, group_objects in material_groups.items():
            if verbose:
                print(f"\n→ Creating UV atlas for material '{material.name}'...")

            # Create temporary joined mesh
            joined = create_temp_joined_mesh(
                group_objects,
                material.name,
                verbose=verbose
            )

            if joined:
                # Apply lightmap pack for atlas
                success = apply_lightmap_pack(
                    joined,
                    image_size=atlas_texture_size,
                    margin=atlas_margin,
                    verbose=verbose
                )

                if success:
                    stats['atlases_created'] += 1
                    stats['objects_in_atlases'] += len(group_objects)
                    stats['atlas_objects'].append(joined)
                    stats['atlased_source_objects'].extend(group_objects)  # Track source objects

                    if verbose:
                        print(f"✓ Atlas created: {len(group_objects)} objects packed into '{joined.name}'")
                else:
                    stats['failed'] += 1
                    # Clean up failed joined object
                    bpy.data.objects.remove(joined, do_unlink=True)
            else:
                stats['failed'] += 1
    else:
        # Atlasing disabled, process all individually
        single_objects = mesh_objects

    # Process single objects individually
    if single_objects:
        if verbose:
            print(f"\n→ Processing {len(single_objects)} objects individually...")

        for obj in single_objects:
            if has_uv_map(obj):
                if verbose:
                    print(f"○ Skipping {obj.name}: Already has UV map")
                stats['skipped'] += 1
            else:
                success = smart_uv_unwrap_individual(
                    obj,
                    angle_limit=fallback_angle_limit,
                    island_margin=fallback_island_margin,
                    verbose=verbose
                )

                if success:
                    stats['individual_unwraps'] += 1
                else:
                    stats['failed'] += 1

    if verbose:
        print(f"{'='*60}")
        print(f"UV Unwrapping complete:")
        print(f"  • {stats['atlases_created']} atlases created ({stats['objects_in_atlases']} objects)")
        print(f"  • {stats['individual_unwraps']} individual unwraps")
        print(f"  • {stats['skipped']} skipped (already had UV maps)")
        print(f"  • {stats['failed']} failed")
        print(f"{'='*60}\n")

    return stats


# Module metadata
__all__ = [
    'has_uv_map',
    'get_primary_material',
    'group_objects_by_material',
    'create_temp_joined_mesh',
    'apply_lightmap_pack',
    'smart_uv_unwrap_individual',
    'auto_unwrap_with_atlasing',
]

if __name__ != "__main__":
    print("○ UV atlas module loaded")
