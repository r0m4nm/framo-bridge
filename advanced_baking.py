"""
Advanced Texture Baking for Complex Shader Materials

Provides sophisticated baking capabilities for complex shader networks,
proper channel isolation, and material property extraction.
"""

import bpy
import bmesh
from mathutils import Vector, Color
from typing import Dict, List, Tuple, Optional, Set
import tempfile
import os

class MaterialBackup:
    """Backup and restore material states during baking"""
    
    def __init__(self):
        self.material_backups = {}
        self.active_materials = {}
    
    def backup_material(self, material):
        """Create a backup of material node tree"""
        if not material.use_nodes or not material.node_tree:
            return
        
        # Store original node tree
        self.material_backups[material.name] = {
            'nodes': {},
            'links': [],
            'outputs': {}
        }
        
        # Backup nodes
        for node in material.node_tree.nodes:
            self.material_backups[material.name]['nodes'][node.name] = {
                'type': node.bl_idname,
                'location': node.location.copy(),
                'inputs': {},
                'outputs': {}
            }
            
            # Backup input values
            for input_socket in node.inputs:
                if not input_socket.is_linked:
                    self.material_backups[material.name]['nodes'][node.name]['inputs'][input_socket.name] = {
                        'default_value': getattr(input_socket, 'default_value', None)
                    }
        
        # Backup links
        for link in material.node_tree.links:
            self.material_backups[material.name]['links'].append({
                'from_node': link.from_node.name,
                'from_socket': link.from_socket.name,
                'to_node': link.to_node.name,
                'to_socket': link.to_socket.name
            })
    
    def restore_material(self, material):
        """Restore material from backup"""
        if material.name not in self.material_backups:
            return
        
        # This is a simplified restore - in production you'd fully reconstruct the node tree
        # For now, we'll just ensure the material is in a usable state
        pass

