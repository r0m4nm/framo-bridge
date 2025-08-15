# Blender to Web App GLB Export Addon - Complete Specification

## Project Overview

A Blender addon that simplifies the process of exporting 3D models as GLB files and sending them directly to a web application, with automatic optimization and preparation features.

---

## Development Cycle 1: Proof of Concept (MVP)

### Goal

Validate the basic architecture by implementing a simple one-click GLB export that sends data from Blender to a running web application.

### MVP Todo List

#### 1. Basic Blender Addon Structure

-   [ ] Create addon folder structure and `__init__.py`
-   [ ] Register basic operator for export button
-   [ ] Add simple UI panel in 3D viewport sidebar
-   [ ] Basic addon metadata (name, version, author)

#### 2. Simple HTTP Server

-   [ ] Start local HTTP server on addon enable (port 8080)
-   [ ] Basic CORS headers for browser access
-   [ ] Simple health check endpoint `/ping`
-   [ ] POST endpoint `/upload-model` to receive GLB data

#### 3. Basic GLB Export

-   [ ] Export selected objects (or full scene) to temporary GLB file
-   [ ] Use Blender's default export settings
-   [ ] Read GLB file as binary data
-   [ ] No optimization or processing (raw export)

#### 4. Data Transfer

-   [ ] Send GLB data via HTTP POST to localhost
-   [ ] Basic error handling for connection failures
-   [ ] Simple success/failure feedback in Blender UI

#### 5. Web App Integration

-   [ ] Create minimal test web page with Three.js
-   [ ] WebSocket or polling to check for new models
-   [ ] Load and display received GLB
-   [ ] Basic error handling

### MVP Implementation Code

```python
# __init__.py - Minimal Proof of Concept
bl_info = {
    "name": "Web GLB Exporter",
    "version": (0, 1, 0),
    "blender": (3, 0, 0),
    "category": "Import-Export",
}

import bpy
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Global server instance
server_instance = None

class GLBRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/upload-model':
            content_length = int(self.headers['Content-Length'])
            glb_data = self.rfile.read(content_length)

            # Store GLB data (in production, handle this better)
            self.server.latest_glb = glb_data

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode())

    def do_GET(self):
        if self.path == '/latest-model':
            if hasattr(self.server, 'latest_glb'):
                self.send_response(200)
                self.send_header('Content-type', 'model/gltf-binary')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(self.server.latest_glb)
            else:
                self.send_response(404)
                self.end_headers()

class WEB_EXPORT_OT_send_to_web(bpy.types.Operator):
    bl_idname = "web_export.send_to_web"
    bl_label = "Send to Web App"

    def execute(self, context):
        # Export to temporary file
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            bpy.ops.export_scene.gltf(
                filepath=tmp.name,
                export_format='GLB',
                use_selection=True
            )

            # Read GLB data
            with open(tmp.name, 'rb') as f:
                glb_data = f.read()

            # Send to server
            global server_instance
            if server_instance:
                server_instance.latest_glb = glb_data
                self.report({'INFO'}, f"Sent {len(glb_data)/1024:.1f}KB to web app")
            else:
                self.report({'ERROR'}, "Server not running")

        return {'FINISHED'}

class WEB_EXPORT_PT_panel(bpy.types.Panel):
    bl_label = "Web Export"
    bl_idname = "WEB_EXPORT_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Web Export"

    def draw(self, context):
        layout = self.layout
        layout.operator("web_export.send_to_web", icon='EXPORT')

def start_server():
    global server_instance
    server_instance = HTTPServer(('localhost', 8080), GLBRequestHandler)
    thread = threading.Thread(target=server_instance.serve_forever)
    thread.daemon = True
    thread.start()

def register():
    bpy.utils.register_class(WEB_EXPORT_OT_send_to_web)
    bpy.utils.register_class(WEB_EXPORT_PT_panel)
    start_server()

def unregister():
    bpy.utils.unregister_class(WEB_EXPORT_OT_send_to_web)
    bpy.utils.unregister_class(WEB_EXPORT_PT_panel)
    global server_instance
    if server_instance:
        server_instance.shutdown()
```

