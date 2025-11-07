"""
Test modifier-based decimation
"""

import bpy

# Create or get text block for results
text_name = "MODIFIER_TEST_RESULT"
if text_name in bpy.data.texts:
    text = bpy.data.texts[text_name]
    text.clear()
else:
    text = bpy.data.texts.new(text_name)

obj = bpy.context.active_object

if not obj or obj.type != 'MESH':
    text.write("ERROR: Please select a mesh object first\n")
else:
    text.write(f"Testing Modifier Decimation\n")
    text.write(f"="*60 + "\n\n")
    
    text.write(f"Object: {obj.name}\n")
    text.write(f"Initial: {len(obj.data.polygons)} faces\n\n")
    
    target_ratio = 0.5
    
    try:
        # Add decimate modifier
        text.write(f"Adding Decimate modifier (ratio: {target_ratio})...\n")
        modifier = obj.modifiers.new(name="TestDecimate", type='DECIMATE')
        modifier.ratio = target_ratio
        modifier.decimate_type = 'COLLAPSE'
        
        text.write(f"Modifier added: {modifier.name}\n")
        text.write(f"Predicted result: ~{int(len(obj.data.polygons) * target_ratio)} faces\n\n")
        
        # Apply modifier
        text.write(f"Applying modifier...\n")
        
        # Ensure object mode
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Select object
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        
        # Apply
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        
        text.write(f"✓ SUCCESS!\n\n")
        text.write(f"Final: {len(obj.data.polygons)} faces\n")
        text.write(f"Reduction: {100 * (1 - len(obj.data.polygons) / (len(obj.data.polygons) / target_ratio)):.1f}%\n")
        
    except Exception as e:
        text.write(f"\n✗ FAILED\n")
        text.write(f"Error: {type(e).__name__}\n")
        text.write(f"{str(e)}\n\n")
        
        import traceback
        text.write("Full traceback:\n")
        text.write(traceback.format_exc())
        
        # Try to remove modifier
        try:
            if "TestDecimate" in obj.modifiers:
                obj.modifiers.remove(obj.modifiers["TestDecimate"])
        except:
            pass

# Show result
for area in bpy.context.screen.areas:
    if area.type == 'TEXT_EDITOR':
        area.spaces[0].text = text
        break

print(f"Test complete - check text: {text_name}")

