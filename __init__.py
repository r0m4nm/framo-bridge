bl_info = {
    "name": "Framo Bridge",
    "author": "Roman Moor",
    "version": (0, 2, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Framo Export",
    "description": "Export GLB models directly to web applications with compression and mesh decimation",
    "category": "Import-Export",
}

import bpy
from bpy.props import BoolProperty, IntProperty, EnumProperty, FloatProperty
from bpy.types import PropertyGroup
import tempfile
import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
from datetime import datetime

# Custom icon preview collection
custom_icons = None

# Try to import dependency management
try:
    from . import dependencies
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

# Try to import fast decimation module
try:
    from . import fast_decimation
    from . import trimesh_decimation
    FAST_DECIMATION_AVAILABLE = True
    # Check Trimesh availability through the new API
    TRIMESH_AVAILABLE = trimesh_decimation.is_available()
except ImportError:
    FAST_DECIMATION_AVAILABLE = False
    TRIMESH_AVAILABLE = False
    print("Warning: fast_decimation module not available. Using Blender's native decimation.")

# Try to import mesh repair module
try:
    from . import mesh_repair
    MESH_REPAIR_AVAILABLE = True
except ImportError:
    MESH_REPAIR_AVAILABLE = False
    print("Warning: mesh_repair module not available.")

# Try to import material analyzer module
try:
    from . import material_analyzer
    MATERIAL_ANALYZER_AVAILABLE = True
except ImportError:
    MATERIAL_ANALYZER_AVAILABLE = False
    print("Warning: material_analyzer module not available.")

# Try to import UV unwrapping module
try:
    from . import uv_unwrap
    UV_UNWRAP_AVAILABLE = True
except ImportError:
    UV_UNWRAP_AVAILABLE = False
    print("Warning: uv_unwrap module not available.")

# Global server instance
server_instance = None
server_thread = None

# Global dictionary to track expanded state of materials in UI
material_expanded_states = {}

class MaterialExpandedState(PropertyGroup):
    """Property group to track expanded state of materials in the UI"""
    expanded: BoolProperty(
        name="Expanded",
        description="Whether this material's details are expanded",
        default=False
    )

class FramoExportSettings(PropertyGroup):
    # Compression Settings
    use_draco: BoolProperty(
        name="Use Draco Compression",
        description="Enable Draco mesh compression for smaller file sizes",
        default=False
    )
    
    draco_compression_level: IntProperty(
        name="Compression Level",
        description="Draco compression level (0=least compression, 10=most compression)",
        default=6,
        min=0,
        max=10
    )
    
    draco_quantization_position: IntProperty(
        name="Position Quantization",
        description="Quantization bits for position values (higher=better quality)",
        default=14,
        min=8,
        max=16
    )
    
    draco_quantization_normal: IntProperty(
        name="Normal Quantization",
        description="Quantization bits for normal values (higher=better quality)",
        default=10,
        min=8,
        max=16
    )
    
    draco_quantization_texcoord: IntProperty(
        name="Texture Coord Quantization",
        description="Quantization bits for texture coordinates (higher=better quality)",
        default=12,
        min=8,
        max=16
    )
    
    compression_preset: EnumProperty(
        name="Compression Preset",
        description="Quick compression presets",
        items=[
            ('NONE', "No Compression", "No compression, highest quality"),
            ('LOW', "Low Compression", "Minimal compression, high quality"),
            ('MEDIUM', "Medium Compression", "Balanced compression and quality"),
            ('HIGH', "High Compression", "Maximum compression, lower quality"),
            ('CUSTOM', "Custom", "Use custom compression settings"),
        ],
        default='MEDIUM',
        update=lambda self, context: update_compression_preset(self, context)
    )
    
    # Mesh Decimation Settings
    enable_decimation: BoolProperty(
        name="Enable Decimation",
        description="Reduce polygon count before export using decimate modifier",
        default=True
    )
    
    decimate_ratio: FloatProperty(
        name="Decimate Ratio",
        description="Ratio of faces to keep (1.0 = no reduction, 0.1 = 90% reduction)",
        default=0.1,
        min=0.01,
        max=1.0,
        precision=2
    )
    
    decimate_type: EnumProperty(
        name="Decimate Type",
        description="Type of decimation algorithm to use",
        items=[
            ('COLLAPSE', "Collapse", "Edge collapse decimation - best for most cases"),
            ('UNSUBDIV', "Un-Subdivide", "Remove subdivision levels - good for over-subdivided models"),
            ('DISSOLVE', "Planar", "Remove planar faces - good for architectural models"),
        ],
        default='COLLAPSE'
    )
    
    preserve_sharp_edges: BoolProperty(
        name="Preserve Sharp Edges",
        description="Try to preserve sharp edges during decimation",
        default=True
    )
    
    preserve_uv_seams: BoolProperty(
        name="Preserve UV Seams",
        description="Try to preserve UV seams during decimation",
        default=True
    )
    
    # UV Unwrapping Settings
    enable_auto_uv: BoolProperty(
        name="Auto UV Unwrap (if no UV map present)",
        description="Automatically unwrap meshes that don't have UV maps using Smart UV Project",
        default=True
    )
    
    # Mesh Repair/Cleaning Settings
    enable_mesh_repair: BoolProperty(
        name="Enable Mesh Repair",
        description="Repair and clean meshes before export",
        default=False
    )
    
    repair_remove_duplicate_verts: BoolProperty(
        name="Remove Duplicate Vertices",
        description="Merge duplicate vertices",
        default=True
    )
    
    repair_remove_duplicate_faces: BoolProperty(
        name="Remove Duplicate Faces",
        description="Remove duplicate faces",
        default=True
    )
    
    repair_remove_unreferenced_verts: BoolProperty(
        name="Remove Unreferenced Vertices",
        description="Remove vertices not used by any face",
        default=True
    )
    
    repair_fix_normals: BoolProperty(
        name="Fix Normals",
        description="Fix face normals to be consistent",
        default=True
    )
    
    repair_fill_holes: BoolProperty(
        name="Fill Holes",
        description="Fill holes in the mesh (may change geometry)",
        default=False
    )
    
    repair_remove_degenerate: BoolProperty(
        name="Remove Degenerate Faces",
        description="Remove zero-area and invalid faces",
        default=True
    )
    
    repair_make_watertight: BoolProperty(
        name="Make Watertight",
        description="Make mesh watertight (closed, no holes) - may significantly change geometry",
        default=False
    )
    
    adaptive_decimation: BoolProperty(
        name="Adaptive Decimation",
        description="Adjust decimation ratio based on object complexity",
        default=False
    )
    
    decimation_method: EnumProperty(
        name="Decimation Method",
        description="Choose which decimation algorithm to use",
        items=[
            ('AUTO', "Auto", "Automatically select the best available method (Trimesh > bmesh)"),
            ('TRIMESH', "Trimesh", "Fast decimation using Trimesh library (requires trimesh)"),
            ('BMESH', "BMesh", "Native Blender decimation (always available, slower)"),
        ],
        default='AUTO'
    )
    
    # Trimesh-specific settings
    trimesh_aggression: IntProperty(
        name="Aggression",
        description="Decimation aggression for Trimesh (1-10)\n"
                    "Lower (1-3): Conservative, preserves edges better\n"
                    "Medium (4-7): Balanced (recommended)\n"
                    "Higher (8-10): Aggressive, may alter geometry",
        default=7,
        min=1,
        max=10
    )
    
    trimesh_preserve_border: BoolProperty(
        name="Preserve Border Edges",
        description="Preserve border/boundary edges during Trimesh decimation",
        default=True
    )

def update_compression_preset(self, context):
    settings = context.scene.framo_export_settings
    
    if settings.compression_preset == 'NONE':
        settings.use_draco = False
    elif settings.compression_preset == 'LOW':
        settings.use_draco = True
        settings.draco_compression_level = 3
        settings.draco_quantization_position = 16
        settings.draco_quantization_normal = 12
        settings.draco_quantization_texcoord = 14
    elif settings.compression_preset == 'MEDIUM':
        settings.use_draco = True
        settings.draco_compression_level = 6
        settings.draco_quantization_position = 14
        settings.draco_quantization_normal = 10
        settings.draco_quantization_texcoord = 12
    elif settings.compression_preset == 'HIGH':
        settings.use_draco = True
        settings.draco_compression_level = 10
        settings.draco_quantization_position = 11
        settings.draco_quantization_normal = 8
        settings.draco_quantization_texcoord = 10

class GLBRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress console output
        pass
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Model-Metadata')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/ping':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(b'pong')
        elif self.path == '/latest-model':
            if hasattr(self.server, 'latest_glb'):
                self.send_response(200)
                self.send_header('Content-type', 'model/gltf-binary')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(self.server.latest_glb)
            else:
                self.send_response(404)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'No model available')
        elif self.path == '/latest-model-info':
            if hasattr(self.server, 'latest_metadata'):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(self.server.latest_metadata).encode())
            else:
                self.send_response(404)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'No model metadata available')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/upload-model':
            try:
                content_length = int(self.headers['Content-Length'])
                
                # Check if metadata is sent as header
                metadata_header = self.headers.get('X-Model-Metadata')
                
                if metadata_header:
                    # Metadata sent as header, body is just GLB
                    glb_data = self.rfile.read(content_length)
                    metadata = json.loads(metadata_header)
                    
                    # Store GLB data and metadata
                    self.server.latest_glb = glb_data
                    self.server.latest_metadata = metadata
                else:
                    # Legacy format: just GLB data
                    glb_data = self.rfile.read(content_length)
                    self.server.latest_glb = glb_data
                    # Create minimal metadata
                    self.server.latest_metadata = {
                        "filename": "model.glb",
                        "size": len(glb_data),
                        "size_mb": f"{len(glb_data)/(1024*1024):.2f}",
                        "timestamp": None
                    }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    "status": "success",
                    "size": len(glb_data),
                    "size_mb": f"{len(glb_data)/(1024*1024):.2f}MB"
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

