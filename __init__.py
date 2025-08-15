bl_info = {
    "name": "Framo Web GLB Exporter",
    "author": "Roman Moor",
    "version": (0, 2, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Framo Export",
    "description": "Export GLB models directly to web applications with compression, decimation, and AO baking",
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

# Global server instance
server_instance = None
server_thread = None

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
        default='NONE',
        update=lambda self, context: update_compression_preset(self, context)
    )
    
    # Texture Baking Settings
    enable_baking: BoolProperty(
        name="Enable Texture Baking",
        description="Automatically bake procedural materials to textures",
        default=False
    )
    
    bake_resolution: IntProperty(
        name="Bake Resolution",
        description="Resolution for baked textures",
        default=1024,
        min=256,
        max=4096
    )
    
    bake_diffuse: BoolProperty(
        name="Bake Diffuse",
        description="Bake base color/diffuse maps",
        default=True
    )
    
    bake_normal: BoolProperty(
        name="Bake Normal",
        description="Bake normal maps",
        default=True
    )
    
    bake_roughness: BoolProperty(
        name="Bake Roughness",
        description="Bake roughness maps",
        default=True
    )
    
    bake_metallic: BoolProperty(
        name="Bake Metallic",
        description="Bake metallic maps",
        default=True
    )
    
    bake_ao: BoolProperty(
        name="Bake Ambient Occlusion",
        description="Bake ambient occlusion maps",
        default=False
    )
    
    bake_emission: BoolProperty(
        name="Bake Emission",
        description="Bake emission maps",
        default=False
    )
    
    auto_detect_procedural: BoolProperty(
        name="Auto-detect Procedural Materials",
        description="Automatically detect which objects need baking",
        default=True
    )
    
    # Advanced Baking Settings
    use_advanced_baking: BoolProperty(
        name="Advanced Baking",
        description="Use advanced channel isolation and adaptive resolution",
        default=True
    )
    
    adaptive_resolution: BoolProperty(
        name="Adaptive Resolution",
        description="Automatically adjust resolution based on material complexity",
        default=True
    )
    
    smart_uv_unwrap: BoolProperty(
        name="Smart UV Unwrapping",
        description="Automatically unwrap UVs with seam detection for optimal baking",
        default=True
    )
    
    bake_margin: IntProperty(
        name="Bake Margin",
        description="Margin in pixels to prevent edge bleeding",
        default=2,
        min=0,
        max=16
    )
    
    # Mesh Decimation Settings
    enable_decimation: BoolProperty(
        name="Enable Decimation",
        description="Reduce polygon count before export using decimate modifier",
        default=False
    )
    
    decimate_ratio: FloatProperty(
        name="Decimate Ratio",
        description="Ratio of faces to keep (1.0 = no reduction, 0.1 = 90% reduction)",
        default=0.5,
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
    
    adaptive_decimation: BoolProperty(
        name="Adaptive Decimation",
        description="Adjust decimation ratio based on object complexity",
        default=False
    )
    
    # Advanced AO Baking Settings
    enable_ao_baking: BoolProperty(
        name="Enable AO Baking",
        description="Bake high-quality ambient occlusion maps",
        default=False
    )
    
    ao_preset: EnumProperty(
        name="AO Preset",
        description="Predefined AO baking settings",
        items=[
            ('web_standard', "Web Standard", "Balanced quality for web use"),
            ('high_quality', "High Quality", "Best quality for hero assets"),
            ('mobile_optimized', "Mobile Optimized", "Fast baking for mobile targets"),
            ('architectural', "Architectural", "Optimized for buildings and interiors"),
            ('organic', "Organic", "Best for characters and organic models"),
            ('custom', "Custom", "Use custom AO settings"),
        ],
        default='web_standard'
    )
    
    ao_samples: IntProperty(
        name="AO Samples",
        description="Number of AO samples (higher = better quality, slower)",
        default=32,
        min=4,
        max=256
    )
    
    ao_distance: FloatProperty(
        name="AO Distance", 
        description="Maximum distance for AO rays",
        default=0.2,
        min=0.001,
        max=10.0,
        precision=3
    )
    
    ao_resolution: IntProperty(
        name="AO Resolution",
        description="Resolution of AO texture maps",
        default=1024,
        min=256,
        max=4096
    )
    
    ao_contrast: FloatProperty(
        name="AO Contrast",
        description="Adjust AO contrast (1.0 = no change)",
        default=1.2,
        min=0.1,
        max=3.0,
        precision=2
    )
    
    ao_brightness: FloatProperty(
        name="AO Brightness",
        description="Adjust AO brightness (0.0 = no change)",
        default=0.0,
        min=-0.5,
        max=0.5,
        precision=3
    )
    
    ao_adaptive_settings: BoolProperty(
        name="Adaptive AO Settings",
        description="Automatically adjust AO settings based on geometry analysis",
        default=True
    )
    
    ao_quality_validation: BoolProperty(
        name="Quality Validation",
        description="Validate AO quality and suggest improvements",
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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
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
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/upload-model':
            try:
                content_length = int(self.headers['Content-Length'])
                glb_data = self.rfile.read(content_length)
                
                # Store GLB data
                self.server.latest_glb = glb_data
                
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
    bl_description = "Export selected objects as GLB and send to web app"
    
    def execute(self, context):
        global server_instance
        
        if not server_instance:
            self.report({'ERROR'}, "Server not running. Please restart the addon.")
            return {'CANCELLED'}
        
        # Get settings
        settings = context.scene.framo_export_settings
        
        # Check if anything is selected
        if not context.selected_objects:
            self.report({'WARNING'}, "No objects selected. Exporting entire scene.")
        
        try:
            info_parts = []
            
            # Perform non-destructive mesh decimation if enabled
            temp_objects = []
            original_selection = context.selected_objects.copy() if context.selected_objects else []
            
            if settings.enable_decimation:
                mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH'] if context.selected_objects else [obj for obj in context.scene.objects if obj.type == 'MESH']
                
                if mesh_objects:
                    decimated_count = 0
                    total_faces_before = 0
                    total_faces_after = 0
                    
                    for obj in mesh_objects:
                        if len(obj.data.polygons) > 100:  # Only decimate high-poly objects
                            faces_before = len(obj.data.polygons)
                            total_faces_before += faces_before
                            
                            # Create temporary duplicate for decimation
                            temp_obj = obj.copy()
                            temp_obj.data = obj.data.copy()
                            temp_obj.name = f"TEMP_DECIMATED_{obj.name}"
                            
                            # Add to scene
                            context.collection.objects.link(temp_obj)
                            temp_objects.append(temp_obj)
                            
                            # Add decimate modifier to temp object
                            decimate_mod = temp_obj.modifiers.new(name="TempDecimate", type='DECIMATE')
                            decimate_mod.decimate_type = settings.decimate_type
                            
                            if settings.decimate_type == 'COLLAPSE':
                                decimate_mod.ratio = settings.decimate_ratio
                            elif settings.decimate_type == 'UNSUBDIV':
                                # Calculate iterations from ratio
                                iterations = max(1, int(-2 * (settings.decimate_ratio - 1)))
                                decimate_mod.iterations = min(iterations, 10)
                            elif settings.decimate_type == 'DISSOLVE':
                                decimate_mod.angle_limit = 0.087  # 5 degrees
                            
                            # Apply modifier to temp object
                            bpy.context.view_layer.objects.active = temp_obj
                            bpy.ops.object.modifier_apply(modifier=decimate_mod.name)
                            
                            faces_after = len(temp_obj.data.polygons)
                            total_faces_after += faces_after
                            decimated_count += 1
                            
                            # Hide original object temporarily
                            obj.hide_set(True)
                    
                    if decimated_count > 0:
                        if total_faces_before > 0:
                            reduction_pct = ((total_faces_before - total_faces_after) / total_faces_before) * 100
                            info_parts.append(f"Decimated {decimated_count} objects ({reduction_pct:.0f}% reduction)")
                        else:
                            info_parts.append(f"Decimated {decimated_count} objects")
                        
                        # Select temp objects for export
                        bpy.ops.object.select_all(action='DESELECT')
                        for temp_obj in temp_objects:
                            temp_obj.select_set(True)
            
            # Perform AO baking if enabled
            if settings.enable_ao_baking:
                ao_objects = temp_objects if temp_objects else ([obj for obj in context.selected_objects if obj.type == 'MESH'] if context.selected_objects else [obj for obj in context.scene.objects if obj.type == 'MESH'])
                suitable_ao_objects = [obj for obj in ao_objects if obj.type == 'MESH' and len(obj.data.polygons) > 50]
                
                if suitable_ao_objects:
                    self.report({'INFO'}, f"Baking AO for {len(suitable_ao_objects)} objects...")
                    
                    # Get AO settings from preset
                    if settings.ao_preset == 'custom':
                        ao_samples = settings.ao_samples
                        ao_distance = settings.ao_distance
                        ao_resolution = settings.ao_resolution
                    else:
                        preset_data = {
                            'web_standard': (32, 0.2, 1024),
                            'high_quality': (128, 0.1, 2048),
                            'mobile_optimized': (16, 0.3, 512),
                            'architectural': (64, 0.5, 1024),
                            'organic': (64, 0.05, 1024)
                        }
                        ao_samples, ao_distance, ao_resolution = preset_data.get(settings.ao_preset, (32, 0.2, 1024))
                    
                    # Simple AO baking implementation
                    try:
                        # Store original engine and settings
                        original_engine = context.scene.render.engine
                        context.scene.render.engine = 'CYCLES'
                        
                        # Configure AO baking
                        context.scene.cycles.samples = ao_samples
                        context.scene.render.bake.use_pass_direct = False
                        context.scene.render.bake.use_pass_indirect = False
                        context.scene.render.bake.margin = 2
                        context.scene.render.bake.use_clear = True
                        
                        ao_baked_count = 0
                        
                        for obj in suitable_ao_objects:
                            try:
                                # Ensure UV map exists
                                if not obj.data.uv_layers:
                                    bpy.context.view_layer.objects.active = obj
                                    bpy.ops.object.mode_set(mode='EDIT')
                                    bpy.ops.mesh.select_all(action='SELECT')
                                    bpy.ops.uv.smart_project(island_margin=0.02)
                                    bpy.ops.object.mode_set(mode='OBJECT')
                                
                                # Create AO image
                                ao_image = bpy.data.images.new(
                                    name=f"AO_{obj.name}",
                                    width=ao_resolution,
                                    height=ao_resolution,
                                    alpha=False
                                )
                                ao_image.colorspace_settings.name = 'Non-Color'
                                
                                # Create simple material for baking
                                if not obj.material_slots:
                                    mat = bpy.data.materials.new(f"TempAO_{obj.name}")
                                    mat.use_nodes = True
                                    obj.data.materials.append(mat)
                                
                                material = obj.material_slots[0].material
                                if material and material.use_nodes:
                                    # Add image texture node for baking
                                    nodes = material.node_tree.nodes
                                    tex_node = nodes.new('ShaderNodeTexImage')
                                    tex_node.image = ao_image
                                    tex_node.select = True
                                    nodes.active = tex_node
                                    
                                    # Select object and bake
                                    bpy.ops.object.select_all(action='DESELECT')
                                    obj.select_set(True)
                                    bpy.context.view_layer.objects.active = obj
                                    
                                    bpy.ops.object.bake(type='AO')
                                    ao_baked_count += 1
                                    
                                    # Remove temp texture node
                                    nodes.remove(tex_node)
                                    
                            except Exception as e:
                                print(f"Failed to bake AO for {obj.name}: {e}")
                                continue
                        
                        # Restore render engine
                        context.scene.render.engine = original_engine
                        
                        if ao_baked_count > 0:
                            info_parts.append(f"AO baked for {ao_baked_count} objects")
                        
                    except Exception as e:
                        print(f"AO baking failed: {e}")
                        context.scene.render.engine = original_engine
            
            # Create temporary file for GLB export
            with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            # Prepare export parameters
            export_params = {
                'filepath': tmp_path,
                'export_format': 'GLB',
                'use_selection': len(context.selected_objects) > 0,
                'export_apply': True,  # Apply modifiers
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
            
            # Store in server
            server_instance.latest_glb = glb_data
            
            # Report success
            size_mb = len(glb_data) / (1024 * 1024)
            info_str = f" ({', '.join(info_parts)})" if info_parts else ""
            self.report({'INFO'}, f"Exported {size_mb:.2f}MB{info_str} to web app")
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
        
        finally:
            # ALWAYS clean up temporary objects and restore originals
            if settings.enable_decimation and temp_objects:
                # Remove temporary decimated objects
                for temp_obj in temp_objects:
                    if temp_obj.name in bpy.data.objects:
                        bpy.data.objects.remove(temp_obj, do_unlink=True)
                
                # Restore original object visibility
                mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH'] if original_selection else [obj for obj in context.scene.objects if obj.type == 'MESH']
                for obj in mesh_objects:
                    obj.hide_set(False)
                
                # Restore original selection
                bpy.ops.object.select_all(action='DESELECT')
                if original_selection:
                    for obj in original_selection:
                        if obj.name in bpy.data.objects:
                            obj.select_set(True)
                    if original_selection:
                        bpy.context.view_layer.objects.active = original_selection[0]
        
        return {'FINISHED'}

class FRAMO_PT_export_panel(bpy.types.Panel):
    bl_label = "Framo Web Export"
    bl_idname = "FRAMO_PT_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Framo Export"
    
    def draw(self, context):
        layout = self.layout
        settings = context.scene.framo_export_settings
        
        # Server status
        global server_instance
        if server_instance:
            row = layout.row()
            row.label(text="Server Status: Running", icon='CHECKMARK')
            row = layout.row()
            row.label(text="http://localhost:8080")
        else:
            row = layout.row()
            row.label(text="Server Status: Not Running", icon='ERROR')
        
        layout.separator()
        
        # Compression Settings
        box = layout.box()
        box.label(text="Compression Settings", icon='MODIFIER')
        
        # Preset selector
        box.prop(settings, "compression_preset")
        
        # Show custom settings if Custom is selected
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
        
        layout.separator()
        
        # AO Baking Settings
        box = layout.box()
        box.label(text="Ambient Occlusion Baking", icon='SHADING_RENDERED')
        
        box.prop(settings, "enable_ao_baking")
        
        if settings.enable_ao_baking:
            col = box.column(align=True)
            col.prop(settings, "ao_preset")
            
            if settings.ao_preset == 'custom':
                col.separator()
                col.prop(settings, "ao_samples")
                col.prop(settings, "ao_distance")
                col.prop(settings, "ao_resolution")
                col.separator()
                col.prop(settings, "ao_contrast")
                col.prop(settings, "ao_brightness")
            
            col.separator()
            col.prop(settings, "ao_adaptive_settings")
            col.prop(settings, "ao_quality_validation")
            
            # Show AO info
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH'] if context.selected_objects else [obj for obj in context.scene.objects if obj.type == 'MESH']
            suitable_objects = [obj for obj in mesh_objects if len(obj.data.polygons) > 50]  # Simple filter
            if suitable_objects:
                col.separator()
                col.label(text=f"AO candidates: {len(suitable_objects)}", icon='INFO')
                
                # Estimate time based on preset
                if settings.ao_preset == 'custom':
                    samples = settings.ao_samples
                    resolution = settings.ao_resolution
                else:
                    preset_data = {
                        'web_standard': (32, 1024),
                        'high_quality': (128, 2048),
                        'mobile_optimized': (16, 512),
                        'architectural': (64, 1024),
                        'organic': (64, 1024)
                    }
                    samples, resolution = preset_data.get(settings.ao_preset, (32, 1024))
                
                time_factor = (samples / 32) * ((resolution / 1024) ** 2)
                estimated_time = len(suitable_objects) * 3.0 * time_factor
                col.label(text=f"Est. time: {estimated_time:.1f}s")
            else:
                col.separator()
                col.label(text="No suitable objects for AO", icon='ERROR')
        
        layout.separator()
        
        # Mesh Decimation Settings
        box = layout.box()
        box.label(text="Mesh Optimization", icon='MOD_DECIM')
        
        box.prop(settings, "enable_decimation")
        
        if settings.enable_decimation:
            col = box.column(align=True)
            col.prop(settings, "decimate_ratio", slider=True)
            col.prop(settings, "decimate_type")
            
            if settings.decimate_type == 'COLLAPSE':
                col.separator()
                col.prop(settings, "preserve_sharp_edges")
                col.prop(settings, "preserve_uv_seams")
            
            col.separator()
            col.prop(settings, "adaptive_decimation")
            
            # Show decimation info
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH'] if context.selected_objects else [obj for obj in context.scene.objects if obj.type == 'MESH']
            high_poly_objects = [obj for obj in mesh_objects if len(obj.data.polygons) > 100]
            if high_poly_objects:
                col.separator()
                total_faces = sum(len(obj.data.polygons) for obj in high_poly_objects)
                col.label(text=f"Objects: {len(high_poly_objects)}", icon='INFO')
                col.label(text=f"Total faces: {total_faces:,}")
                reduction = (1 - settings.decimate_ratio) * 100
                col.label(text=f"Est. reduction: {reduction:.0f}%")
        
        # Export button
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0
        row.operator("framo.export_to_web", text="Send to Web App", icon='EXPORT')
        
        # Info
        layout.separator()
        col = layout.column()
        col.label(text="Selection:")
        if context.selected_objects:
            col.label(text=f"  {len(context.selected_objects)} object(s)", icon='OBJECT_DATA')
        else:
            col.label(text="  Full scene", icon='SCENE_DATA')

def start_server():
    global server_instance, server_thread
    
    try:
        server_instance = HTTPServer(('localhost', 8080), GLBRequestHandler)
        server_thread = threading.Thread(target=server_instance.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        print("Framo Web Export server started on http://localhost:8080")
    except Exception as e:
        print(f"Failed to start server: {e}")
        server_instance = None

def stop_server():
    global server_instance, server_thread
    
    if server_instance:
        server_instance.shutdown()
        server_instance = None
        server_thread = None
        print("Framo Web Export server stopped")

classes = [
    FramoExportSettings,
    FRAMO_OT_export_to_web,
    FRAMO_PT_export_panel
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Register the property group
    bpy.types.Scene.framo_export_settings = bpy.props.PointerProperty(type=FramoExportSettings)
    
    start_server()

def unregister():
    stop_server()
    
    # Unregister the property group
    del bpy.types.Scene.framo_export_settings
    
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()