"""
Material Cleaner Module for GLB Export Optimization

This module provides functions to remove unused materials from objects,
significantly reducing export file size when materials contain textures
but aren't actually applied to any faces.
"""

import bpy


def get_used_material_indices(obj):
    """
    Get the set of material indices actually used by the mesh faces.
    
    Args:
        obj: Blender object (must be MESH type)
        
    Returns:
        set: Set of material indices used by at least one face
    """
    if obj.type != 'MESH' or not obj.data:
        return set()
    
    mesh = obj.data
    used_indices = set()
    
    # Check each polygon (face) to see which material index it uses
    for poly in mesh.polygons:
        used_indices.add(poly.material_index)
    
    return used_indices


def analyze_material_usage(obj):
    """
    Analyze which materials are used vs unused on an object.
    
    Args:
        obj: Blender object (must be MESH type)
        
    Returns:
        dict: {
            'total_materials': int,
            'used_materials': list[dict],  # List of {'index': int, 'name': str}
            'unused_materials': list[dict],  # List of {'index': int, 'name': str}
            'total_faces': int
        }
    """
    result = {
        'total_materials': 0,
        'used_materials': [],
        'unused_materials': [],
        'total_faces': 0
    }
    
    if obj.type != 'MESH' or not obj.data:
        return result
    
    mesh = obj.data
    result['total_faces'] = len(mesh.polygons)
    result['total_materials'] = len(obj.material_slots)
    
    # Get which indices are actually used
    used_indices = get_used_material_indices(obj)
    
    # Categorize materials
    for idx, slot in enumerate(obj.material_slots):
        material_info = {
            'index': idx,
            'name': slot.material.name if slot.material else '<empty>'
        }
        
        if idx in used_indices:
            result['used_materials'].append(material_info)
        else:
            result['unused_materials'].append(material_info)
    
    return result


def remove_unused_materials(obj, dry_run=False):
    """
    Remove materials that aren't used by any faces on the object.
    
    This significantly reduces file size when unused materials contain textures.
    
    Args:
        obj: Blender object (must be MESH type)
        dry_run: If True, only report what would be removed without actually removing
        
    Returns:
        dict: {
            'success': bool,
            'removed_count': int,
            'removed_materials': list[str],  # Names of removed materials
            'kept_count': int,
            'message': str
        }
    """
    result = {
        'success': False,
        'removed_count': 0,
        'removed_materials': [],
        'kept_count': 0,
        'message': ''
    }
    
    if obj.type != 'MESH' or not obj.data:
        result['message'] = f"Object '{obj.name}' is not a mesh"
        return result
    
    # Analyze current usage
    analysis = analyze_material_usage(obj)
    
    if not analysis['unused_materials']:
        result['success'] = True
        result['kept_count'] = analysis['total_materials']
        result['message'] = f"All {analysis['total_materials']} materials are in use"
        return result
    
    # Track what we're removing
    removed_names = [mat['name'] for mat in analysis['unused_materials']]
    removed_indices = [mat['index'] for mat in analysis['unused_materials']]
    
    if dry_run:
        result['success'] = True
        result['removed_count'] = len(removed_names)
        result['removed_materials'] = removed_names
        result['kept_count'] = len(analysis['used_materials'])
        result['message'] = f"DRY RUN: Would remove {len(removed_names)} unused materials"
        return result
    
    # Remove unused materials (in reverse order to maintain indices)
    for idx in sorted(removed_indices, reverse=True):
        obj.data.materials.pop(index=idx)
    
    result['success'] = True
    result['removed_count'] = len(removed_names)
    result['removed_materials'] = removed_names
    result['kept_count'] = len(analysis['used_materials'])
    result['message'] = f"Removed {len(removed_names)} unused materials, kept {result['kept_count']}"
    
    return result


def clean_materials_batch(objects, dry_run=False):
    """
    Remove unused materials from multiple objects.
    
    Args:
        objects: List of Blender objects
        dry_run: If True, only report what would be removed without actually removing
        
    Returns:
        dict: {
            'total_objects': int,
            'cleaned_objects': int,
            'total_removed': int,
            'results': list[dict]  # Per-object results
        }
    """
    batch_result = {
        'total_objects': len(objects),
        'cleaned_objects': 0,
        'total_removed': 0,
        'results': []
    }
    
    for obj in objects:
        if obj.type != 'MESH':
            continue
        
        result = remove_unused_materials(obj, dry_run=dry_run)
        result['object_name'] = obj.name
        
        if result['removed_count'] > 0:
            batch_result['cleaned_objects'] += 1
            batch_result['total_removed'] += result['removed_count']
        
        batch_result['results'].append(result)
    
    return batch_result


def clean_selected_objects(context=None, dry_run=False):
    """
    Clean unused materials from all selected objects.
    
    Args:
        context: Blender context (uses bpy.context if None)
        dry_run: If True, only report what would be removed
        
    Returns:
        dict: Batch cleaning results
    """
    if context is None:
        context = bpy.context
    
    selected_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
    return clean_materials_batch(selected_objects, dry_run=dry_run)


def clean_all_objects(context=None, dry_run=False):
    """
    Clean unused materials from all objects in the scene.
    
    Args:
        context: Blender context (uses bpy.context if None)
        dry_run: If True, only report what would be removed
        
    Returns:
        dict: Batch cleaning results
    """
    if context is None:
        context = bpy.context
    
    all_objects = [obj for obj in context.scene.objects if obj.type == 'MESH']
    return clean_materials_batch(all_objects, dry_run=dry_run)


def print_material_usage_report(obj):
    """
    Print a detailed report of material usage for an object.
    
    Args:
        obj: Blender object (must be MESH type)
    """
    print("\n" + "="*60)
    print(f"Material Usage Report: {obj.name}")
    print("="*60)
    
    analysis = analyze_material_usage(obj)
    
    print(f"\nTotal Materials: {analysis['total_materials']}")
    print(f"Total Faces: {analysis['total_faces']}")
    
    print(f"\nUsed Materials ({len(analysis['used_materials'])}):")
    for mat in analysis['used_materials']:
        print(f"  [{mat['index']}] {mat['name']}")
    
    print(f"\nUnused Materials ({len(analysis['unused_materials'])}):")
    for mat in analysis['unused_materials']:
        print(f"  [{mat['index']}] {mat['name']}")
    
    if analysis['unused_materials']:
        percentage = (len(analysis['unused_materials']) / analysis['total_materials']) * 100
        print(f"\n⚠️  {percentage:.1f}% of materials are unused!")
        print("   Consider running remove_unused_materials() to optimize export size.")
    else:
        print("\n✓ All materials are being used efficiently.")
    
    print("="*60 + "\n")


def print_batch_cleaning_summary(batch_result):
    """
    Print a summary of batch cleaning results.
    
    Args:
        batch_result: Result dict from clean_materials_batch()
    """
    print("\n" + "="*60)
    print("MATERIAL CLEANING SUMMARY")
    print("="*60)
    print(f"Total objects processed: {batch_result['total_objects']}")
    print(f"Objects with unused materials: {batch_result['cleaned_objects']}")
    print(f"Total materials removed: {batch_result['total_removed']}")
    print("="*60)
    
    if batch_result['results']:
        print("\nDetailed Results:")
        for result in batch_result['results']:
            if result['removed_count'] > 0:
                print(f"\n  {result['object_name']}:")
                print(f"    Removed: {result['removed_count']} materials")
                print(f"    Kept: {result['kept_count']} materials")
                print(f"    Removed materials: {', '.join(result['removed_materials'])}")
    
    print("\n" + "="*60 + "\n")

