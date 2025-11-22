import os
import bpy
import bpy.utils.previews

# Global icon collection
custom_icons = None

def load_custom_icons():
    global custom_icons
    if custom_icons:
        return

    custom_icons = bpy.utils.previews.new()
    # Assuming this file is in framo-bridge/ui/icons.py
    addon_dir = os.path.dirname(os.path.dirname(__file__)) 
    icons_dir = os.path.join(addon_dir, "icons")
    
    icon_paths = [
        os.path.join(icons_dir, "framo_icon.png"),
        os.path.join(icons_dir, "framo.png"),
    ]
    
    icon_path = None
    for path in icon_paths:
        if os.path.exists(path):
            icon_path = path
            break
            
    if icon_path:
        custom_icons.load("framo_icon", icon_path, 'IMAGE')

def unregister_custom_icons():
    global custom_icons
    if custom_icons:
        bpy.utils.previews.remove(custom_icons)
        custom_icons = None

def get_icon_id(name):
    """Get icon ID by name (e.g. 'framo_icon')"""
    global custom_icons
    if custom_icons and name in custom_icons:
        return custom_icons[name].icon_id
    return 0

