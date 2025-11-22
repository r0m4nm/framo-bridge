import bpy
from contextlib import contextmanager
from .logging_config import get_logger

# Get logger for this module
log = get_logger()

def _deferred_restore_selection(selected_names, active_name):
    """Restore selection after Blender has finished processing the operator.

    This runs as a timer callback to avoid crashes when restoring selection
    immediately after mesh data swaps.
    """
    log.debug(f"Deferred selection restore: Restoring {len(selected_names)} objects...")
    try:
        # Ensure we're in object mode
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')

        # Restore selection using names
        restored_count = 0
        for obj_name in selected_names:
            if obj_name in bpy.data.objects:
                obj = bpy.data.objects[obj_name]
                if obj and obj.name in bpy.context.view_layer.objects:
                    try:
                        obj.select_set(True)
                        restored_count += 1
                    except Exception as e:
                        log.debug(f"Deferred selection restore: Failed to select {obj_name}: {e}")

        log.debug(f"Deferred selection restore: Restored {restored_count}/{len(selected_names)} selections")

        # Restore active object
        if active_name and active_name in bpy.data.objects:
            obj = bpy.data.objects[active_name]
            if obj and obj.name in bpy.context.view_layer.objects:
                try:
                    bpy.context.view_layer.objects.active = obj
                    log.debug(f"Deferred selection restore: Set active to {active_name}")
                except Exception as e:
                    log.debug(f"Deferred selection restore: Failed to set active: {e}")

        log.debug("Deferred selection restore: Complete!")
    except Exception as e:
        log.debug(f"Deferred selection restore: Exception: {e}")

    return None  # Don't repeat the timer


@contextmanager
def preserve_blender_state():
    """Preserve and restore Blender selection/context state.

    Selection restoration is deferred to a timer callback to avoid crashes
    when the context manager exits after mesh data operations.
    """
    # Store current state - use names instead of object references
    prev_active_name = bpy.context.view_layer.objects.active.name if bpy.context.view_layer.objects.active else None
    prev_selected_names = [obj.name for obj in bpy.context.selected_objects]

    try:
        yield
    finally:
        # Defer selection restoration to after the operator returns
        # This prevents crashes when Blender tries to validate selection state
        # immediately after mesh data swaps
        log.debug(f"preserve_blender_state: Scheduling deferred restore for {len(prev_selected_names)} objects...")
        bpy.app.timers.register(
            lambda: _deferred_restore_selection(prev_selected_names, prev_active_name),
            first_interval=0.2  # Run after deferred cleanup (0.1s)
        )

@contextmanager
def temp_image_manager(original_image):
    """Safely manage temporary image creation and cleanup"""
    temp_image = None
    try:
        temp_image = original_image.copy()
        yield temp_image
    finally:
        if temp_image and temp_image.name in bpy.data.images:
            bpy.data.images.remove(temp_image)
            # print(f"Cleaned up temporary image: {temp_image.name}")