class FRAMO_OT_export_to_web(bpy.types.Operator):
    bl_idname = "framo.export_to_web"
    bl_label = "Export to Web"
    bl_description = "Export selected objects as GLB and send to Framo"
    
    @classmethod
    def poll(cls, context):
        """Only allow export if objects are selected and no unsupported materials exist"""
        # Require at least one selected object
        if not context.selected_objects:
            return False
        
        # If material analyzer not available, allow export (can't check materials)
        if not MATERIAL_ANALYZER_AVAILABLE:
            return True
        
        # Check for unsupported materials in selected objects
        try:
            materials_to_check = material_analyzer.get_materials_to_analyze(context)
            if not materials_to_check:
                # No materials found - allow export
                return True
            
            # Check each material
            for material in materials_to_check:
                if not material:
                    continue
                result = material_analyzer.analyze_material_readiness(material)
                if not result.get('is_ready', True):
                    # Found unsupported material - disable export
                    return False
            
            # All materials are ready
            return True
        except Exception:
            # If analysis fails, allow export (fail open)
            return True
    
    def execute(self, context):
        global server_instance
        
        if not server_instance:
            self.report({'ERROR'}, "Server not running. Please restart the the addon.")
            return {'CANCELLED'}
        
        # Get settings
        settings = context.scene.framo_export_settings
        
        # Require at least one object to be selected
        if not context.selected_objects:
            self.report({'ERROR'}, "No objects selected. Please select at least one object to export.")
            return {'CANCELLED'}
        
        # Initialize variables that need to be accessible in finally block
        temp_objects = []
        original_selection = context.selected_objects.copy() if context.selected_objects else []
        
        try:
            info_parts = []
            
            # Create temporary copies of objects for decimation/repair
            # This ensures we never modify the original geometry in Blender
            original_to_temp = {}  # Map original objects to temporary copies
            
            # Process selected objects (we already checked selection exists)
            objects_to_process = context.selected_objects
            mesh_objects = [obj for obj in objects_to_process if obj.type == 'MESH']
            
            # Create temporary copies if decimation, repair, or UV unwrapping is enabled
            if (settings.enable_decimation or settings.enable_mesh_repair or settings.enable_auto_uv) and mesh_objects:
                # Deselect all first
                bpy.ops.object.select_all(action='DESELECT')
                
                for obj in mesh_objects:
                    # Create a temporary copy of the object
                    temp_obj = obj.copy()
                    temp_obj.data = obj.data.copy()  # Deep copy the mesh data
                    temp_obj.name = f"TEMP_EXPORT_{obj.name}"
                    
                    # Link to scene
                    context.collection.objects.link(temp_obj)
                    temp_objects.append(temp_obj)
                    original_to_temp[obj] = temp_obj
                    
                    # Select the temp object for export
                    temp_obj.select_set(True)
                
                # Set active object to first temp object if any exist
                if temp_objects:
                    context.view_layer.objects.active = temp_objects[0]
            
            # Perform auto UV unwrapping if enabled (on temp copies or originals)
            if settings.enable_auto_uv:
                if not UV_UNWRAP_AVAILABLE:
                    self.report({'WARNING'}, "UV unwrapping module not available.")
                else:
                    objects_to_unwrap = temp_objects if temp_objects else mesh_objects
                    
                    if objects_to_unwrap:
                        uv_stats = uv_unwrap.auto_unwrap_objects(
                            objects_to_unwrap,
                            angle_limit=66.0,
                            island_margin=0.02,
                            verbose=False
                        )
                        
                        if uv_stats['unwrapped'] > 0:
                            info_parts.append(f"UV unwrapped {uv_stats['unwrapped']} objects")
            
            # Perform mesh repair/cleaning if enabled (on temp copies)
            if settings.enable_mesh_repair:
                if not MESH_REPAIR_AVAILABLE:
                    self.report({'WARNING'}, "Mesh repair libraries not installed. Install trimesh for mesh repair.")
                else:
                    objects_to_repair = temp_objects if temp_objects else mesh_objects
                    
                    if objects_to_repair:
                        repaired_count = 0
                        total_verts_removed = 0
                        total_faces_removed = 0
                        
                        for obj in objects_to_repair:
                            success, stats = mesh_repair.repair_object(
                                obj,
                                remove_duplicate_verts=settings.repair_remove_duplicate_verts,
                                remove_duplicate_faces=settings.repair_remove_duplicate_faces,
                                remove_unreferenced_verts=settings.repair_remove_unreferenced_verts,
                                fix_normals=settings.repair_fix_normals,
                                fill_holes=settings.repair_fill_holes,
                                remove_degenerate=settings.repair_remove_degenerate,
                                make_watertight=settings.repair_make_watertight,
                                verbose=False
                            )
                            
                            if success:
                                repaired_count += 1
                                if 'vertices_removed' in stats:
                                    total_verts_removed += stats.get('vertices_removed', 0)
                                if 'faces_removed' in stats:
                                    total_faces_removed += stats.get('faces_removed', 0)
                            else:
                                self.report({'WARNING'}, f"Failed to repair {obj.name}: {stats.get('error', 'Unknown error')}")
                        
                        if repaired_count > 0:
                            repair_info = f"Repaired {repaired_count} objects"
                            if total_verts_removed > 0 or total_faces_removed > 0:
                                repair_info += f" (removed {total_verts_removed} verts, {total_faces_removed} faces)"
                            info_parts.append(repair_info)
            
            # Perform mesh decimation if enabled (on temp copies) - always use bmesh
            if settings.enable_decimation:
                if settings.decimate_type != 'COLLAPSE':
                    self.report({'WARNING'}, f"Decimation only supports Collapse type. {settings.decimate_type} type not supported.")
                else:
                    objects_to_decimate = temp_objects if temp_objects else mesh_objects
                    
                    if objects_to_decimate:
                        decimated_count = 0
                        total_faces_before = 0
                        total_faces_after = 0
                        
                        for obj in objects_to_decimate:
                            if len(obj.data.polygons) > 100:  # Only decimate high-poly objects
                                faces_before = len(obj.data.polygons)
                                total_faces_before += faces_before
                                
                                # Always use bmesh method with preserve options set to True
                                success, faces_before_check, faces_after, error_details = fast_decimation.fast_decimate_object(
                                    obj,
                                    target_ratio=settings.decimate_ratio,
                                    method='bmesh',
                                    preserve_uv_seams=True,
                                    preserve_sharp_edges=True,
                                    aggression=7,  # Default, not used for bmesh
                                    preserve_border=True  # Default, not used for bmesh
                                )
                                
                                if success:
                                    total_faces_after += faces_after
                                    decimated_count += 1
                                else:
                                    # Show detailed error information
                                    method_name = settings.decimation_method
                                    if error_details:
                                        self.report({'WARNING'}, f"{obj.name}: {error_details}")
                                    else:
                                        self.report({'WARNING'}, f"Failed to decimate {obj.name} with {method_name} method. Check Blender console for details.")
                        
                        if decimated_count > 0:
                            if total_faces_before > 0:
                                reduction_pct = ((total_faces_before - total_faces_after) / total_faces_before) * 100
                                info_parts.append(f"Decimated {decimated_count} objects ({reduction_pct:.0f}% reduction)")
                            else:
                                info_parts.append(f"Decimated {decimated_count} objects")
            
            # Analyze materials before export and block if unsupported materials found
            materials_to_analyze = []
            material_analysis_results = {}
            unsupported_materials = []
            
            if MATERIAL_ANALYZER_AVAILABLE:
                materials_to_analyze = material_analyzer.get_materials_to_analyze(context)
                
                for material in materials_to_analyze:
                    result = material_analyzer.analyze_material_readiness(material)
                    material_analysis_results[material.name] = {
                        'is_ready': result['is_ready'],
                        'issues': result['issues'],
                        'warnings': result['warnings']
                    }
                    
                    if not result['is_ready']:
                        unsupported_materials.append(material.name)
            
            # Block export if unsupported materials are present
            if unsupported_materials:
                material_list = ', '.join(unsupported_materials[:5])  # Show first 5
                if len(unsupported_materials) > 5:
                    material_list += f" (+{len(unsupported_materials) - 5} more)"
                
                self.report(
                    {'ERROR'}, 
                    f"Export blocked: {len(unsupported_materials)} unsupported material(s) found. "
                    f"Fix materials in Material Readiness panel: {material_list}"
                )
                return {'CANCELLED'}
            
            # Create temporary file for GLB export
            with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Prepare export parameters
            # If we have temp objects, they're already selected for export
            # Otherwise, restore original selection for export
            if not temp_objects and original_selection:
                bpy.ops.object.select_all(action='DESELECT')
                for obj in original_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if original_selection:
                    context.view_layer.objects.active = original_selection[0]
            
            export_params = {
                'filepath': tmp_path,
                'export_format': 'GLB',
                'use_selection': len(context.selected_objects) > 0,
                'export_apply': True,  # Apply modifiers
                'export_extras': True,  # Export custom properties to extras field
            }
            
            # Add Draco compression settings if enabled
            if settings.use_draco:
                export_params.update({
                    'export_draco_mesh_compression_enable': True,
                    'export_draco_mesh_compression_level': settings.draco_compression_level,
                    'export_draco_position_quantization': settings.draco_quantization_position,
                    'export_draco_normal_quantization': settings.draco_quantization_normal,
                    'export_draco_texcoord_quantization': settings.draco_quantization_texcoord,
                })
                info_parts.append(f"Draco Level {settings.draco_compression_level}")
            else:
                export_params['export_draco_mesh_compression_enable'] = False
                info_parts.append("Uncompressed")
            
            # Export to GLB with compression settings
            bpy.ops.export_scene.gltf(**export_params)
            
            # Read the GLB file
            with open(tmp_path, 'rb') as f:
                glb_data = f.read()
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            # Generate filename from Blender file
            blend_filepath = bpy.data.filepath
            if blend_filepath:
                # Get filename without path and extension
                filename = os.path.splitext(os.path.basename(blend_filepath))[0] + ".glb"
            else:
                # Fallback if file hasn't been saved
                filename = "untitled.glb"
            
            # Build metadata
            metadata = {
                "filename": filename,
                "scene_name": context.scene.name,
                "timestamp": datetime.now().isoformat(),
                "size": len(glb_data),
                "size_mb": f"{len(glb_data)/(1024*1024):.2f}",
                "export_settings": {
                    "compression": settings.compression_preset,
                    "draco_enabled": settings.use_draco,
                    "draco_level": settings.draco_compression_level if settings.use_draco else None,
                    "decimation_enabled": settings.enable_decimation,
                    "decimation_ratio": settings.decimate_ratio if settings.enable_decimation else None,
                    "decimation_method": settings.decimation_method if settings.enable_decimation else None,
                    "mesh_repair_enabled": settings.enable_mesh_repair,
                },
                "object_count": len(context.selected_objects),
            }
            
            # Add material analysis to metadata if available
            # Note: At this point, all materials are supported (we blocked export if not)
            if MATERIAL_ANALYZER_AVAILABLE and materials_to_analyze and material_analysis_results:
                metadata["materials"] = {
                    "total": len(materials_to_analyze),
                    "ready": len([m for m in materials_to_analyze if material_analysis_results[m.name]['is_ready']]),
                    "unsupported": [],  # Always empty since we block export if unsupported materials exist
                    "analysis": material_analysis_results
                }
            
            # Send to server with metadata
            try:
                req = urllib.request.Request(
                    'http://localhost:8080/upload-model',
                    data=glb_data,
                    headers={
                        'Content-Type': 'application/octet-stream',
                        'X-Model-Metadata': json.dumps(metadata)
                    },
                    method='POST'
                )
                with urllib.request.urlopen(req) as response:
                    pass  # Successfully uploaded
            except Exception as e:
                print(f"Failed to upload to server: {e}")
                # Fallback: store directly if upload fails
                server_instance.latest_glb = glb_data
                server_instance.latest_metadata = metadata
            
            # Report success
            size_mb = len(glb_data) / (1024 * 1024)
            info_str = f" ({', '.join(info_parts)})" if info_parts else ""
            self.report({'INFO'}, f"Exported {size_mb:.2f}MB{info_str} to Framo")
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
        
        finally:
            # Clean up temporary objects created for decimation/repair
            if temp_objects:
                # Deselect all first
                bpy.ops.object.select_all(action='DESELECT')
                
                # Delete temporary objects and their mesh data
                for temp_obj in temp_objects:
                    try:
                        # Check if object still exists
                        if temp_obj.name in bpy.data.objects:
                            # Get mesh data before deletion
                            mesh_data = temp_obj.data if temp_obj.data else None
                            mesh_name = mesh_data.name if mesh_data else None
                            
                            # Delete the object
                            bpy.data.objects.remove(temp_obj, do_unlink=True)
                            
                            # Remove the mesh data if it exists and isn't used elsewhere
                            if mesh_name and mesh_name in bpy.data.meshes:
                                mesh_data = bpy.data.meshes[mesh_name]
                                if mesh_data.users == 0:
                                    bpy.data.meshes.remove(mesh_data)
                    except Exception as e:
                        # Silently continue cleanup even if one object fails
                        print(f"Warning: Could not clean up temporary object {temp_obj.name}: {e}")
            
            # Restore original selection
            if original_selection:
                bpy.ops.object.select_all(action='DESELECT')
                for obj in original_selection:
                    if obj.name in bpy.data.objects:
                        obj.select_set(True)
                if original_selection:
                    bpy.context.view_layer.objects.active = original_selection[0]
        
        return {'FINISHED'}

