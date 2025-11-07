"""
Show error in text editor window
"""

import bpy
import bmesh

# Create or get text block
text_name = "DECIMATION_TEST_RESULT"
if text_name in bpy.data.texts:
    text = bpy.data.texts[text_name]
    text.clear()
else:
    text = bpy.data.texts.new(text_name)

obj = bpy.context.active_object

if not obj or obj.type != 'MESH':
    text.write("ERROR: Please select a mesh object first\n")
else:
    mesh = obj.data
    initial_faces = len(mesh.polygons)
    
    text.write(f"Object: {obj.name}\n")
    text.write(f"Initial: {initial_faces} faces, {len(mesh.vertices)} vertices\n\n")
    
    # Check face types
    tris = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
    quads = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
    ngons = sum(1 for p in mesh.polygons if len(p.vertices) > 4)
    text.write(f"Face types: {tris} tris, {quads} quads, {ngons} ngons\n\n")
    
    text.write("Available bmesh.ops decimation functions:\n")
    for attr in dir(bmesh.ops):
        if 'decim' in attr.lower():
            text.write(f"  - bmesh.ops.{attr}\n")
    
    text.write("\n--- Testing decimation ---\n\n")
    
    # Try bmesh decimation
    bm = bmesh.new()
    bm.from_mesh(mesh)
    
    text.write(f"1. Created bmesh: {len(bm.faces)} faces\n")
    
    # Triangulate
    non_tris = [f for f in bm.faces if len(f.verts) > 3]
    if non_tris:
        text.write(f"2. Triangulating {len(non_tris)} faces...\n")
        bmesh.ops.triangulate(bm, faces=non_tris)
        text.write(f"   After: {len(bm.faces)} faces\n")
    
    # Preprocessing
    text.write(f"3. Preprocessing...\n")
    bmesh.ops.dissolve_degenerate(bm, dist=0.0001, edges=bm.edges[:])
    loose_verts = [v for v in bm.verts if not v.link_faces]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.0001)
    text.write(f"   After: {len(bm.faces)} faces, {len(bm.verts)} vertices\n\n")
    
    # Try decimation with different methods
    target_ratio = 0.5
    
    text.write("4. Testing decimation methods:\n\n")
    
    # Method 1: decimate_collapse
    text.write("Method 1: bmesh.ops.decimate_collapse\n")
    try:
        bmesh.ops.decimate_collapse(bm, edges=bm.edges[:], target_faces=int(len(bm.faces) * target_ratio))
        text.write(f"  ✓ SUCCESS\n\n")
    except AttributeError as e:
        text.write(f"  ✗ AttributeError: {e}\n\n")
    except Exception as e:
        text.write(f"  ✗ {type(e).__name__}: {e}\n\n")
    
    # Method 2: decimate_dissolve
    text.write("Method 2: bmesh.ops.decimate_dissolve\n")
    try:
        bmesh.ops.decimate_dissolve(bm, angle_limit=0.0872665, use_face_split=False, use_boundary_tear=False, delimit={'NORMAL'})
        text.write(f"  ✓ SUCCESS - {len(bm.faces)} faces after\n\n")
    except AttributeError as e:
        text.write(f"  ✗ AttributeError: {e}\n\n")
    except Exception as e:
        text.write(f"  ✗ {type(e).__name__}: {e}\n\n")
    
    # Method 3: decimate (basic)
    text.write("Method 3: bmesh.ops.decimate\n")
    try:
        bmesh.ops.decimate(bm, faces=bm.faces[:], ratio=target_ratio)
        text.write(f"  ✓ SUCCESS - {len(bm.faces)} faces after\n\n")
    except AttributeError as e:
        text.write(f"  ✗ AttributeError: {e}\n\n")
    except Exception as e:
        text.write(f"  ✗ {type(e).__name__}: {e}\n\n")
    
    bm.free()
    
    text.write(f"\nFinal mesh: {len(mesh.polygons)} faces, {len(mesh.vertices)} vertices\n")
    text.write("\n" + "="*60 + "\n")
    text.write("Test complete!\n")

# Show the text in the text editor
for area in bpy.context.screen.areas:
    if area.type == 'TEXT_EDITOR':
        area.spaces[0].text = text
        break
else:
    # No text editor visible, try to split current area
    bpy.ops.screen.area_split(direction='VERTICAL', factor=0.5)
    bpy.context.area.type = 'TEXT_EDITOR'
    bpy.context.space_data.text = text

print(f"Results written to text block: {text_name}")

