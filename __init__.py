bl_info = {
    "name": "Framo Bridge",
    "author": "Roman Moor",
    "version": (0, 2, 7),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Framo Bridge",
    "description": "Export optimized GLB models directly to web applications with Draco compression, mesh decimation, and native texture scaling (no dependencies required)",
    "category": "Import-Export",
    "doc_url": "https://github.com/r0m4nm/framo-bridge",
    "tracker_url": "https://github.com/r0m4nm/framo-bridge/issues",
    "support": "COMMUNITY",
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

# Try to import decimation module
try:
    from . import decimation
    DECIMATION_AVAILABLE = True
except ImportError:
    DECIMATION_AVAILABLE = False
    print("Warning: decimation module not available.")

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

# Try to import texture scaler module (preferred - no dependencies)
try:
    from . import texture_scaler
    TEXTURE_SCALER_AVAILABLE = True
except ImportError:
    TEXTURE_SCALER_AVAILABLE = False
    print("Warning: texture_scaler module not available.")

# Try to import texture analyzer module (legacy Pillow-based)
try:
    from . import texture_analyzer
    TEXTURE_ANALYZER_AVAILABLE = True
except ImportError:
    TEXTURE_ANALYZER_AVAILABLE = False
    print("Warning: texture_analyzer module not available.")

# Try to import updater module
try:
    from . import updater
    UPDATER_AVAILABLE = True
except ImportError:
    UPDATER_AVAILABLE = False
    print("Warning: updater module not available.")

# Global server instance
server_instance = None
server_thread = None

# Global dictionary to track expanded state of materials in UI
material_expanded_states = {}

# Global storage for framo.app user info
framo_user_info = {
    "name": None,
    "email": None,
    "last_connected": None
}

# Global storage for update state
update_state = {
    "checking": False,
    "update_available": False,
    "latest_version": None,
    "update_info": None,
    "downloading": False,
    "installing": False,
    "download_progress": 0.0,
    "download_error": None,
    "pending_restart": False,
    "last_check_time": None
}

class FramoBridgePreferences(bpy.types.AddonPreferences):
    """Addon preferences for Framo Bridge"""
    bl_idname = __name__

    # Update settings
    auto_check_updates: BoolProperty(
        name="Automatically check for updates on startup",
        description="Check for updates every time Blender starts",
        default=True
    )

    def draw(self, context):
        global update_state
        
        layout = self.layout

        box = layout.box()
        box.label(text="Update Settings", icon='IMPORT')

        row = box.row()
        row.prop(self, "auto_check_updates")

        row = box.row()
        op = row.operator("framo.check_for_updates", text="Check for Updates Now", icon='FILE_REFRESH')
        
        # Show update check status
        if update_state.get("checking"):
            row = box.row()
            row.label(text="Checking for updates...", icon='TIME')
        elif update_state.get("download_error"):
            row = box.row()
            row.alert = True
            error_msg = update_state["download_error"]
            # Truncate long error messages
            if len(error_msg) > 60:
                error_msg = error_msg[:57] + "..."
            row.label(text=f"Error: {error_msg}", icon='ERROR')
        elif update_state.get("last_check_time"):
            row = box.row()
            if update_state.get("update_available"):
                latest = update_state.get("latest_version")
                if latest:
                    version_str = f"{latest[0]}.{latest[1]}.{latest[2]}"
                    row.label(text=f"Update available: v{version_str}", icon='IMPORT')
                    # Add install button
                    row = box.row()
                    row.scale_y = 1.5
                    if update_state.get("downloading"):
                        row.enabled = False
                        progress = update_state.get("download_progress", 0.0)
                        row.label(text=f"Downloading... {int(progress * 100)}%", icon='TIME')
                    elif update_state.get("installing"):
                        row.enabled = False
                        row.label(text="Installing update...", icon='TIME')
                    else:
                        op = row.operator("framo.install_update", text="Install Update Now", icon='IMPORT')
            else:
                current = bl_info["version"]
                version_str = f"{current[0]}.{current[1]}.{current[2]}"
                row.label(text=f"Up to date (v{version_str})", icon='CHECKMARK')


class MaterialExpandedState(PropertyGroup):
    """Property group to track expanded state of materials in the UI"""
    expanded: BoolProperty(
        name="Expanded",
        description="Whether this material's details are expanded",
        default=False
    )

class TextureExcludeMaterial(PropertyGroup):
    """Property group to store material names to exclude from texture optimization"""
    material_name: bpy.props.StringProperty(
        name="Material Name",
        description="Name of the material to exclude from texture optimization",
        default=""
    )

class SubdivExcludeObject(PropertyGroup):
    """Property group to store object names to exclude from subdivision override"""
    object_name: bpy.props.StringProperty(
        name="Object Name",
        description="Name of the object to exclude from subdivision override",
        default=""
    )

class SubdivIndividualOverride(PropertyGroup):
    """Property group to store individual subdivision override levels per object"""
    object_name: bpy.props.StringProperty(
        name="Object Name",
        description="Name of the object with individual subdivision override",
        default=""
    )
    
    override_level: bpy.props.IntProperty(
        name="Override Level",
        description="Individual subdivision level override for this object",
        default=3,
        min=0,
        max=4
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
    
    adaptive_decimation: BoolProperty(
        name="Adaptive Decimation",
        description="Adjust decimation ratio based on object complexity",
        default=False
    )
    
    # Subdivision Override Settings
    enable_subdiv_override: BoolProperty(
        name="Override Subdivision Level",
        description="Temporarily set all subdivision modifiers to a specific level during export",
        default=True
    )
    
    subdiv_override_level: IntProperty(
        name="Subdivision Level",
        description="Subdivision level to use during export (0 = no subdivision, higher = more detail)",
        default=3,
        min=0,
        max=4
    )
    
    subdiv_exclude_objects: bpy.props.CollectionProperty(
        type=SubdivExcludeObject,
        name="Excluded Objects",
        description="Objects to exclude from subdivision override"
    )
    
    subdiv_dropdown_expanded: BoolProperty(
        name="Show Affected Objects",
        description="Expand to show all objects affected by subdivision override",
        default=False
    )
    
    subdiv_individual_overrides: bpy.props.CollectionProperty(
        type=SubdivIndividualOverride,
        name="Individual Overrides",
        description="Individual subdivision level overrides per object"
    )
    
    subdiv_exclude_objects_index: bpy.props.IntProperty(
        name="Excluded Objects Index",
        default=0
    )
    
    # Texture Optimization Settings
    enable_texture_optimization: BoolProperty(
        name="Optimize Textures",
        description="Scale down textures and convert to JPEG for smaller file sizes",
        default=True
    )
    
    texture_max_size: EnumProperty(
        name="Max Texture Size",
        description="Maximum texture dimension (longest side will be scaled to this size)",
        items=[
            ('2048', "2K (2048px)", "Maximum texture size of 2048 pixels"),
            ('1024', "1K (1024px)", "Maximum texture size of 1024 pixels (recommended)"),
            ('512', "512px", "Maximum texture size of 512 pixels"),
            ('256', "256px", "Maximum texture size of 256 pixels"),
        ],
        default='1024'
    )
    
    texture_exclude_materials: bpy.props.CollectionProperty(
        type=TextureExcludeMaterial,
        name="Excluded Materials",
        description="Materials to exclude from texture optimization"
    )
    
    texture_exclude_materials_index: bpy.props.IntProperty(
        name="Excluded Materials Index",
        default=0
    )
    
    # Export status for loading indicator
    export_status: bpy.props.StringProperty(
        name="Export Status",
        description="Current export operation status",
        default=""
    )
    
    is_exporting: BoolProperty(
        name="Is Exporting",
        description="Whether an export operation is currently in progress",
        default=False
    )

def update_export_status(context, status_text):
    """Update export status and force UI refresh"""
    settings = context.scene.framo_export_settings
    settings.export_status = status_text
    
    # Force UI refresh
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
    
    # Force Blender to process events so UI updates immediately
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)

def clear_export_status(context):
    """Clear export status - used with timer"""
    try:
        settings = context.scene.framo_export_settings
        settings.export_status = ""
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except:
        pass  # Context may no longer be valid
    
    return None  # Don't repeat the timer

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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Model-Metadata, X-User-Info')
        self.end_headers()
    
    def do_GET(self):
        global framo_user_info

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
        elif self.path == '/user-info':
            # Return current connected user info
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(framo_user_info).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        global framo_user_info
        
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
        elif self.path == '/connect-user':
            # framo.app sends user info when user connects/authenticates
            try:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                user_data = json.loads(body.decode('utf-8'))

                # Update global user info
                framo_user_info['name'] = user_data.get('name')
                framo_user_info['email'] = user_data.get('email')
                framo_user_info['last_connected'] = datetime.now().isoformat()

                # Force UI refresh in Blender
                try:
                    import bpy
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D':
                                area.tag_redraw()
                except:
                    pass

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                response = {
                    "status": "success",
                    "message": f"Connected user: {user_data.get('name', 'Unknown')}"
                }
                self.wfile.write(json.dumps(response).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
        elif self.path == '/disconnect-user':
            # framo.app sends when user logs out or closes the app
            framo_user_info['name'] = None
            framo_user_info['email'] = None
            framo_user_info['last_connected'] = None

            # Force UI refresh
            try:
                import bpy
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()
            except:
                pass

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

class FRAMO_OT_export_to_web(bpy.types.Operator):
    bl_idname = "framo.export_to_web"
    bl_label = "Export to Web"
    bl_description = "Export selected objects as GLB and send to Framo"
    
    @classmethod
    def poll(cls, context):
        """Only allow export if objects are selected and user is connected"""
        # Require user to be connected to framo.app
        global framo_user_info
        if not framo_user_info.get('name'):
            return False

        # Require at least one selected object
        if not context.selected_objects:
            return False

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
        
        # Mark export as in progress
        settings.is_exporting = True
        update_export_status(context, "Preparing export...")
        
        # Initialize variables that need to be accessible in finally block
        temp_objects = []
        original_selection = context.selected_objects.copy() if context.selected_objects else []
        subdiv_original_levels = []  # Store original subdivision levels for restoration
        
        try:
            info_parts = []
            
            # Apply subdivision override if enabled
            if settings.enable_subdiv_override:
                update_export_status(context, "Applying subdivision override...")
                
                # Get excluded object names
                excluded_objects = [item.object_name for item in settings.subdiv_exclude_objects if item.object_name]
                
                # Get individual override levels
                individual_overrides = {item.object_name: item.override_level 
                                      for item in settings.subdiv_individual_overrides}
                
                # Get all objects to process (selected objects or temp copies if they exist)
                objects_to_check = context.selected_objects if context.selected_objects else []
                
                for obj in objects_to_check:
                    # Skip excluded objects
                    if obj.name in excluded_objects:
                        continue
                    
                    if obj.type == 'MESH':
                        for modifier in obj.modifiers:
                            if modifier.type == 'SUBSURF':
                                # Get current subdivision level (prefer render_levels if set, otherwise use levels)
                                current_viewport_level = modifier.levels
                                current_render_level = modifier.render_levels if hasattr(modifier, 'render_levels') and modifier.render_levels > 0 else modifier.levels
                                
                                # Check for individual override first, then fall back to global override
                                override_level = individual_overrides.get(obj.name, settings.subdiv_override_level)
                                
                                # Only override if override level is smaller than current level
                                # This ensures we only reduce subdivision, never increase it
                                should_override_viewport = override_level < current_viewport_level
                                should_override_render = override_level < current_render_level
                                
                                if should_override_viewport or should_override_render:
                                    # Store original levels
                                    original_viewport = modifier.levels
                                    original_render = modifier.render_levels if hasattr(modifier, 'render_levels') else modifier.levels
                                    subdiv_original_levels.append((obj, modifier, original_viewport, original_render))
                                    
                                    # Apply override only where needed
                                    if should_override_viewport:
                                        modifier.levels = override_level
                                    if hasattr(modifier, 'render_levels') and should_override_render:
                                        modifier.render_levels = override_level
                
                if subdiv_original_levels:
                    info_parts.append(f"Subdiv Override: Level {settings.subdiv_override_level}")

            
            # Create temporary copies of objects for decimation/repair
            # This ensures we never modify the original geometry in Blender
            original_to_temp = {}  # Map original objects to temporary copies
            
            # Process selected objects (we already checked selection exists)
            objects_to_process = context.selected_objects
            mesh_objects = [obj for obj in objects_to_process if obj.type == 'MESH']
            
            # Create temporary copies if decimation or UV unwrapping is enabled
            if (settings.enable_decimation or settings.enable_auto_uv) and mesh_objects:
                update_export_status(context, f"Creating temporary copies of {len(mesh_objects)} object(s)...")
                
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
                        update_export_status(context, f"UV unwrapping {len(objects_to_unwrap)} object(s)...")
                        uv_stats = uv_unwrap.auto_unwrap_objects(
                            objects_to_unwrap,
                            angle_limit=66.0,
                            island_margin=0.02,
                            verbose=False
                        )
                        
                        if uv_stats['unwrapped'] > 0:
                            info_parts.append(f"UV unwrapped {uv_stats['unwrapped']} objects")
            
            # Perform mesh decimation if enabled (on temp copies) - always use bmesh
            if settings.enable_decimation:
                objects_to_decimate = temp_objects if temp_objects else mesh_objects
                
                if objects_to_decimate:
                    update_export_status(context, f"Decimating {len(objects_to_decimate)} mesh(es)...")
                    
                    decimated_count = 0
                    total_faces_before = 0
                    total_faces_after = 0
                    
                    for idx, obj in enumerate(objects_to_decimate):
                        if len(obj.data.polygons) > 10:  # Only decimate high-poly objects
                            faces_before = len(obj.data.polygons)
                            total_faces_before += faces_before
                            
                            # Update status for this specific object
                            update_export_status(context, f"Decimating {obj.name} ({idx+1}/{len(objects_to_decimate)})...")
                            
                            # Always use bmesh method with preserve options set to True
                            success, faces_before_check, faces_after, error_details = decimation.decimate_object(
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
            
            # Analyze materials before export (informational only - doesn't block export)
            materials_to_analyze = []
            material_analysis_results = {}
            unsupported_materials = []
            
            update_export_status(context, "Analyzing materials...")
            
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
            
            # Warn about unsupported materials but don't block export
            if unsupported_materials:
                material_list = ', '.join(unsupported_materials[:5])  # Show first 5
                if len(unsupported_materials) > 5:
                    material_list += f" (+{len(unsupported_materials) - 5} more)"
                
                self.report(
                    {'WARNING'}, 
                    f"{len(unsupported_materials)} unsupported material(s) detected: {material_list}. Check Material Readiness panel."
                )
            
            # Process textures: scale down (NON-DESTRUCTIVE)
            # WebP conversion happens automatically in Blender's glTF exporter
            texture_scaled_copies = {}  # Track scaled copies for cleanup
            
            if settings.enable_texture_optimization and (TEXTURE_SCALER_AVAILABLE or TEXTURE_ANALYZER_AVAILABLE):
                update_export_status(context, "Optimizing textures...")
                try:
                    # Get target size from settings
                    target_size = int(settings.texture_max_size)

                    # Get excluded material names
                    excluded_materials = [item.material_name for item in settings.texture_exclude_materials if item.material_name]

                    # Scale down textures above target size
                    # This is NON-DESTRUCTIVE - originals remain in scene
                    # Format conversion to WebP happens automatically during GLB export via 'export_image_format': 'WEBP'

                    # Use native texture scaler (preferred - no dependencies) or fallback to Pillow-based
                    if TEXTURE_SCALER_AVAILABLE:
                        # Native Blender texture scaling - no external dependencies
                        texture_result = texture_scaler.process_textures_native(
                            context,
                            scale_to_target=True,
                            compress=False,  # glTF exporter handles WebP conversion
                            target_size=target_size,
                            excluded_materials=excluded_materials,
                            status_callback=lambda msg: update_export_status(context, msg)
                        )
                        # Map native result to expected format
                        texture_scaled_copies = texture_result.get('processed_images', {})
                    else:
                        # Fallback to Pillow-based texture analyzer
                        texture_result = texture_analyzer.process_textures(
                            context,
                            scale_to_1k=True,
                            convert_to_jpeg=False,  # glTF exporter handles WebP conversion
                            target_size=target_size,
                            excluded_materials=excluded_materials,
                            status_callback=lambda msg: update_export_status(context, msg)
                        )
                        texture_scaled_copies = texture_result.get('scaled_copies', {})

                    # Add texture processing info to export info
                    # Both native and Pillow-based return 'scaled' and 'errors' keys
                    scaled_count = texture_result.get('scaled', 0)
                    if scaled_count > 0:
                        size_label = settings.texture_max_size
                        method = "Native" if TEXTURE_SCALER_AVAILABLE else "Pillow"
                        info_parts.append(f"Scaled {scaled_count} texture(s) to {size_label}px ({method})")
                        info_parts.append("WebP export by glTF exporter")
                    
                    # Report errors if any
                    if texture_result['errors']:
                        for error in texture_result['errors'][:3]:  # Show first 3 errors
                            self.report({'WARNING'}, error)
                except Exception as e:
                    self.report({'WARNING'}, f"Texture processing error: {str(e)}")
            
            update_export_status(context, "Exporting GLB...")
            
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
                'export_image_format': 'WEBP',  # Convert all textures to WebP
                'export_texture_dir': '',  # Pack textures into GLB
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
            # Try with WEBP format first, with fallbacks if some images can't be converted
            export_success = False
            export_error = None
            
            try:
                bpy.ops.export_scene.gltf(**export_params)
                export_success = True
            except Exception as e:
                export_error = str(e)
                print(f"Export failed with WEBP image format: {e}")
                
                # Fallback 1: Try with AUTO (let Blender choose best format)
                try:
                    export_params['export_image_format'] = 'AUTO'
                    bpy.ops.export_scene.gltf(**export_params)
                    export_success = True
                    self.report({'WARNING'}, "Some textures couldn't convert to WebP - exported with AUTO format")
                except Exception as e2:
                    print(f"Export also failed with AUTO format: {e2}")
                    
                    # Fallback 2: Try with NONE (original format)
                    try:
                        export_params['export_image_format'] = 'NONE'
                        bpy.ops.export_scene.gltf(**export_params)
                        export_success = True
                        self.report({'WARNING'}, "Export completed with original texture formats (conversion failed)")
                    except Exception as e3:
                        export_error = str(e3)
                        print(f"Export also failed with NONE format: {e3}")
            
            if not export_success:
                raise Exception(f"GLB export failed: {export_error}")
            
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
            update_export_status(context, "Uploading to Framo...")
            
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
            
            update_export_status(context, f"✓ Export complete! ({size_mb:.2f}MB)")
            self.report({'INFO'}, f"Exported {size_mb:.2f}MB{info_str} to Framo")
            
            # Schedule status clear after 3 seconds
            bpy.app.timers.register(lambda: clear_export_status(context), first_interval=3.0)
            
        except Exception as e:
            update_export_status(context, f"✗ Export failed: {str(e)}")
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            
            # Schedule status clear after 5 seconds (longer for errors)
            bpy.app.timers.register(lambda: clear_export_status(context), first_interval=5.0)
            
            return {'CANCELLED'}
        
        finally:
            # Clear export status after a brief moment
            settings.is_exporting = False
            
            # Restore original subdivision levels
            if subdiv_original_levels:
                try:
                    for obj, modifier, original_viewport, original_render in subdiv_original_levels:
                        if obj and obj.name in bpy.data.objects:
                            # Find the modifier again (it should still exist)
                            for mod in obj.modifiers:
                                if mod == modifier and mod.type == 'SUBSURF':
                                    mod.levels = original_viewport
                                    if hasattr(mod, 'render_levels'):
                                        mod.render_levels = original_render
                                    break
                    
                    print("✓ Restored original subdivision levels after export")
                except Exception as e:
                    print(f"Warning: Could not fully restore subdivision levels: {e}")
            
            # Restore original textures and clean up temporary copies
            if TEXTURE_ANALYZER_AVAILABLE and texture_scaled_copies:
                try:
                    # Restore scaled texture references
                    for original_img, scaled_copy in texture_scaled_copies.items():
                        if original_img and original_img.name in bpy.data.images:
                            # Restore original in materials
                            texture_analyzer.replace_image_in_materials(context, scaled_copy, original_img)
                            
                            # Remove scaled copy from Blender data
                            if scaled_copy and scaled_copy.name in bpy.data.images:
                                bpy.data.images.remove(scaled_copy)
                    
                    print("✓ Restored original textures after export (non-destructive)")
                except Exception as e:
                    print(f"Warning: Could not fully restore textures: {e}")
            
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
    bl_label = f"Framo Bridge v{bl_info['version'][0]}.{bl_info['version'][1]}.{bl_info['version'][2]}"
    bl_idname = "FRAMO_PT_export_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Framo Bridge"

    def draw(self, context):
        global server_instance, framo_user_info, update_state

        layout = self.layout

        # Ensure property is registered (safety check)
        if not hasattr(context.scene, 'framo_export_settings'):
            layout.label(text="Error: Settings not initialized. Please reload addon.", icon='ERROR')
            return

        settings = context.scene.framo_export_settings

        # ============================================================================
        # Update System - Silent background updates only (no UI)
        # Updates are checked and installed automatically on Blender startup
        # ============================================================================
        # Manual update UI removed - updates happen silently in background

        # Connected user status
        box = layout.box()
        row = box.row()

        if framo_user_info['name']:
            # User connected - show name
            row.label(text=f"Connected: {framo_user_info['name']}", icon='LINKED')
        else:
            # No user connected
            row.label(text="Disconnected", icon='UNLINKED')

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

        # Export Settings (Compression + Mesh Optimization)
        row = layout.row()
        row.label(text="Export Settings:")
        row.operator("framo.reset_export_settings", text="", icon='FILE_REFRESH', emboss=False)
        main_box = layout.box()
        
        # Disable export settings if no objects selected
        main_box.enabled = len(context.selected_objects) > 0
        
        # Compression preset - in its own box
        compression_box = main_box.box()
        row = compression_box.row()
        row.label(text="Compression", icon='MODIFIER')
        row.prop(settings, "compression_preset", text="")
        
        # Show custom compression settings if Custom is selected
        if settings.compression_preset == 'CUSTOM':
            col = compression_box.column(align=True)
            col.prop(settings, "use_draco")
            
            if settings.use_draco:
                col.separator()
                col.prop(settings, "draco_compression_level")
                col.separator()
                col.label(text="Quantization Bits:")
                col.prop(settings, "draco_quantization_position")
                col.prop(settings, "draco_quantization_normal")
                col.prop(settings, "draco_quantization_texcoord")
        
        # Auto UV Unwrap - in its own box
        uv_box = main_box.box()
        row = uv_box.row()
        row.label(text="Auto UV Unwrap (if no uv map present)", icon='UV')
        row.prop(settings, "enable_auto_uv", text="", emboss=True)
        
        if settings.enable_auto_uv and not UV_UNWRAP_AVAILABLE:
            col = uv_box.column(align=True)
            col.scale_y = 0.85
            col.label(text="UV unwrap module not available", icon='ERROR')
        
        # Decimate - in its own box
        decimate_box = main_box.box()
        row = decimate_box.row()
        row.label(text="Decimate", icon='MOD_DECIM')
        row.prop(settings, "enable_decimation", text="", emboss=True)
        
        if settings.enable_decimation:
            col = decimate_box.column(align=True)
            col.prop(settings, "decimate_ratio", slider=True)
            
            # Show decimation info (without objects count - that's in Selection section)
            mesh_objects = [obj for obj in context.selected_objects if obj.type == 'MESH'] if context.selected_objects else []
            high_poly_objects = [obj for obj in mesh_objects if len(obj.data.polygons) > 10]
            if high_poly_objects:
                col.separator()
                total_faces = sum(len(obj.data.polygons) for obj in high_poly_objects)
                col.label(text=f"Total faces: {total_faces:,}")
                reduction = (1 - settings.decimate_ratio) * 100
                col.label(text=f"Est. reduction: {reduction:.0f}%")
        
        # Subdivision Override - in its own box
        subdiv_box = main_box.box()
        row = subdiv_box.row()
        row.label(text="Subdivision Override", icon='MOD_SUBSURF')
        row.prop(settings, "enable_subdiv_override", text="", emboss=True)
        
        if settings.enable_subdiv_override:
            col = subdiv_box.column(align=True)
            col.prop(settings, "subdiv_override_level", slider=True)
            
            # Show subdivision info for selected objects
            if context.selected_objects:
                # Get excluded object names
                excluded_objects = [item.object_name for item in settings.subdiv_exclude_objects if item.object_name]
                
                subdiv_objects = []
                for obj in context.selected_objects:
                    if obj.type == 'MESH':
                        for modifier in obj.modifiers:
                            if modifier.type == 'SUBSURF':
                                current_level = modifier.render_levels if hasattr(modifier, 'render_levels') and modifier.render_levels > 0 else modifier.levels
                                is_excluded = obj.name in excluded_objects
                                subdiv_objects.append((obj.name, current_level, is_excluded))
                                break
                
                if subdiv_objects:
                    col.separator()
                    
                    # Get individual override levels
                    individual_overrides = {item.object_name: item.override_level 
                                          for item in settings.subdiv_individual_overrides}
                    
                    # Filter to show objects that will be reduced, are excluded, or have individual overrides
                    objects_to_show = []
                    for name, level, excluded in subdiv_objects:
                        has_individual_override = name in individual_overrides
                        global_will_reduce = level > settings.subdiv_override_level
                        individual_will_reduce = has_individual_override and level > individual_overrides[name]
                        
                        if excluded or global_will_reduce or has_individual_override:
                            objects_to_show.append((name, level, excluded))
                    
                    if objects_to_show:
                        # Count non-excluded objects that will be overridden
                        non_excluded_count = sum(1 for _, level, excluded in objects_to_show if not excluded)
                        excluded_count = sum(1 for _, _, excluded in objects_to_show if excluded)
                        
                        # Create collapsible dropdown box
                        dropdown_box = col.box()
                        dropdown_row = dropdown_box.row()
                        
                        # Create summary text
                        if excluded_count > 0:
                            summary_text = f"{non_excluded_count} will be overridden, {excluded_count} excluded"
                        else:
                            summary_text = f"{non_excluded_count} object(s) will be overridden"
                        
                        # Show summary text on the left
                        dropdown_row.label(text=summary_text)
                        
                        # Toggle button with icon on the right
                        dropdown_row.prop(settings, 'subdiv_dropdown_expanded', 
                                        text="", 
                                        icon='TRIA_DOWN' if settings.subdiv_dropdown_expanded else 'TRIA_RIGHT',
                                        emboss=False, toggle=True)
                        
                        if settings.subdiv_dropdown_expanded:
                            dropdown_content = dropdown_box.column(align=True)
                            dropdown_content.scale_y = 0.85
                            
                            # Get individual override levels
                            individual_overrides = {item.object_name: item.override_level 
                                                  for item in settings.subdiv_individual_overrides}
                            
                            for obj_name, level, is_excluded in objects_to_show:
                                info_row = dropdown_content.row(align=True)
                                
                                if is_excluded:
                                    # Excluded objects: no checkbox, just show level
                                    info_row.label(text=f"{obj_name}: Level {level}")
                                else:
                                    # Check if object has individual override
                                    has_individual_override = obj_name in individual_overrides
                                    
                                    # Checkbox: checked = uses global override, unchecked = has individual override
                                    toggle_op = info_row.operator("framo.toggle_subdiv_exclusion", 
                                                                text="", 
                                                                icon='CHECKBOX_HLT' if not has_individual_override else 'CHECKBOX_DEHLT',
                                                                emboss=False)
                                    toggle_op.object_name = obj_name
                                    
                                    if has_individual_override:
                                        # Show individual override slider (unchecked = individual)
                                        override_item = None
                                        for item in settings.subdiv_individual_overrides:
                                            if item.object_name == obj_name:
                                                override_item = item
                                                break
                                        
                                        if override_item:
                                            info_row.label(text=f"{obj_name}: Level {level} →")
                                            slider_row = info_row.row(align=True)
                                            slider_row.scale_x = 1.0
                                            slider_row.prop(override_item, "override_level", text="", slider=True)
                                            
                                            # Remove individual override button
                                            remove_override_op = info_row.operator("framo.remove_individual_subdiv_override", 
                                                                                  text="", icon='X', emboss=False)
                                            remove_override_op.object_name = obj_name
                                    else:
                                        # Show global override info (checked = global override)
                                        info_row.label(text=f"{obj_name}: Level {level} → {settings.subdiv_override_level}")
        
        # Texture Optimization - in its own box
        texture_box = main_box.box()
        row = texture_box.row()
        row.label(text="Optimize Textures", icon='IMAGE_DATA')
        row.prop(settings, "enable_texture_optimization", text="", emboss=True)
        
        if settings.enable_texture_optimization:
            col = texture_box.column(align=True)
            
            # Check if Pillow is available
            if not TEXTURE_ANALYZER_AVAILABLE or not texture_analyzer.is_pillow_available():
                col.separator()
                warning_row = col.row()
                warning_row.scale_y = 0.9
                warning_row.label(text="Pillow not installed", icon='ERROR')
                
                if DEPENDENCIES_AVAILABLE:
                    install_row = col.row()
                    install_row.scale_y = 1.0
                    op = install_row.operator("framo.install_dependencies", text="Install Pillow", icon='IMPORT')
                    op.package = "Pillow"
            else:
                # Target size selector
                col.prop(settings, "texture_max_size", text="Max Size")
                
                # Show texture analysis for selected objects
                if context.selected_objects:
                    try:
                        # Get excluded material names
                        excluded_materials = [item.material_name for item in settings.texture_exclude_materials if item.material_name]
                        
                        texture_analysis = texture_analyzer.analyze_textures(context, excluded_materials=excluded_materials)
                        target_size = int(settings.texture_max_size)
                        
                        if texture_analysis['total'] > 0:
                            # Count how many will be optimized based on target size
                            textures_above_target = sum(1 for img in texture_analysis['sizes'].keys() 
                                                       if max(texture_analysis['sizes'][img]) > target_size)
                            
                            col.separator()
                            info_row = col.row()
                            info_row.scale_y = 0.85
                            if textures_above_target > 0:
                                info_row.label(text=f"{texture_analysis['total']} textures ({textures_above_target} will be scaled)", icon='INFO')
                            else:
                                info_row.label(text=f"{texture_analysis['total']} textures (all within limit)", icon='CHECKMARK')
                        elif len(excluded_materials) > 0:
                            col.separator()
                            info_row = col.row()
                            info_row.scale_y = 0.85
                            info_row.label(text="All textures excluded", icon='INFO')
                    except Exception as e:
                        col.separator()
                        error_row = col.row()
                        error_row.scale_y = 0.85
                        error_row.label(text=f"Error: {str(e)}", icon='ERROR')
                
                # Exclude materials list
                col.separator()
                
                # List of excluded materials
                if len(settings.texture_exclude_materials) > 0:
                    list_col = col.column(align=True)
                    list_col.scale_y = 0.9
                    for i, item in enumerate(settings.texture_exclude_materials):
                        item_row = list_col.row(align=True)
                        item_row.label(text=f"  • {item.material_name}")
                        remove_op = item_row.operator("framo.remove_excluded_material", text="", icon='X', emboss=False)
                        remove_op.index = i
                
                # Add material button
                add_row = col.row()
                add_row.scale_y = 1.0
                add_row.operator("framo.add_excluded_material", text="Add Material to Exclude", icon='ADD')
        
        layout.separator()
        
        # Material Readiness Analyzer
        layout.label(text="Material Readiness:")
        box = layout.box()
        
        # Disable material readiness if no objects selected
        box.enabled = len(context.selected_objects) > 0
        
        # Get materials to analyze
        has_unsupported_materials = False
        unsupported_count = 0
        unsupported_names = []
        
        # Check if objects are selected
        if not context.selected_objects:
            # Box is disabled, no need to show message
            pass
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
                            
                            # Material header with status, name, expand/collapse button, and open shading button
                            header_row = material_col.row(align=True)
                            header_row.label(icon='X')
                            
                            # Material name - use split to make room for buttons
                            name_split = header_row.split(factor=0.7)
                            name_split.label(text=material_name)
                            
                            # Button row for actions
                            button_split = header_row.split(factor=0.3)
                            
                            # Open Shading button
                            open_shading_op = button_split.operator(
                                "framo.open_material_in_shading",
                                text="",
                                icon='SHADING_RENDERED',
                                emboss=False
                            )
                            open_shading_op.material_name = material_name
                            
                            # Expand/collapse button
                            expand_op = button_split.operator(
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
        
        # Export status indicator (loading indicator)
        if settings.is_exporting and settings.export_status:
            layout.separator()
            status_box = layout.box()
            status_box.alert = False
            status_row = status_box.row()
            status_row.alignment = 'CENTER'
            status_row.label(text=settings.export_status, icon='TIME')
        
        # Export button
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0
        
        # Disable button during export
        row.enabled = not settings.is_exporting
        
        # Use custom icon if available, otherwise use default EXPORT icon
        icon_id = get_framo_icon()
        
        # Check if button should be enabled (for showing messages)
        # The poll method will actually control button state
        button_enabled = True
        user_connected = framo_user_info.get('name') is not None

        if not user_connected:
            button_enabled = False
        elif not context.selected_objects:
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
            if not user_connected:
                warning_row.label(
                    text="No user connected to framo.app",
                    icon='INFO'
                )
            elif not context.selected_objects:
                warning_row.label(
                    text="Select at least one object to export",
                    icon='ERROR'
                )
        
        # Show info message if there are unsupported materials (warning only, doesn't block export)
        if has_unsupported_materials:
            warning_row = layout.row()
            warning_row.scale_y = 0.9
            warning_row.label(
                text=f"{unsupported_count} unsupported material(s) - check Material Readiness panel",
                icon='INFO'
            )
        
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
        
        # Reset subdivision override settings
        settings.enable_subdiv_override = True
        settings.subdiv_override_level = 3
        
        self.report({'INFO'}, "Export settings reset to defaults")
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

class FRAMO_OT_open_material_in_shading(bpy.types.Operator):
    bl_idname = "framo.open_material_in_shading"
    bl_label = "Open Material in Shading"
    bl_description = "Open Shading workspace and select this material"
    
    material_name: bpy.props.StringProperty()
    
    def execute(self, context):
        # Get the material
        material = bpy.data.materials.get(self.material_name)
        
        if not material:
            self.report({'ERROR'}, f"Material '{self.material_name}' not found")
            return {'CANCELLED'}
        
        # Find an object that uses this material
        target_object = None
        material_slot_index = 0
        
        # First, try to find it in selected objects
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                for i, slot in enumerate(obj.material_slots):
                    if slot.material == material:
                        target_object = obj
                        material_slot_index = i
                        break
                if target_object:
                    break
        
        # If not found in selected objects, search all objects
        if not target_object:
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    for i, slot in enumerate(obj.material_slots):
                        if slot.material == material:
                            target_object = obj
                            material_slot_index = i
                            break
                    if target_object:
                        break
        
        if not target_object:
            self.report({'WARNING'}, f"No object found using material '{self.material_name}'")
            return {'CANCELLED'}
        
        # Deselect all objects first
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select and activate the target object
        target_object.select_set(True)
        context.view_layer.objects.active = target_object
        
        # Set the material slot as active
        target_object.active_material_index = material_slot_index
        
        # Switch to Shading workspace
        # Try to find the Shading workspace
        shading_workspace = None
        for workspace in bpy.data.workspaces:
            if workspace.name == 'Shading':
                shading_workspace = workspace
                break
        
        if shading_workspace:
            context.window.workspace = shading_workspace
        else:
            # Fallback: try to set workspace by name
            try:
                bpy.ops.screen.workspace_set(name='Shading')
            except:
                self.report({'WARNING'}, "Could not switch to Shading workspace. Please switch manually.")
        
        # Set the material as active in the context
        if target_object.active_material != material:
            target_object.active_material = material
        
        self.report({'INFO'}, f"Opened Shading workspace with material '{self.material_name}'")
        return {'FINISHED'}


class FRAMO_OT_add_excluded_material(bpy.types.Operator):
    bl_idname = "framo.add_excluded_material"
    bl_label = "Add Excluded Material"
    bl_description = "Add a material to exclude from texture optimization"
    
    material_name: bpy.props.EnumProperty(
        name="Material",
        description="Material to exclude from texture optimization",
        items=lambda self, context: [(m.name, m.name, "") for m in bpy.data.materials if m.name]
    )
    
    def invoke(self, context, event):
        if not bpy.data.materials:
            self.report({'WARNING'}, "No materials found in blend file")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "material_name", text="Material")
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        # Check if material already in exclude list
        for item in settings.texture_exclude_materials:
            if item.material_name == self.material_name:
                self.report({'WARNING'}, f"Material '{self.material_name}' is already in the exclude list")
                return {'CANCELLED'}
        
        # Add new item
        new_item = settings.texture_exclude_materials.add()
        new_item.material_name = self.material_name
        
        self.report({'INFO'}, f"Added '{self.material_name}' to exclude list")
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


class FRAMO_OT_remove_excluded_material(bpy.types.Operator):
    bl_idname = "framo.remove_excluded_material"
    bl_label = "Remove Excluded Material"
    bl_description = "Remove a material from the texture optimization exclude list"
    
    index: bpy.props.IntProperty()
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        if 0 <= self.index < len(settings.texture_exclude_materials):
            material_name = settings.texture_exclude_materials[self.index].material_name
            settings.texture_exclude_materials.remove(self.index)
            self.report({'INFO'}, f"Removed '{material_name}' from exclude list")
            
            # Force UI refresh
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        
        return {'FINISHED'}


def get_subdiv_objects_for_exclusion(self, context):
    """Get objects that would be affected by subdivision override"""
    settings = context.scene.framo_export_settings
    filtered_objects = []
    
    # Get excluded object names
    excluded_objects = [item.object_name for item in settings.subdiv_exclude_objects if item.object_name]
    
    print(f"\n=== DEBUG: Filtering objects for exclusion list ===")
    print(f"Override level: {settings.subdiv_override_level}")
    print(f"Already excluded: {excluded_objects}")
    
    # Check all mesh objects (not just selected, so we can exclude any object)
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        
        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                # Use exact same logic as UI display
                current_level = modifier.render_levels if hasattr(modifier, 'render_levels') and modifier.render_levels > 0 else modifier.levels
                
                print(f"  {obj.name}: level={current_level}, override={settings.subdiv_override_level}, excluded={obj.name in excluded_objects}")
                
                # Only include if current level is higher than override (will be reduced)
                # and not already excluded
                if current_level > settings.subdiv_override_level and obj.name not in excluded_objects:
                    print(f"    -> INCLUDED")
                    filtered_objects.append((obj.name, obj.name, ""))
                    break  # Found a qualifying modifier, no need to check others
                else:
                    print(f"    -> FILTERED OUT (level <= override or already excluded)")
                break
    
    print(f"Total filtered objects: {len(filtered_objects)}")
    return filtered_objects if filtered_objects else [("", "No objects to exclude", "")]


class FRAMO_OT_add_excluded_subdiv_object(bpy.types.Operator):
    bl_idname = "framo.add_excluded_subdiv_object"
    bl_label = "Add Excluded Object"
    bl_description = "Add an object to exclude from subdivision override"
    
    object_name: bpy.props.EnumProperty(
        name="Object",
        description="Object to exclude from subdivision override",
        items=get_subdiv_objects_for_exclusion
    )
    
    def invoke(self, context, event):
        # Get filterable objects
        filterable_objects = get_subdiv_objects_for_exclusion(self, context)
        
        # Check if there are any valid objects (ignore the placeholder)
        if not filterable_objects or (len(filterable_objects) == 1 and filterable_objects[0][0] == ""):
            self.report({'WARNING'}, "No mesh objects with subdivision levels higher than the override")
            return {'CANCELLED'}
        
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "object_name", text="Object")
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        # Check if empty placeholder was selected
        if not self.object_name or self.object_name == "":
            self.report({'WARNING'}, "No valid object selected")
            return {'CANCELLED'}
        
        # Check if object already in exclude list
        for item in settings.subdiv_exclude_objects:
            if item.object_name == self.object_name:
                self.report({'WARNING'}, f"Object '{self.object_name}' is already in the exclude list")
                return {'CANCELLED'}
        
        # Add new item
        new_item = settings.subdiv_exclude_objects.add()
        new_item.object_name = self.object_name
        
        self.report({'INFO'}, f"Added '{self.object_name}' to exclude list")
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


def get_object_subdiv_level(object_name):
    """Get the current subdivision level of an object"""
    obj = bpy.data.objects.get(object_name)
    if obj and obj.type == 'MESH':
        for modifier in obj.modifiers:
            if modifier.type == 'SUBSURF':
                # Prefer render_levels if set, otherwise use levels
                return modifier.render_levels if hasattr(modifier, 'render_levels') and modifier.render_levels > 0 else modifier.levels
    return 0


class FRAMO_OT_toggle_subdiv_exclusion(bpy.types.Operator):
    bl_idname = "framo.toggle_subdiv_exclusion"
    bl_label = "Toggle Subdivision Override Mode"
    bl_description = "Toggle between global override (checked) and individual override (unchecked)"
    
    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        # Check if object has individual override
        override_index = -1
        for i, item in enumerate(settings.subdiv_individual_overrides):
            if item.object_name == self.object_name:
                override_index = i
                break
        
        if override_index >= 0:
            # Remove individual override (switch to global override)
            settings.subdiv_individual_overrides.remove(override_index)
        else:
            # Add individual override (switch to individual override)
            # Initialize with the object's actual subdivision level
            actual_level = get_object_subdiv_level(self.object_name)
            new_item = settings.subdiv_individual_overrides.add()
            new_item.object_name = self.object_name
            new_item.override_level = actual_level
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


class FRAMO_OT_add_individual_subdiv_override(bpy.types.Operator):
    bl_idname = "framo.add_individual_subdiv_override"
    bl_label = "Add Individual Subdivision Override"
    bl_description = "Add an individual subdivision override for this object"
    
    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        # Check if object already has an individual override
        for item in settings.subdiv_individual_overrides:
            if item.object_name == self.object_name:
                self.report({'WARNING'}, f"Object '{self.object_name}' already has an individual override")
                return {'CANCELLED'}
        
        # Add new individual override with object's actual subdivision level
        actual_level = get_object_subdiv_level(self.object_name)
        new_item = settings.subdiv_individual_overrides.add()
        new_item.object_name = self.object_name
        new_item.override_level = actual_level
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


class FRAMO_OT_remove_individual_subdiv_override(bpy.types.Operator):
    bl_idname = "framo.remove_individual_subdiv_override"
    bl_label = "Remove Individual Subdivision Override"
    bl_description = "Remove individual subdivision override and use global override"
    
    object_name: bpy.props.StringProperty()
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        # Find and remove the individual override
        for i, item in enumerate(settings.subdiv_individual_overrides):
            if item.object_name == self.object_name:
                settings.subdiv_individual_overrides.remove(i)
                break
        
        # Force UI refresh
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        
        return {'FINISHED'}


class FRAMO_OT_remove_excluded_subdiv_object(bpy.types.Operator):
    bl_idname = "framo.remove_excluded_subdiv_object"
    bl_label = "Remove Excluded Object"
    bl_description = "Remove an object from the subdivision override exclude list"
    
    index: bpy.props.IntProperty()
    
    def execute(self, context):
        settings = context.scene.framo_export_settings
        
        if 0 <= self.index < len(settings.subdiv_exclude_objects):
            object_name = settings.subdiv_exclude_objects[self.index].object_name
            settings.subdiv_exclude_objects.remove(self.index)
            self.report({'INFO'}, f"Removed '{object_name}' from exclude list")
            
            # Force UI refresh
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
        
        return {'FINISHED'}


# ============================================================================
# Update System Operators
# ============================================================================

class FRAMO_OT_check_for_updates(bpy.types.Operator):
    """Check for Framo Bridge updates on GitHub"""
    bl_idname = "framo.check_for_updates"
    bl_label = "Check for Updates"
    bl_description = "Check GitHub for newer versions of Framo Bridge"

    def execute(self, context):
        global update_state

        if not UPDATER_AVAILABLE:
            self.report({'ERROR'}, "Updater module not available")
            return {'CANCELLED'}

        update_state["checking"] = True
        update_state["update_available"] = False
        update_state["download_error"] = None

        # Force UI update
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        # Check for updates in background thread
        def check_updates():
            global update_state

            try:
                print("Framo Bridge: Checking for updates...")
                current_version = bl_info["version"]
                update_info = updater.GitHubReleaseChecker.check_for_updates(current_version)

                if update_info:
                    update_state["update_available"] = True
                    update_state["latest_version"] = update_info.version
                    update_state["update_info"] = update_info
                    update_state["last_check_time"] = datetime.now()
                    update_state["download_error"] = None
                    print(f"Framo Bridge: Update available - v{update_info.tag_name}")
                    
                    # Auto-installation: Automatically download and install the update
                    print("Framo Bridge: Auto-installing update...")
                    try:
                        downloader = updater.UpdateDownloader(update_info)
                        
                        # Download
                        zip_path = downloader.download()
                        if zip_path and downloader.validate_zip(zip_path):
                            extracted_path = downloader.extract_update(zip_path)
                            if extracted_path:
                                # Save and install
                                updater.UpdateInstaller.save_pending_update(extracted_path, update_info.version)
                                success = updater.UpdateInstaller.install_pending_update()
                                if success:
                                    print("Framo Bridge: Update auto-installed successfully!")
                                    update_state["update_available"] = False
                                    print("Framo Bridge: Please restart Blender or reload the addon to use the new version.")
                                else:
                                    print("Framo Bridge: Auto-installation failed, you can install manually")
                            else:
                                print("Framo Bridge: Failed to extract update, you can install manually")
                        else:
                            print("Framo Bridge: Failed to download/validate update, you can install manually")
                    except Exception as e:
                        print(f"Framo Bridge: Auto-installation error: {e}")
                        import traceback
                        traceback.print_exc()
                        print("Framo Bridge: You can install the update manually using the button")
                else:
                    update_state["update_available"] = False
                    update_state["latest_version"] = current_version
                    update_state["last_check_time"] = datetime.now()
                    update_state["download_error"] = None
                    print("Framo Bridge: No updates available - you're on the latest version")

            except Exception as e:
                error_msg = str(e)
                print(f"Framo Bridge: Error checking for updates: {error_msg}")
                import traceback
                traceback.print_exc()
                update_state["download_error"] = error_msg
                update_state["update_available"] = False

            finally:
                update_state["checking"] = False

                # Force UI redraw - use safe context access
                try:
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D' or area.type == 'PREFERENCES':
                                area.tag_redraw()
                except (AttributeError, RuntimeError):
                    # Context not available - that's okay, UI will update on next refresh
                    pass

        thread = threading.Thread(target=check_updates)
        thread.daemon = True
        thread.start()

        self.report({'INFO'}, "Checking for updates... (check console for details)")
        return {'FINISHED'}


class FRAMO_OT_download_update(bpy.types.Operator):
    """Download and prepare Framo Bridge update"""
    bl_idname = "framo.download_update"
    bl_label = "Update Now"
    bl_description = "Download and install the latest version of Framo Bridge"

    def execute(self, context):
        global update_state

        if not UPDATER_AVAILABLE:
            self.report({'ERROR'}, "Updater module not available")
            return {'CANCELLED'}

        if not update_state.get("update_info"):
            self.report({'ERROR'}, "No update information available")
            return {'CANCELLED'}

        update_state["downloading"] = True
        update_state["download_progress"] = 0.0
        update_state["download_error"] = None

        # Force UI update
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

        # Download in background thread
        def download_and_prepare():
            global update_state

            try:
                update_info = update_state["update_info"]
                downloader = updater.UpdateDownloader(update_info)

                # Progress callback
                def on_progress(progress):
                    update_state["download_progress"] = progress
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D':
                                area.tag_redraw()

                # Download
                zip_path = downloader.download(progress_callback=on_progress)

                if not zip_path:
                    update_state["download_error"] = downloader.download_error
                    return

                # Validate
                if not downloader.validate_zip(zip_path):
                    update_state["download_error"] = "Invalid zip file"
                    return

                # Extract
                extracted_path = downloader.extract_update(zip_path)

                if not extracted_path:
                    update_state["download_error"] = "Failed to extract update"
                    return

                # Save pending update
                updater.UpdateInstaller.save_pending_update(extracted_path, update_info.version)

                # Mark as pending restart
                update_state["pending_restart"] = True
                update_state["download_error"] = None

            except Exception as e:
                print(f"Error downloading update: {e}")
                update_state["download_error"] = str(e)

            finally:
                update_state["downloading"] = False

                # Force UI redraw
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'VIEW_3D':
                            area.tag_redraw()

        thread = threading.Thread(target=download_and_prepare)
        thread.daemon = True
        thread.start()

        self.report({'INFO'}, "Downloading update...")
        return {'FINISHED'}


class FRAMO_OT_install_update(bpy.types.Operator):
    """Download and install Framo Bridge update immediately"""
    bl_idname = "framo.install_update"
    bl_label = "Install Update"
    bl_description = "Download and install the latest version of Framo Bridge immediately"

    def execute(self, context):
        global update_state

        if not UPDATER_AVAILABLE:
            self.report({'ERROR'}, "Updater module not available")
            return {'CANCELLED'}

        if not update_state.get("update_info"):
            self.report({'ERROR'}, "No update information available")
            return {'CANCELLED'}

        update_state["downloading"] = True
        update_state["installing"] = False
        update_state["download_progress"] = 0.0
        update_state["download_error"] = None

        # Force UI update
        for area in context.screen.areas:
            if area.type == 'VIEW_3D' or area.type == 'PREFERENCES':
                area.tag_redraw()

        # Download and install in background thread
        def download_and_install():
            global update_state

            try:
                update_info = update_state["update_info"]
                downloader = updater.UpdateDownloader(update_info)

                # Progress callback
                def on_progress(progress):
                    update_state["download_progress"] = progress
                    try:
                        for window in bpy.context.window_manager.windows:
                            for area in window.screen.areas:
                                if area.type == 'VIEW_3D' or area.type == 'PREFERENCES':
                                    area.tag_redraw()
                    except (AttributeError, RuntimeError):
                        pass

                print("Framo Bridge: Downloading update...")
                # Download
                zip_path = downloader.download(progress_callback=on_progress)

                if not zip_path:
                    update_state["download_error"] = downloader.download_error or "Download failed"
                    return

                print("Framo Bridge: Validating update...")
                # Validate
                if not downloader.validate_zip(zip_path):
                    update_state["download_error"] = "Invalid zip file"
                    return

                print("Framo Bridge: Extracting update...")
                # Extract
                extracted_path = downloader.extract_update(zip_path)

                if not extracted_path:
                    update_state["download_error"] = "Failed to extract update"
                    return

                print("Framo Bridge: Installing update...")
                update_state["downloading"] = False
                update_state["installing"] = True
                
                # Force UI update
                try:
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D' or area.type == 'PREFERENCES':
                                area.tag_redraw()
                except (AttributeError, RuntimeError):
                    pass

                # Install immediately (not pending)
                # Save as pending first, then install
                updater.UpdateInstaller.save_pending_update(extracted_path, update_info.version)
                
                # Install the update
                success = updater.UpdateInstaller.install_pending_update()

                if success:
                    print("Framo Bridge: Update installed successfully!")
                    update_state["installing"] = False
                    update_state["download_error"] = None
                    update_state["update_available"] = False
                    print("Framo Bridge: Update complete! Please restart Blender or reload the addon to use the new version.")
                else:
                    update_state["download_error"] = "Failed to install update"
                    update_state["installing"] = False

            except Exception as e:
                error_msg = str(e)
                print(f"Framo Bridge: Error installing update: {error_msg}")
                import traceback
                traceback.print_exc()
                update_state["download_error"] = error_msg
                update_state["downloading"] = False
                update_state["installing"] = False

            finally:
                update_state["downloading"] = False
                if not update_state.get("installing"):
                    # Force UI redraw
                    try:
                        for window in bpy.context.window_manager.windows:
                            for area in window.screen.areas:
                                if area.type == 'VIEW_3D' or area.type == 'PREFERENCES':
                                    area.tag_redraw()
                    except (AttributeError, RuntimeError):
                        pass

        thread = threading.Thread(target=download_and_install)
        thread.daemon = True
        thread.start()

        self.report({'INFO'}, "Downloading and installing update...")
        return {'FINISHED'}


class FRAMO_OT_view_changelog(bpy.types.Operator):
    """View changelog for the latest release"""
    bl_idname = "framo.view_changelog"
    bl_label = "View Changes"
    bl_description = "View changelog for the latest release"

    changelog_text: bpy.props.StringProperty(default="")

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        global update_state

        update_info = update_state.get("update_info")
        if update_info:
            self.changelog_text = update_info.changelog
        else:
            self.changelog_text = "No changelog available"

        return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)

        # Split changelog by lines
        lines = self.changelog_text.split('\n')
        for line in lines[:30]:  # Limit to first 30 lines
            col.label(text=line)

        if len(lines) > 30:
            col.label(text="... (view full changelog on GitHub)")


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
    FramoBridgePreferences,
    TextureExcludeMaterial,
    SubdivExcludeObject,
    SubdivIndividualOverride,
    MaterialExpandedState,
    FramoExportSettings,
    FRAMO_OT_export_to_web,
    FRAMO_OT_reset_export_settings,
    FRAMO_OT_analyze_materials,
    FRAMO_OT_toggle_material_expanded,
    FRAMO_OT_replace_material,
    FRAMO_OT_replace_material_execute,
    FRAMO_OT_open_material_in_shading,
    FRAMO_OT_add_excluded_material,
    FRAMO_OT_remove_excluded_material,
    FRAMO_OT_add_excluded_subdiv_object,
    FRAMO_OT_remove_excluded_subdiv_object,
    FRAMO_OT_toggle_subdiv_exclusion,
    FRAMO_OT_add_individual_subdiv_override,
    FRAMO_OT_remove_individual_subdiv_override,
    FRAMO_PT_export_panel,
    FRAMO_OT_check_for_updates,
    FRAMO_OT_install_update,
    FRAMO_OT_download_update,
    FRAMO_OT_view_changelog
]

