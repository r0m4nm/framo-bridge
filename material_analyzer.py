"""
Material Analyzer Module for GLB Export Compatibility

This module provides functions to analyze Blender materials for glTF/GLB export readiness.
"""

import bpy
import re

# Material Analyzer Constants
# Supported nodes for glTF export
SUPPORTED_SHADER_NODES = {
    'BSDF_PRINCIPLED',  # Principled BSDF
    'EMISSION',  # Emission Shader
}

SUPPORTED_TEXTURE_NODES = {
    'TEX_IMAGE',  # Image Texture
    'UVMAP',  # UV Map
    'MAPPING',  # Mapping
    'NORMAL_MAP',  # Normal Map
}

SUPPORTED_UTILITY_NODES = {
    'MATH',  # Math
    'MIX',  # Mix (limited support)
    'VALTORGB',  # ColorRamp
    'SEPRGB',  # Separate RGB (older node, still supported)
    'SEPARATE_COLOR',  # Separate Color (Blender 3.3+, replaces Separate RGB)
    'COMBRGB',  # Combine RGB (older node, still supported)
    'COMBINE_COLOR',  # Combine Color (Blender 3.3+, replaces Combine RGB)
    'VECT_MATH',  # Vector Math
    'ATTRIBUTE',  # Attribute
}

SUPPORTED_INPUT_NODES = {
    'RGB',  # RGB
    'VALUE',  # Value
    'GEOMETRY',  # Geometry (limited)
    'TEX_COORD',  # Texture Coordinate
}

# Unsupported nodes that will cause export issues
UNSUPPORTED_SHADER_NODES = {
    'BSDF_DIFFUSE',  # Diffuse BSDF
    'BSDF_GLOSSY',  # Glossy BSDF
    'BSDF_ANISOTROPIC',  # Anisotropic BSDF
    'BSDF_GLASS',  # Glass BSDF
    'BSDF_TRANSLUCENT',  # Translucent BSDF
    'BSDF_VELVET',  # Velvet BSDF
    'BSDF_TOON',  # Toon BSDF
    'BSDF_HAIR',  # Hair BSDF
    'VOLUME_SHADER',  # Volume Shader
    'SUBSURFACE_SCATTERING',  # Subsurface Scattering BSDF
    'BSDF_REFRACTION',  # Refraction BSDF
}

UNSUPPORTED_TEXTURE_NODES = {
    'TEX_NOISE',  # Noise Texture
    'TEX_VORONOI',  # Voronoi Texture
    'TEX_WAVE',  # Wave Texture
    'TEX_MAGIC',  # Magic Texture
    'TEX_CHECKER',  # Checker Texture
    'TEX_BRICK',  # Brick Texture
    'TEX_GRADIENT',  # Gradient Texture
    'TEX_MUSGRAVE',  # Musgrave Texture
    'TEX_WHITE_NOISE',  # White Noise Texture
}

UNSUPPORTED_UTILITY_NODES = {
    'LIGHT_PATH',  # Light Path
    'OBJECT_INFO',  # Object Info
    'PARTICLE_INFO',  # Particle Info
    'FRESNEL',  # Fresnel
    'LAYER_WEIGHT',  # Layer Weight
    'CURVE_RGB',  # RGB Curves
    'CURVE_VEC',  # Vector Curves
    'BLACKBODY',  # Blackbody
    'WAVELENGTH',  # Wavelength
}


def get_all_nodes_in_tree(material):
    """Recursively collect all nodes in a material's node tree."""
    if not material or not material.use_nodes or not material.node_tree:
        return []
    
    nodes = []
    visited = set()
    
    def traverse_node(node):
        if node in visited:
            return
        visited.add(node)
        nodes.append(node)
        
        # Traverse inputs
        for input_socket in node.inputs:
            if input_socket.is_linked:
                for link in input_socket.links:
                    traverse_node(link.from_node)
        
        # Traverse outputs
        for output_socket in node.outputs:
            if output_socket.is_linked:
                for link in output_socket.links:
                    traverse_node(link.to_node)
    
    # Start from Material Output node
    output_node = material.node_tree.nodes.get('Material Output')
    if output_node:
        traverse_node(output_node)
    
    return nodes


def is_node_supported(node):
    """Check if a node type is in the supported list."""
    node_type = node.type
    return (node_type in SUPPORTED_SHADER_NODES or
            node_type in SUPPORTED_TEXTURE_NODES or
            node_type in SUPPORTED_UTILITY_NODES or
            node_type in SUPPORTED_INPUT_NODES)


def is_node_unsupported(node):
    """Check if a node type is in the unsupported list."""
    node_type = node.type
    return (node_type in UNSUPPORTED_SHADER_NODES or
            node_type in UNSUPPORTED_TEXTURE_NODES or
            node_type in UNSUPPORTED_UTILITY_NODES)