### Test Web Page (MVP)

```html
<!DOCTYPE html>
<html>
    <head>
        <title>Blender GLB Receiver</title>
        <script src="https://cdn.jsdelivr.net/npm/three@0.150.0/build/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.150.0/examples/js/loaders/GLTFLoader.js"></script>
    </head>
    <body>
        <div id="status">Waiting for model...</div>
        <script>
            // Setup Three.js scene
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(
                75,
                window.innerWidth / window.innerHeight,
                0.1,
                1000
            );
            const renderer = new THREE.WebGLRenderer();
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);

            const loader = new THREE.GLTFLoader();
            camera.position.z = 5;

            // Poll for new model
            setInterval(async () => {
                try {
                    const response = await fetch(
                        "http://localhost:8080/latest-model"
                    );
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);

                        loader.load(url, (gltf) => {
                            // Clear scene
                            while (scene.children.length > 0) {
                                scene.remove(scene.children[0]);
                            }
                            // Add new model
                            scene.add(gltf.scene);
                            document.getElementById("status").innerText =
                                "Model loaded!";
                        });
                    }
                } catch (e) {
                    console.log("Waiting for server...");
                }
            }, 2000);

            // Render loop
            function animate() {
                requestAnimationFrame(animate);
                if (scene.children[0]) {
                    scene.children[0].rotation.y += 0.01;
                }
                renderer.render(scene, camera);
            }
            animate();
        </script>
    </body>
</html>
```

### MVP Success Criteria

-   [ ] Can export a model from Blender with one click
-   [ ] Model appears in web browser within 2-3 seconds
-   [ ] No crashes or blocking of Blender UI
-   [ ] Basic error messages if connection fails
-   [ ] File size is reported to user

---

## Development Cycle 2: Full Feature Set

### Core Features

#### 1. Advanced Server Architecture

-   **WebSocket Server** for real-time bi-directional communication
-   **Authentication System** with license key validation
-   **Rate limiting** and request throttling
-   **Multi-client support** (multiple browser tabs/windows)
-   **Server status indicator** in Blender UI

#### 2. Geometry Optimization Pipeline

-   **Mesh Cleaning**

    -   Remove duplicate vertices
    -   Delete loose geometry
    -   Remove unused vertex groups
    -   Fix non-manifold edges
    -   Apply transforms

-   **Smart Decimation**

    -   Preserve UV seams
    -   Maintain sharp edges
    -   Target polygon count settings
    -   Multiple LOD generation

-   **Normal Optimization**
    -   Auto-smooth normals
    -   Custom split normals
    -   Weighted normals for better shading

#### 3. Automatic UV Operations

-   **Smart UV Unwrapping**

    -   Automatic seam detection
    -   Multiple unwrap algorithms (Smart UV, Lightmap, Cube projection)
    -   UV island packing optimization
    -   Texel density uniformization

-   **UV Layout Optimization**
    -   Minimize wasted texture space
    -   Automatic island rotation for better packing
    -   Margin control for mip-mapping
    -   Multiple UV channel support

#### 4. Material & Texture Optimization

-   **Material Merging**

    -   Detect and merge similar materials
    -   Automatic material deduplication
    -   Preserve unique material properties

-   **Texture Atlas Generation**

    -   Combine multiple textures into atlases
    -   Automatic UV remapping
    -   Smart packing algorithms
    -   Configurable atlas resolution

-   **Texture Optimization**
    -   Automatic resize based on importance
    -   Format conversion (PNG to JPEG where appropriate)
    -   Compression quality settings
    -   Remove unused textures

#### 5. Procedural Texture Baking

