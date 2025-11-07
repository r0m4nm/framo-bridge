# Development Workflow Guide

## Fast Reload Without Restarting Blender

You **don't need to restart Blender** every time you change code! Here are faster methods:

### Method 1: Reload Button (Easiest)

1. **Make your code changes** in your editor
2. **Save the files**
3. **Open Blender** → Framo Export panel (N key)
4. **Click "🔄 Reload Addon (Dev)"** button at the bottom
5. **Done!** Changes are live

**Time:** ~2 seconds vs 30+ seconds for restart

### Method 2: Python Console (Fastest)

1. **Make your code changes** and save
2. **Open Blender Python Console** (Scripting workspace)
3. **Run:**
   ```python
   bpy.ops.framo.reload_addon()
   ```
4. **Done!**

**Time:** ~1 second

### Method 3: Keyboard Shortcut (Most Convenient)

1. **Open Blender** → Edit → Preferences → Keymap
2. **Search for:** "framo.reload_addon"
3. **Assign a shortcut** (e.g., `Ctrl+Shift+R`)
4. **Use shortcut** after making changes

**Time:** Instant after setup

### Method 4: Blender's Built-in Reload

Blender also has a built-in script reload:

1. **Make changes** and save
2. **In Python Console:**
   ```python
   import importlib
   import sys
   for module_name in list(sys.modules.keys()):
       if 'framo' in module_name.lower():
           importlib.reload(sys.modules[module_name])
   ```
3. **Re-register:**
   ```python
   import bpy
   bpy.utils.unregister_class(bpy.types.FRAMO_PT_export_panel)
   # ... unregister all classes ...
   # Then re-register
   ```

**Note:** The reload button does this automatically!

## What Gets Reloaded

The reload function reloads:
- ✅ `__init__.py` (main addon file)
- ✅ `dependencies.py`
- ✅ `fast_decimation.py`
- ✅ `mesh_repair.py`
- ✅ All registered classes
- ✅ UI panels and operators

## What Doesn't Get Reloaded

Some things still require a restart:
- ⚠️ **New dependencies** (trimesh, open3d) - need restart after `pip install`
- ⚠️ **Blender API changes** - if you change `bl_info` or addon structure
- ⚠️ **Property group changes** - sometimes need restart
- ⚠️ **Server port changes** - server needs restart

## Development Tips

### 1. Keep Console Open
- **Window → Toggle System Console**
- See reload messages and errors immediately
- Check for import errors

### 2. Test After Reload
- Always test your changes after reload
- Use the "Test Mesh Repair" button for quick testing
- Check UI updates immediately

### 3. When to Restart
Restart Blender if:
- Installing new Python packages
- Changing addon folder structure
- Reload fails with errors
- Strange behavior after reload

### 4. Hot Reload Workflow

**Recommended workflow:**
```
1. Edit code in your editor
2. Save file
3. Click "Reload Addon" button (or use shortcut)
4. Test immediately
5. Repeat
```

**Much faster than:**
```
1. Edit code
2. Save file
3. Close Blender
4. Open Blender
5. Enable addon
6. Test
7. Repeat (slow!)
```

## Troubleshooting

### "Reload failed"
- Check console for specific error
- May need to restart Blender
- Check for syntax errors in code

### "Changes not showing"
- Make sure you saved the file
- Check console for reload messages
- Try restarting Blender if reload doesn't work

### "Module not found after reload"
- Restart Blender
- Check file paths are correct
- Verify imports are correct

## Advanced: Auto-Reload on File Save

You can set up file watchers to auto-reload:

**Using watchdog (external script):**
```python
# watch_addon.py (run separately)
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import bpy

class AddonReloader(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            bpy.ops.framo.reload_addon()

observer = Observer()
observer.schedule(AddonReloader(), path='path/to/addon', recursive=True)
observer.start()
```

**Or use your editor's file watcher** + Blender's Python API.

## Performance

- **Reload:** ~1-2 seconds
- **Restart:** ~30-60 seconds
- **Speedup:** 15-30x faster!

## Best Practices

1. ✅ **Use reload for code changes**
2. ✅ **Restart for dependency changes**
3. ✅ **Keep console open during development**
4. ✅ **Test immediately after reload**
5. ✅ **Use keyboard shortcut for fastest workflow**

