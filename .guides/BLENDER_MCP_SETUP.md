# Blender MCP Server Setup Guide

This guide will help you set up a Blender MCP (Model Context Protocol) server so that AI assistants can directly query and test Blender's API, preventing issues like the bmesh decimation problem we encountered.

## What This Enables

With Blender MCP configured, AI assistants can:

-   Execute test scripts directly in your Blender environment
-   Query available API functions before writing code
-   Validate assumptions against your specific Blender version
-   Test code snippets in real-time

## Prerequisites

-   Blender 3.0+ (you have 4.4 ✓)
-   Python 3.7+
-   Node.js and npm (for some servers)
-   Git

## Option 1: Using uvx (Recommended - Simplest)

### Step 1: Install uv/uvx

```bash
# On Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Step 2: Install Blender MCP Server

```bash
uvx blender-mcp
```

### Step 3: Configure Cursor

1. Open Cursor settings: `Ctrl/Cmd + Shift + P` → "Preferences: Open User Settings (JSON)"

2. Add MCP configuration:

```json
{
    "mcp": {
        "servers": {
            "blender": {
                "command": "uvx",
                "args": ["blender-mcp"],
                "env": {
                    "BLENDER_PATH": "C:\\Program Files\\Blender Foundation\\Blender 4.4\\blender.exe"
                }
            }
        }
    }
}
```

### Step 4: Install Blender Addon

1. Download the addon from: https://github.com/ahujasid/blender-mcp
2. In Blender: `Edit → Preferences → Add-ons`
3. Click `Install...` → Select `addon.py`
4. Enable the "Blender MCP" addon

### Step 5: Restart Cursor

Close and reopen Cursor to activate the MCP server.

## Option 2: Manual Setup

### Step 1: Clone Repository

```bash
cd C:\Dev
git clone https://github.com/ahujasid/blender-mcp.git
cd blender-mcp
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure Cursor

```json
{
    "mcp": {
        "servers": {
            "blender": {
                "command": "C:\\Dev\\blender-mcp\\venv\\Scripts\\python.exe",
                "args": ["C:\\Dev\\blender-mcp\\server.py"],
                "env": {
                    "BLENDER_PATH": "C:\\Program Files\\Blender Foundation\\Blender 4.4\\blender.exe"
                }
            }
        }
    }
}
```

### Step 4: Install Blender Addon (same as above)

## Alternative: UBOS Blender MCP Server

UBOS offers a headless Blender script execution server:

```bash
# Install via npm
npm install -g @ubos/blender-mcp-server

# Or use npx directly
npx @ubos/blender-mcp-server
```

### Cursor Configuration:

```json
{
    "mcp": {
        "servers": {
            "blender": {
                "command": "npx",
                "args": ["@ubos/blender-mcp-server"],
                "env": {
                    "BLENDER_PATH": "C:\\Program Files\\Blender Foundation\\Blender 4.4\\blender.exe"
                }
            }
        }
    }
}
```

## Testing the Setup

After configuration, try asking in Cursor:

```
"What bmesh operators are available for decimation in my Blender version?"
```

The AI should be able to execute a test script and return actual results from your Blender installation.

## Verification Script

Create a test in Blender's Script Editor:

```python
import bmesh
import bpy

# List all bmesh.ops that contain "decim"
print("Available decimation operators:")
for attr in dir(bmesh.ops):
    if 'decim' in attr.lower():
        print(f"  - {attr}")

# Test if specific operators exist
ops_to_test = ['decimate', 'decimate_collapse', 'decimate_dissolve', 'decimate_planar']
for op in ops_to_test:
    exists = hasattr(bmesh.ops, op)
    print(f"{op}: {'✓' if exists else '✗'}")
```

## Troubleshooting

### Server not connecting

-   Check that Blender path is correct
-   Verify Python/Node.js are in PATH
-   Check Cursor's output panel for MCP errors

### Blender path issues

Find your Blender executable:

```bash
# Windows
where blender

# Or check default location
C:\Program Files\Blender Foundation\Blender 4.4\blender.exe
```

### Permission errors

Run Cursor as administrator (Windows) or with appropriate permissions.

## Benefits for This Project

With MCP configured, future development will:

-   ✓ Validate API calls before implementation
-   ✓ Test against your exact Blender version
-   ✓ Discover available functions automatically
-   ✓ Catch deprecated/missing APIs immediately
-   ✓ Test complex workflows interactively

## Resources

-   Blender MCP GitHub: https://github.com/ahujasid/blender-mcp
-   UBOS MCP Server: https://ubos.tech/mcp/blender-mcp-server/
-   MCP Protocol: https://modelcontextprotocol.io/
-   Blender Python API: https://docs.blender.org/api/current/

---

**Note**: This would have immediately revealed that `bmesh.ops.decimate_collapse` doesn't exist, saving us the debugging time!