-   **Automatic Detection** of procedural materials
-   **Multi-channel Baking**

    -   Base Color
    -   Metallic
    -   Roughness
    -   Normal
    -   Ambient Occlusion
    -   Emission

-   **Baking Optimization**
    -   GPU acceleration when available
    -   Adaptive sampling
    -   Denoising
    -   Batch baking for multiple objects

#### 6. Advanced Baking Features

-   **Ambient Occlusion**

    -   Automatic UV generation if missing
    -   Contrast enhancement
    -   Multiple quality presets

-   **Normal Map Baking**

    -   High-poly to low-poly baking
    -   Cage generation
    -   Ray distance optimization

-   **PBR Map Generation**
    -   Roughness maps
    -   Metallic maps
    -   Combined ORM textures (Occlusion, Roughness, Metallic)

#### 7. Export Optimization

-   **Draco Compression**

    -   Geometry compression
    -   Configurable quality levels
    -   Quantization settings

-   **Format Options**

    -   GLB (binary)
    -   GLTF (separate files)
    -   USDZ (for AR)

-   **Selective Export**
    -   Export selected objects only
    -   Include/exclude animations
    -   Include/exclude morphs

#### 8. Live Link Features

-   **Real-time Updates**

    -   Stream transform changes
    -   Geometry update detection
    -   Material change sync

-   **Selective Sync**

    -   Transform-only mode (fast)
    -   Full geometry sync (slower)
    -   Smart delta updates

-   **Bidirectional Communication**
    -   Receive commands from web app
    -   Parameter adjustments
    -   Camera sync

#### 9. Quality Presets System

```python
quality_presets = {
    'preview': {
        'decimate_ratio': 0.1,
        'texture_size': 512,
        'skip_baking': True,
        'compression': 'aggressive'
    },
    'web_standard': {
        'decimate_ratio': 0.5,
        'texture_size': 1024,
        'bake_ao': True,
        'compression': 'balanced'
    },
    'high_quality': {
        'decimate_ratio': 0.8,
        'texture_size': 2048,
        'bake_all_maps': True,
        'compression': 'minimal'
    },
    'custom': {
        # User-defined settings
    }
}
```

#### 10. User Interface Features

-   **Progress Indicators**

    -   Export progress bar
    -   Step-by-step status
    -   Time estimation

-   **Settings Panel**

    -   Quality presets dropdown
    -   Advanced settings toggle
    -   Per-feature enable/disable

-   **Statistics Display**

    -   Original vs optimized file size
    -   Vertex/face count reduction
    -   Texture memory usage
    -   Estimated download time

-   **Batch Operations**
    -   Export multiple objects separately
    -   Queue system
    -   Batch settings

#### 11. Advanced Features

-   **Instance Detection**

    -   Convert duplicates to instances
    -   Linked duplicate optimization

-   **Vertex Color Conversion**

    -   Convert simple materials to vertex colors
    -   Eliminate textures for flat-colored objects

-   **Animation Optimization**

    -   Keyframe reduction
    -   Compression settings
    -   Selective animation export

-   **Metadata Embedding**
    -   Copyright information
    -   Author details
    -   Custom properties

#### 12. Error Handling & Recovery

-   **Validation System**

    -   Pre-export checks
    -   Mesh validity verification
    -   Material compatibility check

-   **Error Recovery**

    -   Automatic backup before processing
    -   Undo support
    -   Detailed error logging

-   **Fallback Options**
    -   Skip problematic objects
    -   Use alternative export methods
    -   Degraded mode operation

### Performance Targets

-   Models under 10MB: < 2 seconds total processing
-   Models 10-50MB: < 10 seconds
-   Models 50MB+: Progress indication with cancellation option
-   Memory usage: < 500MB additional RAM
-   No UI blocking during export

### Browser Compatibility

-   Chrome 90+
-   Firefox 88+
-   Safari 14+
-   Edge 90+
-   WebGL 2.0 support required

### Security Considerations