class FRAMO_PT_export_panel(bpy.types.Panel):
    bl_label = "Framo Bridge"
    bl_idname = "FRAMO_PT_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Framo Export"
    
    def draw(self, context):
        layout = self.layout
        
        # Ensure property is registered (safety check)
        if not hasattr(context.scene, 'framo_export_settings'):
            layout.label(text="Error: Settings not initialized. Please reload addon.", icon='ERROR')
            return
        
        settings = context.scene.framo_export_settings
        
        # Server status in a box
        box = layout.box()
        global server_instance
        row = box.row()
        if server_instance:
            # Use a split to create visual emphasis
            split = row.split(factor=0.15)
            split.label(icon='CHECKMARK')  # Green checkmark icon
            split.label(text="Running")  # Text next to green icon
        else:
            row.label(text="Not Running", icon='ERROR')
        
        layout.separator()
        
        # Dependencies Status
        if DEPENDENCIES_AVAILABLE:
            dep_status = dependencies.check_all_dependencies()
            missing_required = [k for k, v in dep_status.items() if not v['installed'] and not v['optional']]
            
            if missing_required:
                box = layout.box()
                box.label(text="Dependencies", icon='PACKAGE')
                col = box.column(align=True)
                
                for key in missing_required:
                    dep = dep_status[key]
                    row = col.row()
                    row.label(text=f"{dep['name']}: Missing", icon='ERROR')
                
                col.separator()
                row = col.row()
                row.scale_y = 1.2
                op = row.operator("framo.install_dependencies", text="Install Required Dependencies", icon='IMPORT')
                
                # Show optional dependencies
                missing_optional = [k for k, v in dep_status.items() if not v['installed'] and v['optional']]
                if missing_optional:
                    col.separator()
                    col.label(text="Optional:", icon='INFO')
                    for key in missing_optional:
                        dep = dep_status[key]
                        row = col.row()
                        row.label(text=f"{dep['name']}: {dep['description']}")
                        op = row.operator("framo.install_dependencies", text="Install", icon='IMPORT')
                        op.package = dep['name']
        
        # Selection info
        layout.label(text="Selection:")
        box = layout.box()
        if context.selected_objects:
            box.label(text=f"  {len(context.selected_objects)} object(s)", icon='OBJECT_DATA')
        else:
            box.label(text="  Select Objects to export", icon='ERROR')
        
        layout.separator()
        
        # Export Settings (Compression + Mesh Optimization)
        row = layout.row()
        row.label(text="Export Settings:")
        row.operator("framo.reset_export_settings", text="", icon='FILE_REFRESH', emboss=False)
        box = layout.box()
        
        # Compression preset
        row = box.row()
        row.label(text="Compression", icon='MODIFIER')
        row.prop(settings, "compression_preset", text="")
        
        # Show custom compression settings if Custom is selected
        if settings.compression_preset == 'CUSTOM':
            col = box.column(align=True)
            col.prop(settings, "use_draco")
            
            if settings.use_draco:
                col.separator()
                col.prop(settings, "draco_compression_level")
                col.separator()
                col.label(text="Quantization Bits:")
                col.prop(settings, "draco_quantization_position")
                col.prop(settings, "draco_quantization_normal")
                col.prop(settings, "draco_quantization_texcoord")
        
        box.separator()
        
        # Auto UV Unwrap
        row = box.row()
        row.label(text="Auto UV Unwrap (if no uv map present)", icon='UV')
        row.prop(settings, "enable_auto_uv", text="", emboss=True)
        
        if settings.enable_auto_uv:
            col = box.column(align=True)
            col.scale_y = 0.85
            
            # Check how many selected objects need UV unwrapping
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH'] if context.selected_objects else []
            if mesh_objects and UV_UNWRAP_AVAILABLE:
                needs_uv = [obj for obj in mesh_objects if not uv_unwrap.has_uv_map(obj)]
                if needs_uv:
                    col.label(text=f"{len(needs_uv)} object(s) will be unwrapped", icon='INFO')
                else:
                    col.label(text="All objects already have UV maps", icon='CHECKMARK')
            elif not UV_UNWRAP_AVAILABLE:
                col.label(text="UV unwrap module not available", icon='ERROR')
        
        # Decimate
        row = box.row()
        row.label(text="Decimate", icon='MOD_DECIM')
        row.prop(settings, "enable_decimation", text="", emboss=True)
        
        if settings.enable_decimation:
            col = box.column(align=True)
            col.prop(settings, "decimate_ratio", slider=True)
            
            # Show decimation info (without objects count - that's in Selection section)
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH'] if context.selected_objects else []
            high_poly_objects = [obj for obj in mesh_objects if len(obj.data.polygons) > 100]
            if high_poly_objects:
                col.separator()
                total_faces = sum(len(obj.data.polygons) for obj in high_poly_objects)
                col.label(text=f"Total faces: {total_faces:,}")
                reduction = (1 - settings.decimate_ratio) * 100
                col.label(text=f"Est. reduction: {reduction:.0f}%")
        
        layout.separator()
        
        # Material Readiness Analyzer
        box = layout.box()
        box.label(text="Material Readiness", icon='MATERIAL')
        
        # Get materials to analyze
        has_unsupported_materials = False
        unsupported_count = 0
        unsupported_names = []
        
        # Check if objects are selected
        if not context.selected_objects:
            box.label(text="No Objects selected", icon='INFO')
        elif not MATERIAL_ANALYZER_AVAILABLE:
            box.label(text="Material analyzer not available", icon='ERROR')
        else:
            materials = material_analyzer.get_materials_to_analyze(context)
            
            if not materials:
                box.label(text="No materials found", icon='INFO')
            else:
                # Analyze all materials
                material_results = {}
                ready_count = 0
                
                for material in materials:
                    result = material_analyzer.analyze_material_readiness(material)
                    material_results[material] = result
                    if result['is_ready']:
                        ready_count += 1
                    else:
                        has_unsupported_materials = True
                        unsupported_count += 1
                        unsupported_names.append(material.name)
                
                # Summary
                summary_row = box.row()
                if unsupported_count > 0:
                    summary_row.label(text=f"{unsupported_count} material(s) need attention", icon='ERROR')
                else:
                    summary_row.label(text=f"All {len(materials)} materials ready", icon='CHECKMARK')
                
                # Only show materials that are NOT ready
                if unsupported_count > 0:
                    box.separator()
                    
                    # Material list - only show not ready materials
                    col = box.column(align=False)
                    for material in materials:
                        result = material_results[material]
                        material_name = material.name
                        
                        # Only show materials that are not ready
                        if not result['is_ready']:
                            # Check if this material is expanded
                            global material_expanded_states
                            is_expanded = material_expanded_states.get(material_name, False)
                            
                            # Main container box for problematic material
                            material_box = col.box()
                            material_col = material_box.column(align=False)
                            
                            # Material header with status, name, and expand/collapse button
                            header_row = material_col.row(align=True)
                            header_row.label(icon='X')
                            
                            # Material name - use split to make room for expand button
                            name_split = header_row.split(factor=0.85)
                            name_split.label(text=material_name)
                            
                            # Expand/collapse button
                            expand_op = name_split.operator(
                                "framo.toggle_material_expanded",
                                text="",
                                icon='TRIA_DOWN' if is_expanded else 'TRIA_RIGHT',
                                emboss=False
                            )
                            expand_op.material_name = material_name
                            
                            # Show details only if expanded
                            if is_expanded:
                                material_col.separator()
                                
                                # Issues section
                                if result['issues']:
                                    issues_col = material_col.column(align=False)
                                    
                                    for i, issue in enumerate(result['issues']):
                                        # Each issue gets its own row - force new line
                                        issue_row = issues_col.row()
                                        issue_row.scale_y = 0.9
                                        
                                        # Check if this is a header (ends with colon) or a list item
                                        if issue.endswith(':'):
                                            # Header - show with error icon
                                            issue_row.label(text=issue, icon='ERROR')
                                        elif issue.startswith('  •'):
                                            # List item with bullet - show as-is on its own line
                                            issue_row.label(text=issue)
                                        elif issue.startswith('  '):
                                            # Indented item without bullet - keep indentation
                                            issue_row.label(text=issue)
                                        else:
                                            # Regular item
                                            issue_row.label(text=issue)
                                        
                                        # Add small spacing between items for readability
                                        if i < len(result['issues']) - 1:
                                            issues_col.separator(factor=0.3)
                                    
                                    material_col.separator()
                                
                                # Warnings section
                                if result['warnings']:
                                    warnings_col = material_col.column(align=True)
                                    warnings_col.scale_y = 0.95
                                    warnings_col.label(text="Warnings:", icon='INFO')
                                    for warning in result['warnings']:
                                        warning_row = warnings_col.row()
                                        warning_row.scale_y = 0.95
                                        warning_row.label(text=f"  • {warning}")
                                    
                                    material_col.separator()
                                
                                # Replace button
                                replace_row = material_col.row()
                                replace_row.scale_y = 1.4
                                replace_op = replace_row.operator(
                                    "framo.replace_material",
                                    text="Replace Material",
                                    icon='MATERIAL'
                                )
                                replace_op.old_material_name = material_name
                            
                            # Add spacing after problematic material
                            col.separator()
        
        # Export button
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0
        
        # Use custom icon if available, otherwise use default EXPORT icon
        icon_id = get_framo_icon()
        
        # Check if button should be enabled (for showing messages)
        # The poll method will actually control button state
        button_enabled = True
        if not context.selected_objects:
            button_enabled = False
        elif has_unsupported_materials:
            button_enabled = False
        
        # Create operator button (poll method will handle actual enabling/disabling)
        if isinstance(icon_id, int):
            row.operator("framo.export_to_web", text="Send to Framo", icon_value=icon_id)
        else:
            row.operator("framo.export_to_web", text="Send to Framo", icon=icon_id)
        
        # Show warning message below button if disabled
        if not button_enabled:
            warning_row = layout.row()
            warning_row.scale_y = 0.9
            if not context.selected_objects:
                warning_row.label(
                    text="Select at least one object to export",
                    icon='ERROR'
                )
            elif has_unsupported_materials:
                warning_row.label(
                    text=f"Fix {unsupported_count} unsupported material(s) above to enable export",
                    icon='ERROR'
                )
        