# Add dependency operator if available
if DEPENDENCIES_AVAILABLE:
    classes.append(dependencies.FRAMO_OT_install_dependencies)

# Add update operators if available
if UPDATER_AVAILABLE:
    classes.extend([
        FRAMO_OT_check_for_updates,
        FRAMO_OT_download_update,
        FRAMO_OT_view_changelog
    ])

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


# ============================================================================
# Update System Startup Handler
# ============================================================================

@bpy.app.handlers.persistent
def check_pending_update_on_startup(dummy):
    """Check for pending updates on Blender startup and install if found."""
    global update_state

    if not UPDATER_AVAILABLE:
        return

    try:
        # First, check if there's a pending update to install
        if updater.UpdateInstaller.has_pending_update():
            print("Framo Bridge: Pending update detected, installing...")

            # Install the update
            success = updater.UpdateInstaller.install_pending_update()

            if success:
                print("Framo Bridge: Update installed successfully!")
                # The addon will be reloaded with the new version
            else:
                print("Framo Bridge: Failed to install pending update")
                updater.UpdateInstaller.clear_pending_update()
            return  # Don't check for new updates if we just installed one

        # Auto-check for updates if enabled in preferences
        # Use try-except since bpy.context might not be available during startup (especially on macOS)
        auto_check_enabled = True  # Default to True
        try:
            if hasattr(bpy.context, 'preferences'):
                prefs = bpy.context.preferences.addons.get(__name__)
                if prefs and hasattr(prefs, 'preferences'):
                    auto_check_enabled = prefs.preferences.auto_check_updates
        except (AttributeError, RuntimeError):
            # bpy.context not available - use default (check for updates)
            # This is common on macOS during startup
            pass

        if auto_check_enabled:
            # Check in background (non-blocking)
            def auto_check():
                global update_state
                try:
                    current_version = bl_info["version"]
                    update_info = updater.GitHubReleaseChecker.check_for_updates(current_version)

                    if update_info:
                        update_state["update_available"] = True
                        update_state["latest_version"] = update_info.version
                        update_state["update_info"] = update_info
                        update_state["last_check_time"] = datetime.now()
                        print(f"Framo Bridge: Update available - v{update_info.tag_name}")
                    else:
                        update_state["update_available"] = False
                        update_state["latest_version"] = current_version
                        update_state["last_check_time"] = datetime.now()
                except Exception as e:
                    print(f"Framo Bridge: Error auto-checking for updates: {e}")

            # Run in background thread
            thread = threading.Thread(target=auto_check)
            thread.daemon = True
            thread.start()

    except Exception as e:
        print(f"Framo Bridge: Error during startup update check: {e}")


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

    # Register update startup handler
    if UPDATER_AVAILABLE and check_pending_update_on_startup not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(check_pending_update_on_startup)

    start_server()

def unregister():
    global custom_icons

    stop_server()

    # Unregister update startup handler
    if UPDATER_AVAILABLE and check_pending_update_on_startup in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(check_pending_update_on_startup)

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