-   Local-only server binding (localhost)
-   Authentication token system
-   Rate limiting per session
-   Input validation for all parameters
-   Sanitization of file paths
-   License validation system

### Future Enhancements (Cycle 3+)

-   Cloud processing for heavy operations
-   Multi-user collaboration features
-   Version control integration
-   Automated testing suite
-   Plugin marketplace for extensions
-   Machine learning optimization suggestions
-   Direct integration with popular web frameworks
-   Mobile app companion

---

## Installation Instructions

### For Development (Cycle 1)

1. Clone the repository
2. Copy addon folder to Blender's scripts/addons directory
3. Enable addon in Blender preferences
4. Open test web page in browser
5. Select model and click "Send to Web App"

### For Production (Cycle 2)

1. Install via Blender addon manager
2. Enter license key when prompted
3. Configure quality preferences
4. Set up web app endpoint
5. Begin exporting optimized models

---

## Testing Checklist

### MVP Tests

-   [ ] Basic export works
-   [ ] Server starts/stops correctly
-   [ ] Web page receives model
-   [ ] Error handling for no selection
-   [ ] Multiple exports in succession

### Full Version Tests

-   [ ] All optimization features work
-   [ ] Large models (>100MB) handled gracefully
-   [ ] Procedural materials baked correctly
-   [ ] Texture atlasing preserves appearance
-   [ ] Memory cleanup after operations
-   [ ] Concurrent exports handled properly

---

## Documentation Requirements

-   User manual with screenshots
-   API documentation for web integration
-   Troubleshooting guide
-   Performance optimization tips
-   Video tutorials for common workflows

---

## Technical Implementation Details

### Optimization Functions Reference

#### Geometry Optimization

-   `remove_doubles()` - Merge vertices within threshold
-   `decimate_smart()` - Intelligent polygon reduction
-   `optimize_mesh_data()` - Clean loose geometry
-   `apply_transforms()` - Apply location/rotation/scale
-   `auto_smooth_normals()` - Optimize shading

#### UV Operations

-   `smart_uv_unwrap()` - Automatic UV mapping
-   `lightmap_pack()` - Optimized for baking
-   `optimize_uv_layout()` - Pack islands efficiently

#### Material Processing

-   `merge_similar_materials()` - Combine duplicate materials
-   `create_texture_atlas()` - Combine multiple textures
-   `bake_procedural_textures()` - Convert procedurals to images

#### Export Functions

-   `export_glb()` - Core export with compression
-   `validate_mesh()` - Pre-export validation
-   `calculate_statistics()` - Size and performance metrics

### API Endpoints

#### Server Endpoints

-   `POST /upload-model` - Receive GLB data
-   `GET /latest-model` - Retrieve latest export
-   `WS /live-sync` - WebSocket for real-time updates
-   `POST /auth/validate` - License validation
-   `GET /status` - Server health check

#### Client Commands

-   `export` - Trigger export from web
-   `update-settings` - Change export parameters
-   `cancel` - Cancel ongoing operation
-   `get-stats` - Request optimization statistics

### Data Formats

#### Export Configuration

```json
{
    "quality": "medium",
    "optimization": {
        "geometry": true,
        "materials": true,
        "textures": true
    },
    "export": {
        "format": "GLB",
        "compression": true,
        "animations": false
    }
}
```

#### Statistics Response

```json
{
    "original": {
        "fileSize": 15728640,
        "vertices": 50000,
        "faces": 100000,
        "materials": 12,
        "textures": 8
    },
    "optimized": {
        "fileSize": 3145728,
        "vertices": 12500,
        "faces": 25000,
        "materials": 3,
        "textures": 2
    },
    "reduction": {
        "percentage": 80,
        "processingTime": 4.5
    }
}
```

---

## License

This specification is for a proprietary Blender addon. All rights reserved.

---

## Contact

For questions about this specification or implementation details, please contact the development team.

---

_Document Version: 1.0.0_  
_Last Updated: 2024_