class FRAMO_PT_optimization_tools(bpy.types.Panel):
    bl_label = "Optimization Tools"
    bl_idname = "FRAMO_PT_optimization_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Framo Export"
    
    def draw(self, context):
        layout = self.layout
        
        # Ensure property is registered (safety check)
        if not hasattr(context.scene, 'framo_export_settings'):
            layout.label(text="Error: Settings not initialized. Please reload addon.", icon='ERROR')
            return
        
        settings = context.scene.framo_export_settings
        
        # Mesh Repair/Cleaning Settings
        box = layout.box()
        # Title on left, checkbox on right
        row = box.row()
        row.label(text="Mesh Repair & Cleaning", icon='TOOL_SETTINGS')
        row.prop(settings, "enable_mesh_repair", text="", emboss=True)
        
        if settings.enable_mesh_repair:
            col = box.column(align=True)
            
            # Mesh repair status (only show if not available)
            if not MESH_REPAIR_AVAILABLE:
                row = col.row()
                row.label(text="Mesh repair not available", icon='ERROR')
                if DEPENDENCIES_AVAILABLE:
                    row = col.row()
                    op = row.operator("framo.install_dependencies", text="Install trimesh", icon='IMPORT')
                    op.package = "trimesh"
                else:
                    row = col.row()
                    row.label(text="Install trimesh manually", icon='INFO')
                col.separator()
            
            # Repair options
            col.prop(settings, "repair_remove_duplicate_verts")
            col.prop(settings, "repair_remove_duplicate_faces")
            col.prop(settings, "repair_remove_unreferenced_verts")
            col.prop(settings, "repair_fix_normals")
            col.prop(settings, "repair_remove_degenerate")
            
            # col.separator()
            # col.label(text="Advanced (may change geometry):", icon='INFO')
            # col.prop(settings, "repair_fill_holes")
            # col.prop(settings, "repair_make_watertight")
            
            # Repair button
            col.separator()
            row = col.row()
            row.scale_y = 1.2
            row.operator("framo.test_mesh_repair", text="Repair Mesh")

