# Blender glTF 2.0 Import/Export Guide

**Source:** [Blender 4.5 LTS Manual - glTF 2.0](https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html)  
**Last Updated:** 2025-11-07  
**License:** CC-BY-SA 4.0 International License

---

## Table of Contents

1. [Overview](#overview)
2. [Enabling Add-on](#enabling-add-on)
3. [Usage](#usage)
4. [Meshes](#meshes)
5. [Materials](#materials)
6. [Extensions](#extensions)
7. [Custom Properties](#custom-properties)
8. [Animations](#animations)
9. [File Format Variations](#file-format-variations)
10. [Import Properties](#import-properties)
11. [Export Properties](#export-properties)
12. [Collection Exporters](#collection-exporters)
13. [Contributing](#contributing)

---

## Overview

The glTF 2.0 (GL Transmission Format) is an open standard for 3D content delivery. It is designed for efficient transmission and loading of 3D models and scenes. Blender's glTF 2.0 add-on provides comprehensive import and export capabilities for this format.

**Key Features:**
- Full material support including PBR workflows
- Animation support (skeletal, shape keys, object transforms)
- Mesh compression using Google Draco
- GPU instancing support
- Custom properties and extensions
- Multiple file format variations (.glb, .gltf)

---

## Enabling Add-on

To enable the glTF 2.0 add-on in Blender:

1. Open Blender Preferences (`Edit > Preferences`)
2. Navigate to the `Add-ons` section
3. Search for "glTF"
4. Enable the checkbox next to "Import-Export: glTF 2.0 format"

---

## Usage

### Importing glTF Files

**Menu Location:** `File > Import > glTF 2.0 (.glb/.gltf)`

Import glTF files into your current Blender scene. The importer supports:
- Binary glTF (.glb)
- Separate glTF (.gltf + .bin + textures)
- Embedded glTF (.gltf with embedded resources)

### Exporting to glTF

**Menu Location:** `File > Export > glTF 2.0 (.glb/.gltf)`

Export your Blender scene or selected objects to glTF format. The exporter provides extensive options for customizing the output.

---

## Meshes

### Mesh Support

The glTF format supports:
- Triangle and quad meshes (quads are automatically triangulated on export)
- Vertex colors
- UV maps (multiple UV layers supported)
- Normals (automatically calculated if not present)
- Tangents (for normal mapping)

### GPU Instances

The glTF format supports GPU instancing for efficient rendering of repeated objects. When multiple objects share the same mesh data, they can be exported as instances, reducing file size and improving performance.

**Export Behavior:**
- Objects with the same mesh data are automatically detected
- Instances maintain their individual transforms
- Material assignments are preserved per instance

---

## Materials

### Imported Materials

When importing glTF files, materials are converted to Blender's node-based material system. The importer creates a complete node tree that matches the glTF material definition.

**Supported Material Features:**
- PBR Metallic-Roughness workflow
- Base color with texture support
- Metallic and roughness mapping
- Normal mapping
- Emission
- Alpha modes (opaque, blend, mask)
- Double-sided materials
- Extensions (Clearcoat, Sheen, Specular, Transmission, etc.)

### Exported Materials

Blender materials are exported using the glTF PBR Metallic-Roughness model. The exporter analyzes your node tree to determine the appropriate glTF material properties.

#### Base Color

**Node Setup:**
- Connect an Image Texture or color output to the `Base Color` input of the Principled BSDF
- RGB textures are exported as-is
- Vertex colors can be multiplied with base color

**glTF Property:** `baseColorFactor` and `baseColorTexture`

#### Metallic and Roughness

**Node Setup:**
- Connect values or textures to `Metallic` and `Roughness` inputs
- Textures are packed into a single image (Blue = Metallic, Green = Roughness)
- Separate textures are automatically combined during export

**glTF Property:** `metallicFactor`, `roughnessFactor`, and `metallicRoughnessTexture`

#### Baked Ambient Occlusion

**Node Setup:**
- Use a Mix node to combine base color with AO texture
- Set Mix mode to Multiply
- AO is packed into the Red channel of the metallic-roughness texture

**glTF Property:** `occlusionTexture` (packed in metallicRoughness texture)

#### Normal Map

**Node Setup:**
- Connect an Image Texture (set to Non-Color) to a Normal Map node
- Connect Normal Map node output to the `Normal` input of Principled BSDF
- Tangent space normal maps are supported

**glTF Property:** `normalTexture`

**Important:** Use tangent-space normal maps. Object-space normal maps are not supported by glTF.

#### Emissive

**Node Setup:**
- Connect color or texture to the `Emission Color` input
- Set `Emission Strength` to control intensity
- Emission is additive to the base color

**glTF Property:** `emissiveFactor` and `emissiveTexture`

#### Clearcoat

Adds a reflective coating layer on top of the base material, useful for car paint, varnished wood, etc.

**Node Setup:**
- Enable Clearcoat on Principled BSDF
- Set `Clearcoat` value (0-1)
- Set `Clearcoat Roughness`
- Optional: Add clearcoat normal map

**glTF Extension:** `KHR_materials_clearcoat`

#### Sheen

Adds a soft fabric-like appearance, useful for cloth, velvet, etc.

**Node Setup:**
- Enable Sheen on Principled BSDF
- Set `Sheen Weight` value
- Set `Sheen Tint` for color
- Optional: Adjust `Sheen Roughness`

**glTF Extension:** `KHR_materials_sheen`

#### Specular

Provides additional control over specular reflections beyond the metallic-roughness model.

**Node Setup:**
- Adjust `Specular IOR Level` on Principled BSDF
- Set `Specular Tint` for colored reflections

**glTF Extension:** `KHR_materials_specular`

#### Anisotropy

Creates directional reflections, useful for brushed metal, hair, etc.

**Node Setup:**
- Enable Anisotropic on Principled BSDF
- Set `Anisotropic` value
- Set `Anisotropic Rotation` for direction

**glTF Extension:** `KHR_materials_anisotropy`

#### Transmission

Enables light transmission through the material (glass, water, etc.).

**Node Setup:**
- Set `Transmission Weight` on Principled BSDF
- Adjust `IOR` (Index of Refraction)
- Optional: Add transmission texture

**glTF Extension:** `KHR_materials_transmission`

#### IOR

Index of Refraction controls how light bends when passing through transparent materials.

**Node Setup:**
- Set `IOR` value on Principled BSDF
- Common values: Glass (1.5), Water (1.33), Diamond (2.42)

**glTF Extension:** `KHR_materials_ior`

#### Volume

Enables volumetric effects like fog, smoke, or subsurface scattering approximation.

**Node Setup:**
- Set `Transmission Weight` > 0
- Enable volume properties
- Set `Volume Absorption Color` and `Density`

**glTF Extension:** `KHR_materials_volume`

#### glTF Variants

Material variants allow a single model to have multiple material configurations that can be switched at runtime.

**Use Cases:**
- Different color options for products
- Day/night material variations
- Damage states for game assets

##### glTF Variants Switching

To view different material variants in Blender after importing:

1. Select the object
2. Open the Object Properties panel
3. Find the "glTF Material Variants" section
4. Select the desired variant from the dropdown

##### glTF Variants Creation

To create material variants for export:

1. Select the object
2. Open the Object Properties panel
3. Add variants using the "glTF Material Variants" interface
4. Assign different materials to each variant
5. Export with variants enabled

##### Advanced glTF Variant Checks

The add-on performs validation checks to ensure:
- Variant names are unique
- Material slots are properly assigned
- All variants have valid materials

#### Double-Sided / Backface Culling

Controls whether both sides of faces are rendered.

**Settings:**
- Enable "Backface Culling" in Material Properties to make single-sided
- Disable for double-sided rendering
- glTF property: `doubleSided`

#### Alpha Modes

glTF supports three alpha/transparency modes:

1. **Opaque:** No transparency (default)
   - Set material blend mode to Opaque
   - Alpha channel is ignored

2. **Blend:** Alpha blending
   - Set material blend mode to Alpha Blend
   - Enables gradual transparency
   - Order-dependent rendering required

3. **Mask:** Alpha cutoff
   - Set material blend mode to Alpha Clip
   - Binary transparency (visible or invisible)
   - Set alpha threshold value
   - No order-dependent rendering needed

#### UV Mapping

glTF supports multiple UV layers per mesh.

**Export Behavior:**
- All UV maps are exported by default
- UV maps are named UV, UV2, UV3, etc. in glTF
- Textures reference specific UV sets via `texCoord` attribute

**Best Practices:**
- Use UV coordinates in range 0-1 for best compatibility
- Use "UV Map" node to specify which UV layer a texture uses

#### Factors

Material factors are scalar multipliers applied to material properties.

**Common Factors:**
- `baseColorFactor`: RGBA multiplier for base color
- `metallicFactor`: Multiplier for metallic value
- `roughnessFactor`: Multiplier for roughness value
- `emissiveFactor`: RGB multiplier for emission

**Usage:** Factors are multiplied with texture values, allowing runtime material adjustments.

#### Example

**Complete PBR Material Node Setup:**

```
Image Texture (Base Color) → Principled BSDF (Base Color)
Image Texture (Normal) → Normal Map → Principled BSDF (Normal)
Image Texture (MetallicRoughness) → Separate RGB →
    R (unused or AO) → Mix with Base Color
    G (Roughness) → Principled BSDF (Roughness)
    B (Metallic) → Principled BSDF (Metallic)
Principled BSDF → Material Output
```

#### UDIM

UDIM texture tiles allow multiple texture tiles for a single object, useful for high-resolution texturing.

**Support Status:**
- UDIM is supported for import
- Export support may be limited
- Each tile is handled as a separate texture in glTF

---

### Exporting a Shadeless (Unlit) Material

To export a material without lighting calculations:

**Node Setup:**
1. Delete the Principled BSDF node
2. Add an Emission shader
3. Connect your color/texture to Emission
4. Connect Emission to Material Output

**glTF Extension:** `KHR_materials_unlit`

**Result:** Material displays colors as-is without lighting, useful for UI elements, stylized art, or pre-lit textures.

---

## Extensions

The Blender glTF add-on supports numerous official and vendor extensions.

### Official Extensions (Supported)

- `KHR_materials_clearcoat` - Clearcoat layer
- `KHR_materials_sheen` - Fabric/sheen appearance
- `KHR_materials_specular` - Enhanced specular control
- `KHR_materials_anisotropy` - Anisotropic reflections
- `KHR_materials_transmission` - Light transmission/glass
- `KHR_materials_volume` - Volumetric effects
- `KHR_materials_ior` - Index of refraction
- `KHR_materials_unlit` - Unlit/shadeless materials
- `KHR_materials_variants` - Material variants
- `KHR_lights_punctual` - Point, spot, and directional lights
- `KHR_texture_transform` - UV transformation
- `KHR_draco_mesh_compression` - Mesh compression
- `KHR_mesh_quantization` - Vertex attribute quantization

### Third-party glTF Extensions

Custom extensions can be imported and exported through Blender's custom properties system. Extension data is preserved in the `extras` field.

**Creating Custom Extensions:**
1. Add custom properties to objects/materials
2. Prefix property names with extension identifier
3. Export with custom properties enabled

---

## Custom Properties

Blender's custom properties are exported to the glTF `extras` field.

**Supported Objects:**
- Objects
- Materials
- Meshes
- Cameras
- Lights
- Collections
- Scene

**Export Settings:**
- Enable "Custom Properties" in export options
- Properties are converted to JSON format
- Nested properties are supported

**Usage:**
Custom properties allow storing arbitrary metadata that can be read by glTF viewers or game engines.

---

## Animations

### Import

The importer handles glTF animations and converts them to Blender's animation system.

**Import Behavior:**
- Animations are imported as Actions
- Actions are assigned to objects/armatures
- NLA tracks can be created automatically
- Shape key animations are supported
- Skeletal animations are applied to armatures

**Animation Mapping:**
- glTF animations → Blender Actions
- Animation channels → F-Curves
- Samplers → Interpolation modes (LINEAR, STEP, CUBICSPLINE)

### Export

The exporter provides multiple animation export modes to suit different workflows.

#### Actions (default)

**Behavior:**
- Each Action in Blender is exported as a separate glTF animation
- Only actions assigned to objects are exported
- Actions are baked to keyframes

**Use Case:** Best for traditional animation workflows with distinct actions per object.

#### Active Actions merged

**Behavior:**
- Only the currently active action per object is exported
- All active actions are merged into a single glTF animation
- Timeline range determines export range

**Use Case:** Exporting a single unified animation from multiple animated objects.

#### NLA Tracks

**Behavior:**
- Each NLA track is exported as a separate glTF animation
- Track names become animation names
- Strips are baked in sequence
- Supports muting and soloing tracks

**Use Case:** Complex animation systems with layered or sequenced animations.

**Options:**
- Export muted tracks: Include tracks that are muted in the NLA editor
- Merge tracks with same name: Combine NLA tracks across objects with matching names

#### Scene

**Behavior:**
- Exports the entire scene timeline as a single animation
- All animated objects are included
- Respects scene frame range

**Use Case:** Cinematic sequences or complete scene playback.

---

## File Format Variations

glTF 2.0 offers three file format options:

### glTF Binary (.glb)

**Structure:** Single binary file containing all resources

**Contents:**
- JSON scene description
- Binary buffer data (geometry, animations)
- Embedded textures

**Advantages:**
- Single file - easy distribution
- Smaller file size due to binary encoding
- Faster loading (no separate HTTP requests)

**Use Case:** Web applications, games, distribution platforms

### glTF Separate (.gltf + .bin + textures)

**Structure:** Multiple files

**Contents:**
- `.gltf` - JSON scene description
- `.bin` - Binary buffer data
- Separate texture files (PNG, JPEG)

**Advantages:**
- Human-readable JSON
- Easy to edit scene description
- Textures can be optimized separately
- Better version control

**Use Case:** Development, content pipelines, version control

### glTF Embedded (.gltf)

**Structure:** Single JSON file with embedded resources

**Contents:**
- JSON scene description
- Base64-encoded binary data
- Base64-encoded textures

**Advantages:**
- Single file
- Human-readable JSON
- No binary file dependencies

**Disadvantages:**
- Larger file size (Base64 overhead ~33%)
- Slower parsing
- Not recommended for production

**Use Case:** Testing, debugging, educational purposes

---

## Import Properties

### Texture

#### Texture Folder

Specify a custom folder to search for external textures when they're not found in the default location.

### Bones & Skin

#### Bone Direction

Controls the orientation of imported bones:

- **Temperance Bone Dir:** Balanced between visual and technical requirements
- **Blender:** Uses Blender's default bone orientation
- **Blenderific:** Alternative orientation for compatibility

#### Guess Original Bind Pose

Attempts to reconstruct the original bind pose for rigged meshes when not explicitly defined in the glTF file.

### Pipeline

#### Import WebP Texture

Enable import of WebP format textures. Requires WebP support in Blender.

#### Import Variants

Import material variants as multiple material slots. Allows switching between variants in Blender.

---

## Export Properties

### Include

#### Limit to Selected Objects

Export only the currently selected objects instead of the entire scene.

#### Visible Objects

Export only objects that are visible in the viewport (not hidden).

#### Renderable Objects

Export only objects that are enabled for rendering.

#### Active Collection

Export only objects in the active collection.

#### Active Scene

Export only objects in the active scene (useful in multi-scene files).

#### Custom Properties

Include custom properties in the export (stored in `extras` field).

#### Cameras

Export camera objects with their properties.

#### Punctual Lights

Export point, spot, and directional lights using the `KHR_lights_punctual` extension.

---

### Transform

#### Y Up

Convert Blender's Z-up coordinate system to Y-up (glTF standard). Recommended to keep enabled for maximum compatibility.

---

### Data - Scene Graph

#### GPU Instances

Export instances of the same mesh as GPU instances, reducing file size and improving performance.

#### Flatten Object Hierarchy

Remove parent-child relationships, placing all objects at the root level. Useful for engines that don't support hierarchies.

#### Full Collection Hierarchy

Export the complete collection hierarchy as nodes in the glTF scene graph.

#### Export Extras

Export additional metadata from custom properties.

---

### Data - Mesh

#### Apply Modifiers

Apply mesh modifiers before export. Recommended for final exports.

#### UVs

Export UV coordinates. Required for textured materials.

#### Normals

Export vertex normals. If disabled, normals are calculated by the viewer.

#### Tangents

Export tangent vectors. Required for normal mapping.

#### Attributes - Loose Edges

Export edges that are not part of faces.

#### Attributes - Loose Points

Export vertices that are not connected to any edge or face.

#### Compress - Draco Mesh Compression

Enable Google Draco compression to significantly reduce file size. See [Data - Compression](#data---compression) section.

---

### Data - Mesh - Vertex Color

Controls how vertex colors are exported.

#### Use Vertex Color

**Options:**

- **Material:** Export vertex color when used in material node tree as Base Color multiplier (default, most accurate)
- **Active:** Export active vertex colors, even if not used in material
- **Name:** Export vertex color with specific name
- **None:** Do not export vertex color

#### Export all vertex colors

Export all vertex color layers (COLOR_0, COLOR_1, COLOR_2, etc.).

#### Export active vertex color when no material

Export the active vertex color for objects without materials assigned.

---

### Data - Material

#### Materials

**Export Modes:**

- **Export:** Full materials with all textures and shaders (default)
- **Placeholder:** Material placeholder only, no textures/shaders
- **Viewport:** Viewport materials only (Base Color, Roughness, Metallic)
- **No Export:** Skip materials entirely, merge primitives

#### Images

**Output Format Options:**

- **PNG:** Lossless, larger file size (recommended)
- **JPEG:** Lossy, smaller file size (web-friendly)
- **WebP:** Modern format, good compression
- **None:** Export materials without textures

#### Image Quality

Quality setting for JPEG/WebP export (0-100). Higher values = better quality but larger files.

#### Create WebP

Generate WebP versions of all textures in addition to original formats.

#### WebP fallback

Create PNG fallback textures for all WebP textures for compatibility.

#### Unused images

Export images not referenced by any material.

#### Unused textures

Export texture info (sampler, image, texcoord) not used in materials.

---

### Data - Shape Keys

#### Export shape keys

Export shape keys (morph targets) for facial animation, blend shapes, etc.

#### Shape Key Normals

Export custom vertex normals with shape keys. Required for correct deformation lighting.

#### Shape Key Tangents

Export vertex tangents with shape keys. Required for normal-mapped morph targets.

---

### Data - Shape Keys - Optimize

#### Use Sparse Accessor if better

Use sparse accessors when they reduce file size (shape keys with few modified vertices).

#### Omitting Sparse Accessor if data is empty

Skip sparse accessors for empty data. Disabled by default due to viewer compatibility issues.

---

### Data - Armature

#### Use Rest Position Armature

Export armatures using rest position as joint rest pose. When disabled, current frame pose is used.

#### Export Deformation Bones only

Export only bones that affect mesh deformation. Non-deforming bones are excluded. Animation is baked.

#### Remove Armature Object

Remove armature objects when possible (all bones have single root). Flattens bone hierarchy into parent transforms.

#### Flatten Bone Hierarchy

Flatten the bone hierarchy. Useful when bones have non-decomposable TRS matrices.

---

### Data - Skinning

#### Export skinning data

Export mesh skinning (rigging) information.

#### Bone influences

**Number of joint influences per vertex:**

- **4:** Standard (maximum compatibility)
- **8:** Extended support (not all viewers support)
- **All:** Include all influences (may cause issues)

**Note:** Models may appear incorrectly with values other than 4 or 8.

#### Include All Bone Influences

Export all joint vertex influences regardless of count. May cause compatibility issues.

---

### Data - Lighting

#### Lighting Mode

**Options:**

- **Standard:** Physically-based glTF lighting units (cd, lx, nt) - Recommended
- **Unitless:** Non-physical lighting (legacy compatibility)
- **Raw (Deprecated):** Blender values without conversion

---

### Data - Compression

Enable Google Draco mesh compression to reduce file size.

#### Compress meshes using Google Draco

Enable Draco compression. Requires decoder support in viewer.

#### Compression Level

**Range:** 0-10

Higher values = better compression but slower encoding/decoding.

#### Quantization Position

**Bits per vertex position coordinate**

Higher values = better compression, lower precision.

#### Normal

**Bits per normal component**

Higher values = better compression, lower precision.

#### Texture Coordinates

**Bits per UV coordinate**

Higher values = better compression, lower precision.

#### Color

**Bits per vertex color component**

Higher values = better compression, lower precision.

#### Generic

**Bits for generic attributes**

Higher values = better compression, lower precision.

---

### Animation

#### Animation mode

Select which animation export mode to use. See [Animations](#animations) section for details.

**Options:**
- Actions
- Active Actions merged
- NLA Tracks
- Scene

---

### Animation - Bake & Merge

#### Bake All Objects Animations

Bake animations for all objects, including constrained objects without keyframes.

#### Merge Animation

**Merge Options:**

- **By Action:** Merge animations with same action
- **By NLA Track Name:** Merge animations with same NLA track name
- **No Merge:** Export all animations separately

---

### Animation - Rest & Ranges

#### Use Current Frame as Object Rest Transformations

Use current frame as rest transformation. When disabled, frame 0 is used.

#### Limit to Playback Range

Restrict exported animation to the scene's playback range.

#### Set all glTF Animation starting at 0

Offset all animations to start at time 0. Useful for looping animations.

#### Negative Frames

**Options when animation contains negative frames:**

- **Slide:** Shift animation to start at 0
- **Crop:** Remove negative frames

---

### Animation - Armature

#### Export all Armature Actions

Export all actions bound to a single armature.

**Warning:** Does not support multiple armatures.

#### Reset pose bones between actions

Reset bone poses between each exported action. Required when bones aren't keyed in all animations.

---

### Animation - Shape Keys

#### Shape Keys Animations

Export shape key animations. Requires shape keys to be exported.

#### Reset Shape Keys between actions

Reset shape keys between actions. Required when shape keys aren't keyed in all animations.

---

### Animation - Sampling

#### Apply sampling to all animations

Sample all animations. Not sampling can lead to incorrect animation export.

#### Sampling Rate

**Frames between samples**

How often to evaluate animated values. Lower = more keyframes, higher accuracy.

#### Sampling Interpolation Fallback

**Interpolation for non-keyed properties:**

- **LINEAR:** Smooth interpolation
- **STEP/CONSTANT:** Hold previous value

---

### Animation - Optimize

#### Optimize Animation Size

Remove duplicate keyframes to reduce file size. Enabled by default.

#### Force keeping channel for armature / bones

Keep minimal animation even when all keyframes are identical for rigs.

#### Force keeping channel for objects

Keep minimal animation even when all keyframes are identical for object transforms.

#### Disable viewport for other objects

Disable viewport display for non-exported objects during export for better performance.

---

### Animation - Filter

Restrict exported actions to those matching a filter pattern.

**Usage:** Enter a text filter to include only actions with matching names.

---

## Collection Exporters

The glTF exporter can be used as a collection exporter for batch export workflows.

### Collection Export Features

**Capabilities:**
- Export collections as separate glTF files
- Export at collection center (center of mass of root objects)
- Collection custom properties exported as scene glTF extras

**Limitations:**
- Include options are not available (objects in collection are always included)

**Use Cases:**
- Asset libraries
- Batch export workflows
- Modular scene composition

---

## Contributing

### Development

The glTF add-on is developed in the **glTF-Blender-IO** repository.

**Get Involved:**
- Report bugs
- Submit feature requests
- Contribute code
- Improve documentation

**Repository:** [glTF-Blender-IO on GitHub](https://github.com/KhronosGroup/glTF-Blender-IO)

### glTF Format Development

The glTF 2.0 format itself is developed by the Khronos Group.

**Repository:** [Khronos Group glTF on GitHub](https://github.com/KhronosGroup/glTF)

**Participation:**
- Format specification discussions
- Extension proposals
- Implementation feedback
- Conformance testing

---

## Additional Resources

### Official Documentation

- [glTF 2.0 Specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
- [Blender Manual](https://docs.blender.org/manual/)
- [glTF Sample Models](https://github.com/KhronosGroup/glTF-Sample-Models)

### Community

- [Blender Artists Forum](https://blenderartists.org/)
- [glTF Discussion Forum](https://github.com/KhronosGroup/glTF/discussions)
- [Blender Stack Exchange](https://blender.stackexchange.com/)

---

## Image References

*Note: Images from the original documentation provide visual examples of:*

- Material node setup examples
- Export dialog screenshots
- Animation export mode comparisons
- Compression settings impact
- Material variant interface
- UV mapping visualization

*For full visual reference, please visit the [original documentation](https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html).*

---

## License

This documentation is derived from the official Blender manual and is licensed under **CC-BY-SA 4.0 International License**.

**Original Source:** Blender Foundation  
**Documentation URL:** https://docs.blender.org/manual/en/latest/addons/import_export/scene_gltf2.html  
**Last Updated:** November 7, 2025

---

## Glossary

**Terms used in this guide:**

- **glTF:** GL Transmission Format - 3D asset format
- **PBR:** Physically Based Rendering
- **BSDF:** Bidirectional Scattering Distribution Function
- **UV:** 2D texture coordinates mapped to 3D geometry
- **NLA:** Non-Linear Animation - Blender's animation layering system
- **IOR:** Index of Refraction
- **AO:** Ambient Occlusion
- **Draco:** Google's mesh compression algorithm
- **UDIM:** U-Dimension - tiled texture system
- **TRS:** Translation, Rotation, Scale transformation matrix

---

*End of Document*