def check_udim_texture(image_texture_node):
    """Detect UDIM texture patterns in an Image Texture node."""
    if image_texture_node.type != 'TEX_IMAGE':
        return False
    
    if not hasattr(image_texture_node, 'image') or not image_texture_node.image:
        return False
    
    # Check if image name contains UDIM pattern (e.g., "texture_1001.png")
    image_name = image_texture_node.image.name
    # UDIM tiles typically have 4-digit numbers (1001, 1002, etc.)
    udim_pattern = r'_\d{4}\.'
    return bool(re.search(udim_pattern, image_name))


def check_complex_mix_shader(mix_shader_node, all_nodes):
    """Detect problematic Mix Shader setups mixing multiple Principled BSDFs."""
    if mix_shader_node.type != 'MIX_SHADER':
        return False
    
    # Check if Mix Shader has multiple Principled BSDF inputs
    principled_count = 0
    for input_socket in mix_shader_node.inputs:
        if input_socket.is_linked:
            for link in input_socket.links:
                connected_node = link.from_node
                if connected_node.type == 'BSDF_PRINCIPLED':
                    principled_count += 1
    
    # If mixing multiple Principled BSDFs, it's problematic
    return principled_count > 1


def analyze_material_readiness(material):
    """
    Analyze a material for GLB export compatibility.
    
    Returns:
        dict: {
            'is_ready': bool,
            'issues': list[str],  # Blocking issues
            'warnings': list[str]  # Non-blocking warnings
        }
    """
    result = {
        'is_ready': True,
        'issues': [],
        'warnings': []
    }
    
    # Check if material exists and uses nodes
    if not material:
        result['is_ready'] = False
        result['issues'].append("Material issues:")
        result['issues'].append("  • Material is None")
        return result
    
    if not material.use_nodes:
        result['is_ready'] = False
        result['issues'].append("Material issues:")
        result['issues'].append("  • Material does not use nodes")
        return result
    
    if not material.node_tree:
        result['is_ready'] = False
        result['issues'].append("Material issues:")
        result['issues'].append("  • Material has no node tree")
        return result
    
    # Get Material Output node
    output_node = material.node_tree.nodes.get('Material Output')
    if not output_node:
        result['is_ready'] = False
        result['issues'].append("Material Output issues:")
        result['issues'].append("  • Missing Material Output node")
        return result
    
    # Check if Material Output Surface input is connected
    surface_input = output_node.inputs.get('Surface')
    if not surface_input or not surface_input.is_linked:
        result['is_ready'] = False
        result['issues'].append("Material Output issues:")
        result['issues'].append("  • Material Output Surface input not connected")
        return result
    
    # Get the shader connected to Surface input
    surface_link = surface_input.links[0]
    surface_shader = surface_link.from_node
    
    # Check if connected shader is Principled BSDF or Emission
    # Don't return early - continue to analyze the rest of the tree for all unsupported nodes
    # GROUP nodes and any other non-supported types should be caught here
    if surface_shader.type not in SUPPORTED_SHADER_NODES:
        result['is_ready'] = False
        # Track this for later - we'll add it to the unsupported shaders list
        # Use a more readable name for GROUP nodes
        if surface_shader.type == 'GROUP':
            shader_display_name = f"{surface_shader.name} (Group Node)"
        else:
            shader_display_name = f"{surface_shader.name} ({surface_shader.type})"
        unsupported_main_shader = shader_display_name
    else:
        unsupported_main_shader = None
    
    # Check for Volume shader connection (problematic)
    volume_input = output_node.inputs.get('Volume')
    if volume_input and volume_input.is_linked:
        result['warnings'].append("Volume shader connected (limited glTF support)")
    
    # Get all nodes in the tree
    all_nodes = get_all_nodes_in_tree(material)
    
    # Track unsupported nodes with node names for better identification
    unsupported_shaders = []
    unsupported_textures = []
    unsupported_utilities = []
    procedural_textures = []
    udim_textures = []
    complex_mix_shaders = []
    
    # Add the main shader if it's unsupported (from earlier check)
    if unsupported_main_shader:
        unsupported_shaders.append(unsupported_main_shader)
    
    # Analyze each node
    for node in all_nodes:
        node_type = node.type
        
        # Skip Material Output node
        if node_type == 'OUTPUT_MATERIAL':
            continue
        
        # Skip the main surface shader - we already checked it
        if node == surface_shader:
            continue
        
        # Check for unsupported shader nodes
        # Also catch GROUP nodes and any other non-supported types
        if node_type in UNSUPPORTED_SHADER_NODES:
            unsupported_shaders.append(f"{node.name} ({node_type})")
        elif node_type == 'GROUP':
            # Group nodes are not supported
            unsupported_shaders.append(f"{node.name} (Group Node)")
        elif node_type not in SUPPORTED_SHADER_NODES and node_type not in SUPPORTED_TEXTURE_NODES and node_type not in SUPPORTED_UTILITY_NODES and node_type not in SUPPORTED_INPUT_NODES and node_type != 'OUTPUT_MATERIAL':
            # Catch any other unsupported node types
            unsupported_shaders.append(f"{node.name} ({node_type})")
        
        # Check for unsupported procedural texture nodes
        if node_type in UNSUPPORTED_TEXTURE_NODES:
            procedural_textures.append(f"{node.name} ({node_type})")
        
        # Check for unsupported utility nodes
        if node_type in UNSUPPORTED_UTILITY_NODES:
            unsupported_utilities.append(f"{node.name} ({node_type})")
        
        # Check for UDIM textures
        if node_type == 'TEX_IMAGE' and check_udim_texture(node):
            udim_textures.append(node.name)
        
        # Check for complex Mix Shader setups
        if node_type == 'MIX_SHADER' and check_complex_mix_shader(node, all_nodes):
            complex_mix_shaders.append(node.name)
    
    # Add blocking issues as individual items
    if unsupported_shaders:
        result['is_ready'] = False
        result['issues'].append("Unsupported shader nodes:")
        for shader in unsupported_shaders:
            result['issues'].append(f"  • {shader}")
        result['issues'].append("  Use Principled BSDF or Emission shader instead")
    
    if procedural_textures:
        result['is_ready'] = False
        result['issues'].append("Contains procedural textures:")
        for texture in procedural_textures:
            result['issues'].append(f"  • {texture}")
    
    if unsupported_utilities:
        result['is_ready'] = False
        result['issues'].append("Contains unsupported utility nodes:")
        for utility in unsupported_utilities:
            result['issues'].append(f"  • {utility}")
    
    if complex_mix_shaders:
        result['is_ready'] = False
        result['issues'].append("Complex Mix Shader setup mixing multiple Principled BSDFs:")
        for mix_shader in complex_mix_shaders:
            result['issues'].append(f"  • {mix_shader}")
    
    # Add warnings (non-blocking)
    if udim_textures:
        result['warnings'].append(f"UDIM textures detected: {', '.join(udim_textures)} (will split into multiple images)")
    
    # Check for complex node tree (heuristic: more than 20 nodes)
    if len(all_nodes) > 20:
        result['warnings'].append(f"Complex node tree ({len(all_nodes)} nodes) - may export with reduced fidelity")
    
    return result