class FRAMO_OT_reset_export_settings(bpy.types.Operator):
    bl_idname = "framo.reset_export_settings"
    bl_label = "Reset Export Settings"
    bl_description = "Reset export settings to defaults"
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        # Reset compression settings
        settings.compression_preset = 'MEDIUM'
        settings.use_draco = True
        settings.draco_compression_level = 6
        settings.draco_quantization_position = 14
        settings.draco_quantization_normal = 10
        settings.draco_quantization_texcoord = 12
        
        # Reset UV unwrapping settings
        settings.enable_auto_uv = True
        
        # Reset decimation settings
        settings.enable_decimation = True
        settings.decimate_ratio = 0.1
        
        self.report({'INFO'}, "Export settings reset to defaults")
        return {'FINISHED'}

class FRAMO_OT_test_mesh_repair(bpy.types.Operator):
    bl_idname = "framo.test_mesh_repair"
    bl_label = "Repair Mesh"
    bl_description = "Analyze and repair mesh on selected objects"
    
    def execute(self, context):
        # Auto-open system console on Windows
        try:
            bpy.ops.wm.console_toggle()
        except:
            pass  # Console already open or not available
        
        if not MESH_REPAIR_AVAILABLE:
            self.report({'ERROR'}, "Mesh repair not available. Install trimesh.")
            return {'CANCELLED'}
        
        mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if not mesh_objects:
            self.report({'WARNING'}, "No mesh objects selected.")
            return {'CANCELLED'}
        
        settings = context.scene.framo_export_settings
        
        # Analyze all objects first
        analysis_results = []
        for obj in mesh_objects:
            issues = mesh_repair.analyze_object(obj)
            if issues:
                analysis_results.append((obj.name, issues))
        
        # Print analysis with flushing
        import sys
        
        def log(msg):
            print(msg)
            sys.stdout.flush()
        
        log("\n" + "="*60)
        log("MESH REPAIR - ANALYSIS")
        log("="*60)
        
        for obj_name, issues in analysis_results:
            log(f"\nObject: {obj_name}")
            log(f"  Vertices: {issues['vertex_count']}")
            log(f"  Faces: {issues['face_count']}")
            log(f"  Watertight: {issues['is_watertight']}")
            log(f"  Winding consistent: {issues['is_winding_consistent']}")
            log(f"  Has duplicate vertices: {issues['has_duplicate_vertices']}")
            log(f"  Has duplicate faces: {issues['has_duplicate_faces']}")
            log(f"  Has holes: {issues['has_holes']}")
            log(f"  Degenerate faces: {issues['degenerate_face_count']}")
        
        # Repair first object
        if mesh_objects:
            test_obj = mesh_objects[0]
            log(f"\n" + "="*60)
            log(f"REPAIRING: {test_obj.name}")
            log("="*60)
            
            success, stats = mesh_repair.repair_object(
                test_obj,
                remove_duplicate_verts=settings.repair_remove_duplicate_verts,
                remove_duplicate_faces=settings.repair_remove_duplicate_faces,
                remove_unreferenced_verts=settings.repair_remove_unreferenced_verts,
                fix_normals=settings.repair_fix_normals,
                fill_holes=settings.repair_fill_holes,
                remove_degenerate=settings.repair_remove_degenerate,
                make_watertight=settings.repair_make_watertight,
                verbose=True
            )
            
            if success:
                log(f"\nRepair Results:")
                log(f"  Vertices: {stats.get('vertices_before', 0)} -> {stats.get('vertices_after', 0)}")
                log(f"  Faces: {stats.get('faces_before', 0)} -> {stats.get('faces_after', 0)}")
                log(f"  Vertices removed: {stats.get('vertices_removed', 0)}")
                log(f"  Faces removed: {stats.get('faces_removed', 0)}")
                
                if 'issues_after' in stats:
                    after = stats['issues_after']
                    log(f"\nAfter repair:")
                    log(f"  Watertight: {after['is_watertight']}")
                    log(f"  Winding consistent: {after['is_winding_consistent']}")
                    log(f"  Degenerate faces: {after['degenerate_face_count']}")
                
                self.report({'INFO'}, f"Mesh repair completed. Check console for details.")
            else:
                self.report({'ERROR'}, f"Repair failed: {stats.get('error', 'Unknown error')}")
        
        log("\n" + "="*60 + "\n")
        
        return {'FINISHED'}

