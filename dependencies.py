"""
Dependency management for the addon
Handles installation and checking of external Python libraries
"""

import bpy
import subprocess
import sys
import os
from typing import List, Tuple, Optional

# Required dependencies
REQUIRED_DEPENDENCIES = {
    'trimesh': {
        'name': 'trimesh',
        'description': 'Fast mesh decimation and repair',
        'required_for': ['mesh_repair', 'fast_decimation'],
        'optional': False,
        'install_order': 1
    },
    'scipy': {
        'name': 'scipy',
        'description': 'Scientific computing (required for quadric decimation)',
        'required_for': ['fast_decimation'],
        'optional': False,
        'install_order': 2
    },
    'networkx': {
        'name': 'networkx',
        'description': 'Graph algorithms (for mesh normals, hole filling, watertight)',
        'required_for': ['mesh_repair'],
        'optional': True,
        'install_order': 3
    },
    'fast_simplification': {
        'name': 'fast-simplification',
        'description': 'Fast mesh simplification for Trimesh',
        'required_for': ['fast_decimation'],
        'optional': False,
        'install_order': 4
    }
}


def get_python_executable() -> str:
    """Get the path to Blender's Python executable"""
    return sys.executable


def check_package_installed(package_name: str) -> bool:
    """Check if a Python package is installed"""
    try:
        # Handle packages with different pip vs import names
        import_name = package_name.replace('-', '_')
        __import__(import_name)
        return True
    except ImportError:
        return False


def install_package(package_name: str, user_requested: bool = False) -> Tuple[bool, str]:
    """
    Install a Python package using pip
    
    Args:
        package_name: Name of the package to install
        user_requested: True if user explicitly requested installation
    
    Returns:
        Tuple of (success, message)
    """
    try:
        python_exe = get_python_executable()
        
        # Show progress
        if user_requested:
            print(f"Installing {package_name}...")
        
        # Run pip install
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )
        
        if result.returncode == 0:
            # Verify installation
            if check_package_installed(package_name):
                return True, f"{package_name} installed successfully"
            else:
                return False, f"{package_name} installation completed but import failed"
        else:
            error_msg = result.stderr if result.stderr else result.stdout
            return False, f"Failed to install {package_name}: {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, f"Installation timeout for {package_name}"
    except Exception as e:
        return False, f"Error installing {package_name}: {str(e)}"


def check_all_dependencies() -> dict:
    """Check status of all dependencies"""
    status = {}
    
    for key, dep_info in REQUIRED_DEPENDENCIES.items():
        package_name = dep_info['name']
        is_installed = check_package_installed(package_name)
        
        status[key] = {
            'installed': is_installed,
            'name': package_name,
            'description': dep_info['description'],
            'required_for': dep_info['required_for'],
            'optional': dep_info.get('optional', False)
        }
    
    return status


def get_missing_dependencies() -> List[str]:
    """Get list of missing required (non-optional) dependencies"""
    status = check_all_dependencies()
    missing = []
    
    for key, dep_status in status.items():
        if not dep_status['installed'] and not dep_status['optional']:
            missing.append(key)
    
    return missing


class FRAMO_OT_install_dependencies(bpy.types.Operator):
    """Install required Python dependencies"""
    bl_idname = "framo.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = "Install required Python packages (trimesh, scipy, fast-simplification)"
    
    package: bpy.props.StringProperty(
        name="Package",
        description="Package to install",
        default=""
    )
    
    def execute(self, context):
        if not self.package:
            # Install all missing dependencies
            missing = get_missing_dependencies()
            if not missing:
                self.report({'INFO'}, "All required dependencies are installed!")
                return {'FINISHED'}
            
            # Sort dependencies by install order
            deps_to_install = []
            for key in missing:
                dep_info = REQUIRED_DEPENDENCIES[key]
                deps_to_install.append((
                    dep_info.get('install_order', 999),
                    key,
                    dep_info['name']
                ))
            
            deps_to_install.sort()  # Sort by install_order
            
            # Install each dependency in order
            installed_count = 0
            failed_packages = []
            
            for _, key, package_name in deps_to_install:
                print(f"Installing {package_name}...")
                success, msg = install_package(package_name, user_requested=True)
                
                if success:
                    installed_count += 1
                    print(f"✓ {package_name} installed successfully")
                else:
                    failed_packages.append((package_name, msg))
                    print(f"✗ {package_name} failed: {msg}")
            
            # Report results
            if failed_packages:
                error_msgs = [f"{pkg}: {msg}" for pkg, msg in failed_packages]
                self.report({'ERROR'}, f"Some installations failed. Check console for details.")
                print("\nFailed installations:")
                for pkg, msg in failed_packages:
                    print(f"  - {pkg}: {msg}")
                return {'CANCELLED'}
            else:
                self.report({'INFO'}, f"Successfully installed {installed_count} packages! Please restart Blender.")
                return {'FINISHED'}
            
        else:
            # Install specific package
            success, msg = install_package(self.package, user_requested=True)
            if success:
                self.report({'INFO'}, f"{self.package} installed successfully! Please restart Blender.")
            else:
                self.report({'ERROR'}, f"Installation failed: {msg}")
                return {'CANCELLED'}
        
        return {'FINISHED'}
    
    def invoke(self, context, event):
        if self.package:
            return self.execute(context)
        else:
            # Show confirmation dialog
            return context.window_manager.invoke_confirm(self, event)


def register_dependency_operator():
    """Register the dependency installation operator"""
    bpy.utils.register_class(FRAMO_OT_install_dependencies)


def unregister_dependency_operator():
    """Unregister the dependency installation operator"""
    bpy.utils.unregister_class(FRAMO_OT_install_dependencies)