def get_materials_to_analyze(context):
    """
    Get list of materials to analyze based on context.
    
    Returns materials assigned to selected objects only.
    Returns empty list if no objects are selected.
    """
    materials = set()
    
    # Only analyze materials from selected objects
    if not context.selected_objects:
        return []
    
    objects_to_check = context.selected_objects
    
    # Collect materials from selected objects only
    for obj in objects_to_check:
        if obj.type == 'MESH' and obj.data:
            # Check material slots
            for slot in obj.material_slots:
                if slot.material:
                    materials.add(slot.material)
        
        # Check if object is a collection instance
        elif obj.type == 'EMPTY' and obj.instance_type == 'COLLECTION' and obj.instance_collection:
            # Get materials from all meshes in the instanced collection
            for coll_obj in obj.instance_collection.all_objects:
                if coll_obj.type == 'MESH' and coll_obj.data:
                    for slot in coll_obj.material_slots:
                        if slot.material:
                            materials.add(slot.material)
    
    # Filter out None materials
    materials = {m for m in materials if m is not None}
    
    return list(materials)


def get_valid_materials(context):
    """
    Get list of materials that are ready for GLB export.
    
    Returns materials that pass the readiness check.
    """
    all_materials = get_materials_to_analyze(context)
    valid_materials = []
    
    for material in all_materials:
        result = analyze_material_readiness(material)
        if result['is_ready']:
            valid_materials.append(material)
    
    return valid_materials


def replace_material_on_objects(old_material, new_material, context):
    """
    Replace old_material with new_material on all objects in the scene or selection.
    
    Returns the number of objects updated.
    """
    if not old_material or not new_material:
        return 0
    
    objects_to_check = context.selected_objects if context.selected_objects else context.scene.objects
    updated_count = 0
    
    for obj in objects_to_check:
        if obj.type == 'MESH' and obj.data:
            for slot in obj.material_slots:
                if slot.material == old_material:
                    slot.material = new_material
                    updated_count += 1
    
    return updated_count

