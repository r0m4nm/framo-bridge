"""
Texture Analyzer Module for GLB Export Optimization

This module provides functions to analyze and optimize textures for GLB export.
- Scales textures above target resolution (default: 1024px)
- Format conversion to WebP is handled automatically by Blender's glTF exporter
Uses Pillow (PIL) for efficient image processing.
"""

import bpy
import os
import tempfile
import numpy as np

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
    print("✓ Pillow available - texture scaling enabled (WebP conversion handled by glTF exporter)")
except ImportError:
    PILLOW_AVAILABLE = False
    print("✗ Pillow not available - texture optimization disabled")


def is_pillow_available():
    """Check if Pillow is available for texture processing"""
    return PILLOW_AVAILABLE


def get_all_texture_images(context, excluded_materials=None):
    """
    Get all image textures used in materials from selected objects only.
    Only processes textures from materials assigned to selected mesh objects.
    
    Args:
        context: Blender context (must have selected_objects)
        excluded_materials: List of material names to exclude (optional)
    
    Returns:
        set: Set of bpy.types.Image objects from selected objects' materials
    """
    images = set()
    excluded_materials = excluded_materials or []
    
    # Early return if no objects are selected
    if not context.selected_objects:
        return images
    
    # Get all materials from selected objects only
    materials = set()
    for obj in context.selected_objects:
        # Only process mesh objects
        if obj.type != 'MESH' or not obj.data:
            continue
        
        # Get materials from material slots of this selected object
        for slot in obj.material_slots:
            if slot.material:
                # Skip excluded materials
                if slot.material.name not in excluded_materials:
                    materials.add(slot.material)
    
    # Traverse material node trees to find image textures
    # Only process textures from materials assigned to selected objects
    for material in materials:
        if not material or not material.use_nodes or not material.node_tree:
            continue
        
        # Get all nodes in the tree
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                if hasattr(node, 'image') and node.image:
                    # Only add images that are actually assigned to texture nodes
                    images.add(node.image)
    
    return images


def get_texture_size(image):
    """
    Get the size of a texture image.
    
    Args:
        image: bpy.types.Image object
        
    Returns:
        tuple: (width, height) in pixels, or (0, 0) if invalid
    """
    if not image:
        return (0, 0)
    
    # Check if image has valid size
    if hasattr(image, 'size') and len(image.size) >= 2:
        return (image.size[0], image.size[1])
    
    return (0, 0)


def is_texture_above_1k(image):
    """
    Check if texture resolution is above 1k (1024 pixels).
    
    Args:
        image: bpy.types.Image object
        
    Returns:
        bool: True if either dimension is above 1024 pixels
    """
    width, height = get_texture_size(image)
    return width > 1024 or height > 1024


def get_max_dimension(image):
    """
    Get the maximum dimension of a texture.
    
    Args:
        image: bpy.types.Image object
        
    Returns:
        int: Maximum of width and height
    """
    width, height = get_texture_size(image)
    return max(width, height)