class ChannelIsolator:
    """Isolates specific material channels for precise baking"""
    
    def __init__(self):
        self.temp_materials = {}
        self.material_backup = MaterialBackup()
    
    def create_isolation_material(self, original_material, channel_type: str):
        """Create a material that outputs only the specified channel"""
        if not original_material.use_nodes or not original_material.node_tree:
            return None
        
        # Find the principled BSDF node
        principled_node = None
        for node in original_material.node_tree.nodes:
            if node.bl_idname == 'ShaderNodeBsdfPrincipled':
                principled_node = node
                break
        
        if not principled_node:
            return None
        
        # Create temporary material
        temp_mat_name = f"TEMP_BAKE_{channel_type}_{original_material.name}"
        temp_material = bpy.data.materials.new(temp_mat_name)
        temp_material.use_nodes = True
        
        # Clear default nodes
        temp_material.node_tree.nodes.clear()
        
        # Copy relevant nodes from original material
        self._copy_node_network(original_material.node_tree, temp_material.node_tree)
        
        # Create isolation setup
        self._setup_channel_isolation(temp_material.node_tree, channel_type, principled_node.name)
        
        return temp_material
    
    def _copy_node_network(self, source_tree, target_tree):
        """Copy the entire node network from source to target"""
        node_mapping = {}
        
        # Copy nodes
        for node in source_tree.nodes:
            new_node = target_tree.nodes.new(node.bl_idname)
            new_node.name = node.name
            new_node.location = node.location
            node_mapping[node.name] = new_node
            
            # Copy node properties
            self._copy_node_properties(node, new_node)
        
        # Copy links
        for link in source_tree.links:
            if link.from_node.name in node_mapping and link.to_node.name in node_mapping:
                from_node = node_mapping[link.from_node.name]
                to_node = node_mapping[link.to_node.name]
                
                try:
                    target_tree.links.new(
                        from_node.outputs[link.from_socket.name],
                        to_node.inputs[link.to_socket.name]
                    )
                except:
                    pass  # Skip invalid links
    
    def _copy_node_properties(self, source_node, target_node):
        """Copy properties from source node to target node"""
        # Copy input default values
        for i, input_socket in enumerate(source_node.inputs):
            if i < len(target_node.inputs) and not input_socket.is_linked:
                try:
                    if hasattr(input_socket, 'default_value'):
                        target_node.inputs[i].default_value = input_socket.default_value
                except:
                    pass
        
        # Copy node-specific properties
        if source_node.bl_idname == 'ShaderNodeTexImage' and hasattr(source_node, 'image'):
            target_node.image = source_node.image
        elif source_node.bl_idname == 'ShaderNodeTexNoise':
            if hasattr(source_node, 'noise_dimensions'):
                target_node.noise_dimensions = source_node.noise_dimensions
    
    def _setup_channel_isolation(self, node_tree, channel_type: str, principled_name: str):
        """Setup the node tree to output only the specified channel"""
        principled_node = node_tree.nodes.get(principled_name)
        if not principled_node:
            return
        
        # Create emission shader to output the channel
        emission_node = node_tree.nodes.new('ShaderNodeEmission')
        emission_node.location = (principled_node.location.x + 300, principled_node.location.y)
        
        # Create material output
        output_node = node_tree.nodes.new('ShaderNodeOutputMaterial')
        output_node.location = (emission_node.location.x + 200, emission_node.location.y)
        
        # Connect emission to output
        node_tree.links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
        
        # Connect the appropriate channel to emission
        channel_mappings = {
            'DIFFUSE': 'Base Color',
            'ROUGHNESS': 'Roughness',
            'METALLIC': 'Metallic',
            'NORMAL': 'Normal',
            'EMISSION': 'Emission'
        }
        
        if channel_type in channel_mappings:
            input_name = channel_mappings[channel_type]
            if input_name in principled_node.inputs:
                if channel_type == 'NORMAL':
                    # For normal maps, we need special handling
                    self._setup_normal_baking(node_tree, principled_node, emission_node)
                else:
                    # Direct connection for other channels
                    source_socket = principled_node.inputs[input_name]
                    if source_socket.is_linked:
                        node_tree.links.new(
                            source_socket.links[0].from_socket,
                            emission_node.inputs['Color']
                        )
                    else:
                        # Use default value
                        emission_node.inputs['Color'].default_value = source_socket.default_value
    
    def _setup_normal_baking(self, node_tree, principled_node, emission_node):
        """Special setup for normal map baking"""
        # For normal baking, we need to extract the normal information
        # This is complex and depends on whether it's a normal map or bump map
        normal_input = principled_node.inputs.get('Normal')
        if normal_input and normal_input.is_linked:
            # Find if there's a normal map node
            from_socket = normal_input.links[0].from_socket
            if from_socket.node.bl_idname == 'ShaderNodeNormalMap':
                # Connect the color input of the normal map
                color_input = from_socket.node.inputs.get('Color')
                if color_input and color_input.is_linked:
                    node_tree.links.new(
                        color_input.links[0].from_socket,
                        emission_node.inputs['Color']
                    )
    
    def apply_isolation_material(self, obj, channel_type: str):
        """Apply isolation material to object for baking"""
        if not obj.material_slots:
            return None
        
        original_material = obj.material_slots[0].material
        if not original_material:
            return None
        
        # Backup original material
        self.material_backup.backup_material(original_material)
        
        # Create and apply isolation material
        isolation_material = self.create_isolation_material(original_material, channel_type)
        if isolation_material:
            obj.material_slots[0].material = isolation_material
            self.temp_materials[obj.name] = {
                'original': original_material,
                'temp': isolation_material
            }
        
        return isolation_material
    
    def restore_original_material(self, obj):
        """Restore original material to object"""
        if obj.name in self.temp_materials:
            original_material = self.temp_materials[obj.name]['original']
            temp_material = self.temp_materials[obj.name]['temp']
            
            # Restore original material
            obj.material_slots[0].material = original_material
            
            # Clean up temporary material
            bpy.data.materials.remove(temp_material)
            del self.temp_materials[obj.name]
    
    def cleanup_all(self):
        """Clean up all temporary materials"""
        for obj_name in list(self.temp_materials.keys()):
            # Find object and restore
            obj = bpy.data.objects.get(obj_name)
            if obj:
                self.restore_original_material(obj)

class SmartUVUnwrapper:
    """Advanced UV unwrapping for optimal baking results"""
    
    @staticmethod
    def smart_unwrap_for_baking(obj, target_texel_density=256):
        """Perform smart UV unwrapping optimized for baking"""
        # Store current mode
        original_mode = obj.mode if hasattr(obj, 'mode') else 'OBJECT'
        
        # Switch to object mode
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Calculate object surface area for texel density
        mesh = obj.data
        total_area = sum(face.area for face in mesh.polygons)
        
        # Determine optimal UV layout
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        
        # Mark sharp edges as seams for better unwrapping
        bpy.ops.mesh.edges_select_sharp()
        bpy.ops.uv.seams_from_islands()
        
        # Perform smart projection
        bpy.ops.uv.smart_project(
            angle_limit=1.15,  # ~66 degrees
            island_margin=0.02,
            area_weight=0.0,
            correct_aspect=True
        )
        
        # Optimize UV layout
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.pack_islands(
            rotate=True,
            margin=0.01
        )
        
        # Return to original mode
        bpy.ops.object.mode_set(mode=original_mode)
        
        return True

