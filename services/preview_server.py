import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import bpy
from ..utils.thread_safety import safe_user_info_access

# Global server instance
server_instance = None
server_thread = None

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
            with safe_user_info_access() as user_info:
                self.wfile.write(json.dumps(user_info).encode())
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
                self.wfile.write(json.dumps({"success": True}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(str(e).encode())
                
        elif self.path == '/connect-user':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                user_data = json.loads(post_data)
                
                with safe_user_info_access() as user_info:
                    user_info['name'] = user_data.get('name')
                    user_info['email'] = user_data.get('email')
                    user_info['last_connected'] = datetime.now().isoformat()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
                
                # Force UI redraw to show connected user
                # Schedule it on main thread
                def redraw():
                    for window in bpy.context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D':
                                area.tag_redraw()
                bpy.app.timers.register(lambda: (redraw(), None)[1])

            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    global server_instance, server_thread
    
    if server_instance:
        return

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

