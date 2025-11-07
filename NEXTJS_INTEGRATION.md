# Blender Addon → Next.js Integration

## Server Details

**Port:** `8080`  
**Host:** `localhost`

## API Endpoints

### 1. Health Check

```
GET http://localhost:8080/ping
```

**Returns:** `pong` (text/plain)

**Example:**

```javascript
const response = await fetch("http://localhost:8080/ping");
const text = await response.text(); // "pong"
```

---

### 2. Get Latest Model

```
GET http://localhost:8080/latest-model
```

**Returns:** Binary GLB file (Content-Type: `model/gltf-binary`)

**Status Codes:**

-   `200` - Model available
-   `404` - No model available

**Example:**

```javascript
const response = await fetch("http://localhost:8080/latest-model");
if (response.ok) {
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    // Load with Three.js GLTFLoader
    loader.load(url, (gltf) => {
        scene.add(gltf.scene);
    });
}
```

---

### 3. Get Latest Model Metadata

```
GET http://localhost:8080/latest-model-info
```

**Returns:** JSON metadata object (Content-Type: `application/json`)

**Status Codes:**

-   `200` - Metadata available
-   `404` - No metadata available

**Metadata Structure:**

```typescript
{
  filename: string;                    // e.g., "model.glb"
  scene_name: string;                  // Blender scene name
  timestamp: string;                   // ISO 8601 timestamp
  size: number;                        // File size in bytes
  size_mb: string;                     // File size in MB (formatted)
  export_settings: {
    compression: string;                // "NONE" | "LOW" | "MEDIUM" | "HIGH"
    draco_enabled: boolean;
    draco_level: number | null;         // 1-10, null if disabled
    decimation_enabled: boolean;
    decimation_ratio: number | null;   // 0.0-1.0, null if disabled
    decimation_method: string | null;   // "BMESH" | null
    mesh_repair_enabled: boolean;
  };
  object_count: number;                 // Number of mesh objects
  materials?: {                         // Optional, if material analyzer available
    total: number;                      // Total materials analyzed
    ready: number;                      // Number of GLB-ready materials
    unsupported: string[];              // Array of unsupported material names
    analysis: {                         // Detailed analysis per material
      [materialName: string]: {
        is_ready: boolean;
        issues: string[];               // List of blocking issues
        warnings: string[];             // List of non-blocking warnings
      };
    };
  };
}
```

**Example:**

```javascript
const response = await fetch("http://localhost:8080/latest-model-info");
if (response.ok) {
    const metadata = await response.json();
    console.log(`Model: ${metadata.filename}`);
    console.log(`Size: ${metadata.size_mb} MB`);
    console.log(`Objects: ${metadata.object_count}`);

    if (metadata.materials) {
        console.log(
            `Materials: ${metadata.materials.ready}/${metadata.materials.total} ready`
        );
        if (metadata.materials.unsupported.length > 0) {
            console.warn(
                `Unsupported materials: ${metadata.materials.unsupported.join(
                    ", "
                )}`
            );
        }
    }
}
```

---

### 4. Upload Model (Internal - used by Blender)

```
POST http://localhost:8080/upload-model
```

**Headers:**

-   `Content-Type: application/octet-stream`
-   `X-Model-Metadata: <JSON string>` (optional)

**Body:** Binary GLB data

**Returns:** JSON response

```typescript
{
  status: "success" | "error";
  size: number;              // File size in bytes
  size_mb: string;           // File size in MB (formatted)
  message?: string;          // Error message if status is "error"
}
```

**Status Codes:**

-   `200` - Upload successful
-   `500` - Server error

---

## Material Analysis & Custom Properties

### GLB File Extras

Unsupported materials are marked with custom properties in the GLB file's `extras` field. These can be accessed after loading the GLB:

```javascript
loader.load(url, (gltf) => {
    gltf.scene.traverse((node) => {
        if (node.material) {
            const extras = node.material.userData.gltfExtensions?.extras || {};

            if (extras.framo_unsupported) {
                console.warn(`Material "${node.material.name}" is unsupported`);

                // Parse issues if available
                if (extras.framo_issues) {
                    const issues = JSON.parse(extras.framo_issues);
                    console.log("Issues:", issues);
                }

                // Parse warnings if available
                if (extras.framo_warnings) {
                    const warnings = JSON.parse(extras.framo_warnings);
                    console.log("Warnings:", warnings);
                }
            }
        }
    });
});
```

**Custom Properties:**

-   `framo_unsupported` (boolean): `true` if material is not GLB-ready
-   `framo_issues` (string): JSON array of blocking issues
-   `framo_warnings` (string): JSON array of warnings (optional)

### Material Issues Format

Issues are returned as an array of strings. Headers end with `:` and list items start with `  •`:

```json
[
    "Unsupported shader nodes:",
    "  • Group Node (GROUP)",
    "  • Diffuse BSDF (BSDF_DIFFUSE)",
    "  Use Principled BSDF or Emission shader instead",
    "Contains procedural textures:",
    "  • Noise Texture (TEX_NOISE)"
]
```

---

## Model Features

The GLB files exported from Blender include:

-   **Draco Compression** (optional, configurable levels 1-10)
-   **Mesh Decimation** (optional, face reduction ratio 0.0-1.0)
-   **Mesh Repair** (optional, cleanup operations)
-   **Material Analysis** (automatic detection of unsupported materials)

---

## Usage Pattern

The addon polls every 2 seconds in the test viewer. You can:

1. Poll the `/latest-model` endpoint periodically
2. Poll `/latest-model-info` to check for updates without downloading the model
3. Set up Server-Sent Events (addon doesn't support this yet)
4. Use WebSocket (addon doesn't support this yet)

**Recommended Pattern:**

```javascript
// Poll metadata first to check if model changed
let lastTimestamp = null;

async function checkForUpdates() {
    try {
        const response = await fetch("http://localhost:8080/latest-model-info");
        if (response.ok) {
            const metadata = await response.json();

            // Only reload if timestamp changed
            if (metadata.timestamp !== lastTimestamp) {
                lastTimestamp = metadata.timestamp;
                await loadLatestModel();

                // Handle material warnings
                if (metadata.materials?.unsupported.length > 0) {
                    showMaterialWarnings(metadata.materials);
                }
            }
        }
    } catch (error) {
        console.error("Update check failed:", error);
    }
}

async function loadLatestModel() {
    const response = await fetch("http://localhost:8080/latest-model");
    if (response.ok) {
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        // Load with your GLB loader
    }
}

// Poll every 2 seconds
setInterval(checkForUpdates, 2000);
```

---

## CORS

All endpoints have `Access-Control-Allow-Origin: *` enabled.

**Allowed Headers:**

-   `Content-Type`
-   `X-Model-Metadata`

**Allowed Methods:**

-   `GET`
-   `POST`
-   `OPTIONS`

---

## Complete Example

```javascript
class FramoModelLoader {
    constructor() {
        this.lastTimestamp = null;
        this.scene = null;
    }

    async fetchMetadata() {
        const response = await fetch("http://localhost:8080/latest-model-info");
        if (!response.ok) return null;
        return await response.json();
    }

    async loadModel() {
        const response = await fetch("http://localhost:8080/latest-model");
        if (!response.ok) return null;

        const blob = await response.blob();
        return URL.createObjectURL(blob);
    }

    async checkAndUpdate() {
        const metadata = await this.fetchMetadata();
        if (!metadata) return;

        // Check if model changed
        if (metadata.timestamp === this.lastTimestamp) return;
        this.lastTimestamp = metadata.timestamp;

        // Load new model
        const url = await this.loadModel();
        if (!url) return;

        // Load with Three.js GLTFLoader
        const loader = new THREE.GLTFLoader();
        loader.load(url, (gltf) => {
            // Remove old model
            if (this.scene) {
                this.scene.traverse((obj) => {
                    if (obj.geometry) obj.geometry.dispose();
                    if (obj.material) {
                        if (Array.isArray(obj.material)) {
                            obj.material.forEach((m) => m.dispose());
                        } else {
                            obj.material.dispose();
                        }
                    }
                });
                this.scene.clear();
            }

            // Add new model
            this.scene = gltf.scene;
            // Add to your Three.js scene...

            // Check for unsupported materials
            this.checkMaterials(gltf, metadata);
        });
    }

    checkMaterials(gltf, metadata) {
        // Method 1: Check metadata
        if (metadata.materials?.unsupported.length > 0) {
            console.warn(
                "Unsupported materials:",
                metadata.materials.unsupported
            );

            metadata.materials.unsupported.forEach((name) => {
                const analysis = metadata.materials.analysis[name];
                console.warn(`Material "${name}" issues:`, analysis.issues);
            });
        }

        // Method 2: Check GLB extras
        gltf.scene.traverse((node) => {
            if (node.material && node.material.userData) {
                const extras =
                    node.material.userData.gltfExtensions?.extras || {};
                if (extras.framo_unsupported) {
                    console.warn(
                        `Material "${node.material.name}" marked as unsupported in GLB`
                    );
                }
            }
        });
    }

    startPolling(intervalMs = 2000) {
        setInterval(() => this.checkAndUpdate(), intervalMs);
        this.checkAndUpdate(); // Initial load
    }
}

// Usage
const loader = new FramoModelLoader();
loader.startPolling(2000);
```

---

## Notes

-   Server starts automatically when Blender addon is enabled
-   Server stops when Blender closes or addon is disabled
-   Only stores the **latest** model in memory (no history)
-   File sizes typically 0.1-5 MB depending on compression settings
-   Material analysis is performed automatically before export
-   Unsupported materials are marked in both metadata and GLB file extras