class FRAMO_OT_analyze_materials(bpy.types.Operator):
    bl_idname = "framo.analyze_materials"
    bl_label = "Refresh Material Analysis"
    bl_description = "Re-analyze all materials for GLB export readiness"
    
    def execute(self, context):
        if not MATERIAL_ANALYZER_AVAILABLE:
            self.report({'ERROR'}, "Material analyzer not available")
            return {'CANCELLED'}
        
        # Force UI refresh by tagging the area for redraw
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        materials = material_analyzer.get_materials_to_analyze(context)
        ready_count = 0
        
        for material in materials:
            result = material_analyzer.analyze_material_readiness(material)
            if result['is_ready']:
                ready_count += 1
        
        self.report({'INFO'}, f"Analyzed {len(materials)} materials: {ready_count} ready")
        return {'FINISHED'}

class FRAMO_OT_toggle_material_expanded(bpy.types.Operator):
    bl_idname = "framo.toggle_material_expanded"
    bl_label = "Toggle Material Details"
    bl_description = "Expand or collapse material details"
    
    material_name: bpy.props.StringProperty()
    
    def execute(self, context):
        global material_expanded_states
        material_name = self.material_name
        
        if material_name not in material_expanded_states:
            material_expanded_states[material_name] = False
        
        material_expanded_states[material_name] = not material_expanded_states[material_name]
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}