class AdaptiveBaker:
    """Adaptive baking system that adjusts quality based on content"""
    
    def __init__(self):
        self.channel_isolator = ChannelIsolator()
    
    def analyze_baking_requirements(self, obj):
        """Analyze object to determine optimal baking settings"""
        if not obj.material_slots or not obj.material_slots[0].material:
            return {}
        
        material = obj.material_slots[0].material
        requirements = {
            'needs_high_res': False,
            'complex_normals': False,
            'procedural_complexity': 0,
            'recommended_resolution': 1024
        }
        
        if material.use_nodes and material.node_tree:
            # Count procedural nodes
            procedural_count = 0
            has_complex_normals = False
            
            for node in material.node_tree.nodes:
                if node.bl_idname in ['ShaderNodeTexNoise', 'ShaderNodeTexVoronoi', 'ShaderNodeTexMusgrave']:
                    procedural_count += 1
                elif node.bl_idname in ['ShaderNodeBump', 'ShaderNodeNormalMap']:
                    has_complex_normals = True
            
            requirements['procedural_complexity'] = procedural_count
            requirements['complex_normals'] = has_complex_normals
            
            # Determine recommended resolution
            if procedural_count > 3 or has_complex_normals:
                requirements['recommended_resolution'] = 2048
                requirements['needs_high_res'] = True
            elif procedural_count > 1:
                requirements['recommended_resolution'] = 1024
        
        return requirements
    
    def bake_channel_with_isolation(self, obj, channel_type: str, resolution: int = 1024):
        """Bake a specific channel with proper isolation"""
        try:
            # Apply isolation material
            isolation_material = self.channel_isolator.apply_isolation_material(obj, channel_type)
            if not isolation_material:
                return None
            
            # Ensure UV mapping
            SmartUVUnwrapper.smart_unwrap_for_baking(obj)
            
            # Create bake image
            image_name = f"BAKE_{obj.name}_{channel_type}_{resolution}"
            if image_name in bpy.data.images:
                bpy.data.images.remove(bpy.data.images[image_name])
            
            bake_image = bpy.data.images.new(
                name=image_name,
                width=resolution,
                height=resolution,
                alpha=False
            )
            
            # Setup baking node in isolation material
            nodes = isolation_material.node_tree.nodes
            bake_node = nodes.new('ShaderNodeTexImage')
            bake_node.image = bake_image
            bake_node.select = True
            nodes.active = bake_node
            
            # Configure bake settings
            bpy.context.scene.render.bake.use_pass_direct = False
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_color = True
            bpy.context.scene.render.bake.margin = 2  # Edge padding
            
            # Select object for baking
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # Perform the bake
            bpy.ops.object.bake(type='EMIT')  # Using emit because we're outputting through emission
            
            # Set correct color space
            color_spaces = {
                'DIFFUSE': 'sRGB',
                'EMISSION': 'sRGB',
                'NORMAL': 'Non-Color',
                'ROUGHNESS': 'Non-Color',
                'METALLIC': 'Non-Color',
                'AO': 'Non-Color'
            }
            bake_image.colorspace_settings.name = color_spaces.get(channel_type, 'sRGB')
            
            return bake_image
            
        except Exception as e:
            print(f"Failed to bake {channel_type} for {obj.name}: {e}")
            return None
        
        finally:
            # Always restore original material
            self.channel_isolator.restore_original_material(obj)
    
    def cleanup(self):
        """Clean up all temporary materials and data"""
        self.channel_isolator.cleanup_all()

def get_optimal_baking_settings(obj):
    """Get optimal baking settings for an object"""
    baker = AdaptiveBaker()
    requirements = baker.analyze_baking_requirements(obj)
    baker.cleanup()
    
    return {
        'resolution': requirements['recommended_resolution'],
        'samples': 64 if requirements['needs_high_res'] else 32,
        'margin': 4 if requirements['complex_normals'] else 2
    }