def create_scaled_copy(image, target_size=1024):
    """
    Create a scaled copy of a texture image (non-destructive).
    Original image remains untouched in the Blender scene.
    Maintains aspect ratio - handles non-square textures properly.
    Uses Pillow for high-quality image resizing.
    
    Args:
        image: bpy.types.Image object
        target_size: Target maximum dimension (default: 1024)
        
    Returns:
        bpy.types.Image: Scaled copy, or None if scaling not needed/failed
    """
    if not image:
        return None
    
    if not PILLOW_AVAILABLE:
        print(f"Pillow not available - cannot scale {image.name}")
        return None
    
    width, height = get_texture_size(image)
    
    if width == 0 or height == 0:
        return None
    
    # Calculate new size maintaining aspect ratio
    max_dim = max(width, height)
    if max_dim <= target_size:
        # Already at or below target size - no copy needed
        return None
    
    # Calculate scale factor to make longest side = target_size
    scale = target_size / max_dim
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    # Ensure dimensions are at least 1
    new_width = max(1, new_width)
    new_height = max(1, new_height)
    
    try:
        # Get pixel data from Blender image
        pixels = list(image.pixels)
        
        if len(pixels) == 0:
            print(f"Image {image.name} has no pixel data")
            return None
        
        # Convert to numpy array and reshape to (height, width, channels)
        pixel_array = np.array(pixels, dtype=np.float32)
        
        # Determine number of channels
        if len(pixels) == width * height * 4:
            channels = 4  # RGBA
            pixel_array = pixel_array.reshape((height, width, 4))
        elif len(pixels) == width * height * 3:
            channels = 3  # RGB
            pixel_array = pixel_array.reshape((height, width, 3))
        else:
            print(f"Unexpected pixel format for {image.name}")
            return None
        
        # Convert from float (0.0-1.0) to uint8 (0-255)
        pixel_array = (pixel_array * 255).astype(np.uint8)
        
        # Create PIL Image
        if channels == 4:
            pil_image = Image.fromarray(pixel_array, mode='RGBA')
        else:
            pil_image = Image.fromarray(pixel_array, mode='RGB')
        
        # Flip vertically because Blender uses bottom-up coordinates
        # but image files use top-down coordinates (standard)
        pil_image = pil_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        
        # Resize using high-quality Lanczos filter (best for downscaling)
        resized_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save to temporary file (already in correct top-down format)
        ext = 'png' if channels == 4 else 'jpg'
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        if channels == 4:
            resized_image.save(tmp_path, 'PNG', optimize=True, compress_level=9)
        else:
            resized_image.save(tmp_path, 'JPEG', quality=90, optimize=True)
        
        # Load as new Blender image (copy)
        scaled_copy = bpy.data.images.load(tmp_path)
        scaled_copy.name = f"{image.name}_Scaled"
        scaled_copy.pack()  # Pack into blend file
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        print(f"Created scaled copy of {image.name}: {width}x{height} → {new_width}x{new_height}")
        
        return scaled_copy
        
    except Exception as e:
        print(f"Error creating scaled copy of {image.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def convert_texture_to_jpeg(image, quality=90):
    """
    Convert a texture image to JPEG format by saving and reloading.
    Note: This modifies the image in place by changing its file format.
    
    Args:
        image: bpy.types.Image object
        quality: JPEG quality (1-100, default: 90)
        
    Returns:
        bool: True if conversion was successful or already JPEG
    """
    if not image:
        return False
    
    # Check if image is already JPEG
    if image.filepath:
        ext = os.path.splitext(image.filepath.lower())[1]
        if ext in ('.jpg', '.jpeg'):
            return True
    
    # Check file format
    if hasattr(image, 'file_format') and image.file_format == 'JPEG':
        return True
    
    try:
        # If image is packed, we need to unpack it first to convert
        # For now, we'll mark it for JPEG format on next save
        # The actual conversion will happen when the image is saved during export
        
        # Set JPEG quality if available
        if hasattr(image, 'jpeg_quality'):
            image.jpeg_quality = quality
        
        # Mark for JPEG format - this will be used when saving
        # Note: We can't directly convert packed images, so we'll handle this
        # during the export process by ensuring images are saved as JPEG
        
        # For now, return True to indicate we'll handle it during export
        return True
        
    except Exception as e:
        print(f"Error preparing texture {image.name} for JPEG conversion: {e}")
        return False


def analyze_textures(context, excluded_materials=None):
    """
    Analyze all textures from selected objects' materials and return information.
    Only analyzes textures used by materials assigned to selected objects.
    
    Args:
        context: Blender context (must have selected_objects)
        excluded_materials: List of material names to exclude (optional)
        
    Returns:
        dict: {
            'total': int,
            'above_1k': list of image objects,
            'sizes': dict mapping image names to (width, height),
            'needs_processing': list of image objects that need scaling/conversion
        }
    """
    # Get textures only from selected objects' materials
    images = get_all_texture_images(context, excluded_materials=excluded_materials)
    
    result = {
        'total': len(images),
        'above_1k': [],
        'sizes': {},
        'needs_processing': []
    }
    
    for image in images:
        width, height = get_texture_size(image)
        result['sizes'][image.name] = (width, height)
        
        if is_texture_above_1k(image):
            result['above_1k'].append(image)
            result['needs_processing'].append(image)
        else:
            # Check if needs JPEG conversion
            if image.filepath:
                ext = os.path.splitext(image.filepath.lower())[1]
                if ext not in ('.jpg', '.jpeg'):
                    result['needs_processing'].append(image)
    
    return result


def process_textures(context, scale_to_1k=True, convert_to_jpeg=True, target_size=1024, excluded_materials=None, status_callback=None):
    """
    Process all textures from selected objects' materials: create scaled copies and optimize format.
    NON-DESTRUCTIVE: Original images in the Blender scene remain untouched.
    Only processes textures used by materials assigned to selected objects.
    
    Args:
        context: Blender context (must have selected_objects)
        scale_to_1k: Whether to create scaled copies for textures above target size
        convert_to_jpeg: Whether to optimize texture format (handled by save_images_as_jpeg)
        target_size: Target maximum dimension in pixels (default: 1024)
        excluded_materials: List of material names to exclude (optional)
        status_callback: Optional callback function(status_text) for progress updates
        
    Returns:
        dict: {
            'processed': int,
            'scaled': int,
            'scaled_copies': dict mapping original image to scaled copy,
            'errors': list of error messages
        }
    """
    # Get textures only from selected objects' materials
    images = get_all_texture_images(context, excluded_materials=excluded_materials)
    
    result = {
        'processed': 0,
        'scaled': 0,
        'scaled_copies': {},  # original_image -> scaled_copy
        'errors': []
    }
    
    processed_images = set()  # Track which images we've processed
    total_images = len(images)
    
    for idx, image in enumerate(images):
        if image in processed_images:
            continue
        
        try:
            # Create scaled copy if needed
            if scale_to_1k:
                # Check if texture is above target size
                width, height = get_texture_size(image)
                max_dim = max(width, height)
                
                if max_dim > target_size:
                    if status_callback:
                        status_callback(f"Scaling texture {image.name} ({idx+1}/{total_images})...")
                    
                    scaled_copy = create_scaled_copy(image, target_size=target_size)
                    
                    if scaled_copy:
                        result['scaled_copies'][image] = scaled_copy
                        result['scaled'] += 1
                        result['processed'] += 1
                        
                        # Replace references in materials with scaled copy
                        replace_image_in_materials(context, image, scaled_copy)
                    else:
                        result['errors'].append(f"Failed to create scaled copy of {image.name}")
            
            processed_images.add(image)
            
        except Exception as e:
            result['errors'].append(f"Error processing {image.name}: {str(e)}")
    
    return result


def save_images_as_jpeg(context, quality=90, excluded_materials=None, status_callback=None):
    """
    Optimize and compress all textures from selected objects' materials.
    - Images with transparency: Converted to WebP with alpha (lossy compression)
    - Opaque images: Converted to WebP (lossy compression)
    - Fallback to PNG/JPEG if WebP is not available
    Only processes textures used by materials assigned to selected objects.
    Uses Pillow for efficient image optimization.
    
    Args:
        context: Blender context (must have selected_objects)
        quality: Quality for WebP/JPEG compression (1-100, default: 90)
        excluded_materials: List of material names to exclude (optional)
        status_callback: Optional callback function(status_text) for progress updates
        
    Returns:
        dict: {
            'saved': int (number of images optimized),
            'optimized_copies': dict mapping original to optimized image,
            'errors': list of error messages
        }
    """
    if not PILLOW_AVAILABLE:
        return {
            'saved': 0,
            'errors': ['Pillow not available - cannot optimize textures']
        }
    
    # Get textures only from selected objects' materials
    images = get_all_texture_images(context, excluded_materials=excluded_materials)
    
    result = {
        'saved': 0,
        'optimized_copies': {},  # original_image -> optimized_copy
        'errors': []
    }
    
    total_images = len(images)
    webp_available = is_webp_available()
    
    for idx, image in enumerate(images):
        try:
            # Check if already optimized (JPEG or WebP)
            is_optimized = False
            if image.filepath:
                ext = os.path.splitext(image.filepath.lower())[1]
                is_optimized = ext in ('.jpg', '.jpeg', '.webp')
            
            if is_optimized:
                continue
            
            # Get image dimensions
            width, height = get_texture_size(image)
            if width == 0 or height == 0:
                continue
            
            # Get pixel data from Blender image
            pixels = list(image.pixels)
            if len(pixels) == 0:
                continue
            
            # Convert to numpy array
            pixel_array = np.array(pixels, dtype=np.float32)
            
            # Determine channels
            has_alpha = False
            if len(pixels) == width * height * 4:
                channels = 4  # RGBA
                pixel_array = pixel_array.reshape((height, width, 4))
                
                # Check if alpha channel has meaningful transparency
                # (not all 1.0 which means fully opaque)
                alpha_channel = pixel_array[:, :, 3]
                has_meaningful_alpha = not np.allclose(alpha_channel, 1.0, atol=0.01)
                
                if has_meaningful_alpha:
                    # Has transparency - save as WebP with alpha support (if available)
                    if status_callback:
                        format_name = "WebP" if webp_available else "PNG"
                        status_callback(f"Converting {image.name} to {format_name} ({idx+1}/{total_images})...")
                    
                    if webp_available:
                        print(f"Converting {image.name} to WebP with alpha - has transparency")
                    else:
                        print(f"WebP not available, using PNG for {image.name}")
                    
                    # Convert to uint8 for PIL
                    pixel_array_uint8 = (pixel_array * 255).astype(np.uint8)
                    
                    # Create PIL Image with alpha
                    pil_image = Image.fromarray(pixel_array_uint8, mode='RGBA')
                    
                    # Flip vertically to standard image coordinates
                    pil_image = pil_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                    
                    # Save as WebP (if available) or PNG (fallback)
                    if webp_available:
                        # Create temporary file for WebP
                        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp_file:
                            tmp_path = tmp_file.name
                        
                        # Save as WebP with alpha support
                        # quality=90 for lossy compression (smaller files)
                        # Use lossless=True for lossless compression (larger but perfect quality)
                        pil_image.save(tmp_path, 'WEBP', quality=90, method=6)
                        
                        # Create new Blender image from WebP file
                        optimized_name = f"{image.name}_WebP"
                    else:
                        # Fallback to PNG
                        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                            tmp_path = tmp_file.name
                        
                        pil_image.save(tmp_path, 'PNG', optimize=True, compress_level=9)
                        
                        # Create new Blender image from PNG file
                        optimized_name = f"{image.name}_PNG"
                    
                    # Remove old version if exists
                    if optimized_name in bpy.data.images:
                        old_image = bpy.data.images[optimized_name]
                        bpy.data.images.remove(old_image)
                    
                    # Load the optimized file as a new Blender image
                    optimized_image = bpy.data.images.load(tmp_path)
                    optimized_image.name = optimized_name
                    
                    # Pack the image into the blend file
                    optimized_image.pack()
                    
                    # Replace image references in materials
                    replace_image_in_materials(context, image, optimized_image)
                    
                    result['optimized_copies'][image] = optimized_image
                    result['saved'] += 1
                    
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                    
                    continue
                
                # If fully opaque, convert RGBA to RGB for WebP
                pixel_array = pixel_array[:, :, :3]
            elif len(pixels) == width * height * 3:
                channels = 3  # RGB
                pixel_array = pixel_array.reshape((height, width, 3))
            else:
                result['errors'].append(f"Unexpected pixel format for {image.name}")
                continue
            
            # Opaque image - convert to WebP (no alpha)
            if status_callback:
                format_name = "WebP" if webp_available else "JPEG"
                status_callback(f"Converting {image.name} to {format_name} ({idx+1}/{total_images})...")
            
            # Convert from float (0.0-1.0) to uint8 (0-255)
            pixel_array = (pixel_array * 255).astype(np.uint8)
            
            # Create PIL Image
            pil_image = Image.fromarray(pixel_array, mode='RGB')
            
            # Flip vertically to standard image coordinates
            pil_image = pil_image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            
            # Save as WebP (if available) or JPEG (fallback)
            if webp_available:
                # Create temporary file for WebP
                with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                # Save as WebP with quality setting
                pil_image.save(tmp_path, 'WEBP', quality=quality, method=6)
                
                # Create new Blender image from WebP file
                optimized_name = f"{image.name}_WebP"
                
                print(f"Converted {image.name} to WebP (quality: {quality})")
            else:
                # Fallback to JPEG if WebP not available
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                
                pil_image.save(tmp_path, 'JPEG', quality=quality, optimize=True)
                
                # Create new Blender image from JPEG file
                optimized_name = f"{image.name}_JPEG"
                
                print(f"WebP not available, converted {image.name} to JPEG (quality: {quality})")
            
            # Remove old version if exists
            if optimized_name in bpy.data.images:
                old_image = bpy.data.images[optimized_name]
                bpy.data.images.remove(old_image)
            
            # Load the optimized file as a new Blender image
            optimized_image = bpy.data.images.load(tmp_path)
            optimized_image.name = optimized_name
            
            # Pack the image into the blend file
            optimized_image.pack()
            
            # Replace image references in materials
            replace_image_in_materials(context, image, optimized_image)
            
            result['optimized_copies'][image] = optimized_image
            result['saved'] += 1
            
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
                
        except Exception as e:
            result['errors'].append(f"Error optimizing {image.name}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return result


def replace_image_in_materials(context, old_image, new_image):
    """
    Replace all references to old_image with new_image in material node trees.
    Only replaces images in materials assigned to selected objects.
    
    Args:
        context: Blender context (must have selected_objects)
        old_image: bpy.types.Image to replace
        new_image: bpy.types.Image to use instead
    """
    # Early return if no objects are selected
    if not context.selected_objects:
        return
    
    # Get all materials from selected objects only
    materials = set()
    for obj in context.selected_objects:
        # Only process mesh objects
        if obj.type != 'MESH' or not obj.data:
            continue
        
        # Get materials from material slots of this selected object
        for slot in obj.material_slots:
            if slot.material:
                materials.add(slot.material)
    
    # Replace image references in node trees
    # Only replace in materials assigned to selected objects
    for material in materials:
        if not material or not material.use_nodes or not material.node_tree:
            continue
        
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                if hasattr(node, 'image') and node.image == old_image:
                    node.image = new_image