class FRAMO_OT_replace_material(bpy.types.Operator):
    bl_idname = "framo.replace_material"
    bl_label = "Replace Material"
    bl_description = "Replace this material with a valid GLB-compatible material"
    
    old_material_name: bpy.props.StringProperty()
    new_material_name: bpy.props.StringProperty()
    
    def invoke(self, context, event):
        if not MATERIAL_ANALYZER_AVAILABLE:
            self.report({'ERROR'}, "Material analyzer not available")
            return {'CANCELLED'}
        
        # Get valid materials
        valid_materials = material_analyzer.get_valid_materials(context)
        
        if not valid_materials:
            self.report({'WARNING'}, "No valid GLB-compatible materials found in scene")
            return {'CANCELLED'}
        
        # Show dialog with material selection
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout
        
        if not MATERIAL_ANALYZER_AVAILABLE:
            layout.label(text="Material analyzer not available", icon='ERROR')
            return
        
        # Get valid materials
        valid_materials = material_analyzer.get_valid_materials(context)
        
        if not valid_materials:
            layout.label(text="No valid materials found", icon='INFO')
            return
        
        layout.label(text=f"Replace '{self.old_material_name}' with:", icon='MATERIAL')
        layout.separator()
        
        # Create material selection list with buttons
        for material in valid_materials:
            row = layout.row()
            op = row.operator("framo.replace_material_execute", text=material.name, icon='MATERIAL')
            op.old_material_name = self.old_material_name
            op.new_material_name = material.name
    
    def execute(self, context):
        # Dialog is just for display, actual replacement handled by replace_material_execute
        return {'FINISHED'}

class FRAMO_OT_replace_material_execute(bpy.types.Operator):
    bl_idname = "framo.replace_material_execute"
    bl_label = "Execute Material Replacement"
    bl_description = "Execute the material replacement"
    
    old_material_name: bpy.props.StringProperty()
    new_material_name: bpy.props.StringProperty()
    
    def execute(self, context):
        if not MATERIAL_ANALYZER_AVAILABLE:
            self.report({'ERROR'}, "Material analyzer not available")
            return {'CANCELLED'}
        
        # Get materials by name
        old_material = bpy.data.materials.get(self.old_material_name)
        new_material = bpy.data.materials.get(self.new_material_name)
        
        if not old_material:
            self.report({'ERROR'}, f"Material '{self.old_material_name}' not found")
            return {'CANCELLED'}
        
        if not new_material:
            self.report({'ERROR'}, f"Material '{self.new_material_name}' not found")
            return {'CANCELLED'}
        
        # Verify new material is valid
        result = material_analyzer.analyze_material_readiness(new_material)
        if not result['is_ready']:
            self.report({'WARNING'}, f"Selected material '{self.new_material_name}' is not GLB-compatible")
            # Still allow replacement, but warn user
        
        # Replace material on objects
        updated_count = material_analyzer.replace_material_on_objects(old_material, new_material, context)
        
        if updated_count > 0:
            self.report({'INFO'}, f"Replaced material on {updated_count} object(s)")
        else:
            self.report({'WARNING'}, "No objects found with this material")
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


def start_server():
    global server_instance, server_thread
    
    try:
        server_instance = HTTPServer(('localhost', 8080), GLBRequestHandler)
        server_thread = threading.Thread(target=server_instance.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print("Framo Bridge server started on http://localhost:8080")
    except Exception as e:
        print(f"Failed to start server: {e}")
        server_instance = None

def stop_server():
    global server_instance, server_thread
    
    if server_instance:
        try:
            server_instance.shutdown()
            server_instance.server_close()
            
            # Wait for thread to finish (with timeout)
            if server_thread and server_thread.is_alive():
                server_thread.join(timeout=2.0)
            
            print("Framo Bridge server stopped")
        except Exception as e:
            print(f"Error stopping server: {e}")
        finally:
            server_instance = None
            server_thread = None

classes = [
    MaterialExpandedState,
    FramoExportSettings,
    FRAMO_OT_export_to_web,
    FRAMO_OT_reset_export_settings,
    FRAMO_OT_test_mesh_repair,
    FRAMO_OT_analyze_materials,
    FRAMO_OT_toggle_material_expanded,
    FRAMO_OT_replace_material,
    FRAMO_OT_replace_material_execute,
    FRAMO_PT_export_panel,
    FRAMO_PT_optimization_tools
]

# Add dependency operator if available
if DEPENDENCIES_AVAILABLE:
    classes.append(dependencies.FRAMO_OT_install_dependencies)

def load_custom_icons():
    """Load custom icons from the icons directory"""
    global custom_icons
    
    import bpy.utils.previews
    custom_icons = bpy.utils.previews.new()
    
    # Get addon directory
    addon_dir = os.path.dirname(__file__)
    icons_dir = os.path.join(addon_dir, "icons")
    
    # Try to load framo icon (PNG format)
    icon_paths = [
        os.path.join(icons_dir, "framo_icon.png"),
        os.path.join(icons_dir, "framo.png"),
        os.path.join(addon_dir, "framo_icon.png"),  # Fallback to root
    ]
    
    icon_loaded = False
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            try:
                custom_icons.load("framo_icon", icon_path, 'IMAGE')
                icon_loaded = True
                print(f"✓ Loaded custom Framo icon from: {icon_path}")
                break
            except Exception as e:
                print(f"Warning: Could not load icon from {icon_path}: {e}")
    
    if not icon_loaded:
        print("Info: Custom Framo icon not found. Using default EXPORT icon.")
        print(f"   Place your icon at: {icons_dir}/framo_icon.png")
    
    return custom_icons

def get_framo_icon():
    """Get the custom Framo icon ID, or fallback to default EXPORT icon"""
    global custom_icons
    if custom_icons and "framo_icon" in custom_icons:
        return custom_icons["framo_icon"].icon_id
    return 'EXPORT'  # Fallback to default Blender icon

def register():
    global custom_icons
    
    # Register classes first
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except ValueError:
            # Class already registered, skip
            pass
    
    # Register the property group (remove first if exists to avoid conflicts)
    if hasattr(bpy.types.Scene, 'framo_export_settings'):
        try:
            del bpy.types.Scene.framo_export_settings
        except:
            pass
    
    bpy.types.Scene.framo_export_settings = bpy.props.PointerProperty(type=FramoExportSettings)
    
    # Load custom icons
    load_custom_icons()
    
    start_server()

def unregister():
    global custom_icons
    
    stop_server()
    
    # Unregister the property group
    if hasattr(bpy.types.Scene, 'framo_export_settings'):
        try:
            del bpy.types.Scene.framo_export_settings
        except:
            pass
    
    # Unregister classes in reverse order
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            # Class not registered, skip
            pass
    
    # Unload custom icons
    if custom_icons:
        try:
            import bpy.utils.previews
            bpy.utils.previews.remove(custom_icons)
        except:
            pass
        custom_icons = None

if __name__ == "__main__":
    register()