"""
Framo Bridge Auto-Update System
Handles checking for updates, downloading, and installing new versions from GitHub releases.
"""

import urllib.request
import urllib.error
import json
import os
import socket
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta

# GitHub repository information
GITHUB_OWNER = "r0m4nm"
GITHUB_REPO = "framo-bridge"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Update check cache duration (24 hours)
CACHE_DURATION_HOURS = 24


class UpdateInfo:
    """Information about an available update."""

    def __init__(self, version: Tuple[int, int, int], tag_name: str,
                 download_url: str, changelog: str, published_at: str):
        self.version = version
        self.tag_name = tag_name
        self.download_url = download_url
        self.changelog = changelog
        self.published_at = published_at
        self.size_bytes = 0


class GitHubReleaseChecker:
    """Handles checking GitHub releases for updates."""

    @staticmethod
    def parse_version(tag_name: str) -> Optional[Tuple[int, int, int]]:
        """
        Parse version tuple from tag name.
        Examples: "v0.1.0" -> (0, 1, 0), "0.1.2" -> (0, 1, 2)
        """
        # Remove 'v' prefix if present
        version_str = tag_name.lstrip('v')

        try:
            parts = version_str.split('.')
            if len(parts) != 3:
                return None

            major, minor, patch = map(int, parts)
            return (major, minor, patch)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def version_to_string(version: Tuple[int, int, int]) -> str:
        """Convert version tuple to string: (0, 1, 0) -> "0.1.0" """
        return f"{version[0]}.{version[1]}.{version[2]}"

    @staticmethod
    def is_newer_version(current: Tuple[int, int, int],
                         latest: Tuple[int, int, int]) -> bool:
        """Check if latest version is newer than current version."""
        return latest > current

    @staticmethod
    def check_for_updates(current_version: Tuple[int, int, int],
                         timeout: int = 10) -> Optional[UpdateInfo]:
        """
        Check GitHub API for the latest release.

        Args:
            current_version: Current addon version tuple
            timeout: Request timeout in seconds

        Returns:
            UpdateInfo if newer version available, None otherwise
            
        Raises:
            Exception: If there's a network or API error (for better error reporting)
        """
        try:
            print(f"Framo Bridge: Fetching latest release from GitHub...")
            print(f"Framo Bridge: API URL: {GITHUB_API_URL}")
            
            # Create request with timeout and user agent (some servers require this)
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Framo-Bridge-Addon/1.0'
                }
            )

            print(f"Framo Bridge: Opening connection (timeout: {timeout}s)...")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                print(f"Framo Bridge: Response status: {response.status}")
                
                if response.status != 200:
                    error_msg = f"GitHub API returned status {response.status}"
                    print(f"Framo Bridge: {error_msg}")
                    raise Exception(error_msg)

                print("Framo Bridge: Reading response data...")
                response_data = response.read()
                print(f"Framo Bridge: Received {len(response_data)} bytes")
                
                data = json.loads(response_data.decode('utf-8'))
                print(f"Framo Bridge: Successfully parsed JSON response")

                # Parse release information
                tag_name = data.get('tag_name', '')
                print(f"Framo Bridge: Latest release tag: {tag_name}")
                
                latest_version = GitHubReleaseChecker.parse_version(tag_name)

                if not latest_version:
                    error_msg = f"Could not parse version from tag: {tag_name}"
                    print(f"Framo Bridge: {error_msg}")
                    raise Exception(error_msg)

                print(f"Framo Bridge: Parsed version: {latest_version}")
                print(f"Framo Bridge: Current version: {current_version}")

                # Check if update is available
                if not GitHubReleaseChecker.is_newer_version(current_version, latest_version):
                    print("Framo Bridge: No newer version available")
                    return None

                print(f"Framo Bridge: Newer version found: {latest_version}")

                # Find the .zip asset
                assets = data.get('assets', [])
                print(f"Framo Bridge: Found {len(assets)} assets in release")
                
                zip_asset = None

                for asset in assets:
                    asset_name = asset.get('name', '')
                    print(f"Framo Bridge: Checking asset: {asset_name}")
                    if asset_name.endswith('.zip'):
                        zip_asset = asset
                        print(f"Framo Bridge: Found zip asset: {asset_name}")
                        break

                if not zip_asset:
                    error_msg = f"No .zip asset found in release {tag_name}"
                    print(f"Framo Bridge: {error_msg}")
                    raise Exception(error_msg)

                # Create UpdateInfo object
                update_info = UpdateInfo(
                    version=latest_version,
                    tag_name=tag_name,
                    download_url=zip_asset.get('browser_download_url', ''),
                    changelog=data.get('body', 'No changelog available.'),
                    published_at=data.get('published_at', '')
                )
                update_info.size_bytes = zip_asset.get('size', 0)

                print(f"Framo Bridge: Update info created successfully")
                print(f"Framo Bridge: Download URL: {update_info.download_url}")
                print(f"Framo Bridge: Size: {update_info.size_bytes} bytes")

                return update_info

        except urllib.error.HTTPError as e:
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            print(f"Framo Bridge: {error_msg}")
            # Try to read error response body for more details
            try:
                error_body = e.read().decode('utf-8')
                print(f"Framo Bridge: Error response body: {error_body[:200]}")
            except:
                pass
            raise Exception(error_msg)
            
        except urllib.error.URLError as e:
            error_reason = str(e.reason) if e.reason else str(e)
            error_msg = f"Network error: {error_reason}"
            print(f"Framo Bridge: {error_msg}")
            print(f"Framo Bridge: This might be a network connectivity issue or firewall blocking the connection")
            print(f"Framo Bridge: On macOS, check System Preferences > Security & Privacy > Firewall")
            raise Exception(error_msg)
            
        except socket.timeout:
            error_msg = f"Connection timeout after {timeout} seconds"
            print(f"Framo Bridge: {error_msg}")
            raise Exception(error_msg)
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from GitHub API: {e}"
            print(f"Framo Bridge: {error_msg}")
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"Framo Bridge: {error_msg}")
            import traceback
            traceback.print_exc()
            raise Exception(error_msg)


class UpdateDownloader:
    """Handles downloading and preparing updates."""

    def __init__(self, update_info: UpdateInfo):
        self.update_info = update_info
        self.temp_dir = Path(tempfile.gettempdir()) / "framo-bridge-updates"
        self.download_progress = 0.0
        self.download_complete = False
        self.download_error: Optional[str] = None

    def download(self, progress_callback=None) -> Optional[Path]:
        """
        Download the update .zip file.

        Args:
            progress_callback: Optional callback(progress: float) called during download

        Returns:
            Path to downloaded file, or None on error
        """
        try:
            # Create temp directory
            self.temp_dir.mkdir(parents=True, exist_ok=True)

            # Download file
            zip_filename = f"framo-bridge-v{self.version_string}.zip"
            zip_path = self.temp_dir / zip_filename

            # Remove existing file if present
            if zip_path.exists():
                zip_path.unlink()

            def report_progress(block_num, block_size, total_size):
                if total_size > 0 and progress_callback:
                    downloaded = block_num * block_size
                    progress = min(downloaded / total_size, 1.0)
                    self.download_progress = progress
                    progress_callback(progress)

            urllib.request.urlretrieve(
                self.update_info.download_url,
                zip_path,
                reporthook=report_progress if progress_callback else None
            )

            # Verify download
            if not zip_path.exists():
                self.download_error = "Download failed: file not created"
                return None

            if zip_path.stat().st_size == 0:
                self.download_error = "Download failed: file is empty"
                return None

            self.download_complete = True
            return zip_path

        except Exception as e:
            self.download_error = f"Download error: {str(e)}"
            print(self.download_error)
            return None

    @property
    def version_string(self) -> str:
        """Get version as string."""
        return GitHubReleaseChecker.version_to_string(self.update_info.version)

    def validate_zip(self, zip_path: Path) -> bool:
        """
        Validate that the downloaded zip is a valid Framo Bridge addon.

        Args:
            zip_path: Path to the .zip file

        Returns:
            True if valid, False otherwise
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Check for required files
                namelist = zf.namelist()

                # Must contain framo-bridge/__init__.py
                if 'framo-bridge/__init__.py' not in namelist:
                    print("Invalid zip: missing framo-bridge/__init__.py")
                    return False

                # Try to read and parse bl_info
                init_content = zf.read('framo-bridge/__init__.py').decode('utf-8')

                if 'bl_info' not in init_content:
                    print("Invalid zip: __init__.py missing bl_info")
                    return False

                return True

        except zipfile.BadZipFile:
            print(f"Invalid zip file: {zip_path}")
            return False
        except Exception as e:
            print(f"Error validating zip: {e}")
            return False

    def extract_update(self, zip_path: Path) -> Optional[Path]:
        """
        Extract the update to a temporary location.

        Args:
            zip_path: Path to the downloaded .zip

        Returns:
            Path to extracted addon folder, or None on error
        """
        try:
            extract_dir = self.temp_dir / f"framo-bridge-v{self.version_string}"

            # Remove existing extraction if present
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

            # Extract
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            # Return path to the framo-bridge folder inside extraction
            addon_folder = extract_dir / "framo-bridge"

            if not addon_folder.exists():
                print(f"Extraction failed: addon folder not found at {addon_folder}")
                return None

            return addon_folder

        except Exception as e:
            print(f"Error extracting update: {e}")
            return None


class UpdateInstaller:
    """Handles installing updates on Blender restart."""

    @staticmethod
    def get_pending_update_file() -> Path:
        """Get path to pending update metadata file."""
        import bpy

        # Store in Blender's config directory
        config_dir = Path(bpy.utils.user_resource('CONFIG'))
        return config_dir / "framo_pending_update.json"

    @staticmethod
    def save_pending_update(extracted_path: Path, version: Tuple[int, int, int]):
        """
        Save pending update information for installation on restart.

        Args:
            extracted_path: Path to extracted addon folder
            version: Version tuple
        """
        try:
            metadata = {
                "version": version,
                "extracted_path": str(extracted_path),
                "timestamp": datetime.now().isoformat()
            }

            pending_file = UpdateInstaller.get_pending_update_file()

            with open(pending_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            print(f"Saved pending update: {pending_file}")

        except Exception as e:
            print(f"Error saving pending update: {e}")

    @staticmethod
    def has_pending_update() -> bool:
        """Check if there's a pending update to install."""
        return UpdateInstaller.get_pending_update_file().exists()

    @staticmethod
    def get_pending_update() -> Optional[Dict]:
        """Load pending update metadata."""
        try:
            pending_file = UpdateInstaller.get_pending_update_file()

            if not pending_file.exists():
                return None

            with open(pending_file, 'r') as f:
                return json.load(f)

        except Exception as e:
            print(f"Error loading pending update: {e}")
            return None

    @staticmethod
    def get_addon_directory() -> Optional[Path]:
        """
        Get the actual addon directory path.
        Works across all platforms (Windows, macOS, Linux).
        Works even when bpy.context is not available (e.g., during startup).

        Returns:
            Path to the addon directory, or None if not found
        """
        try:
            import bpy
            import sys

            # Method 1: Use the current module's location (most reliable)
            # Since updater.py is in the addon folder, we can use its location
            current_file = Path(__file__).resolve()
            if current_file.name == 'updater.py':
                addon_dir = current_file.parent
                if addon_dir.exists() and (addon_dir / '__init__.py').exists():
                    return addon_dir

            # Method 1b: Try to get from sys.modules (works without context)
            # Try different possible module name formats
            possible_module_names = ['framo-bridge', 'framo_bridge']
            for module_name in possible_module_names:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                    if hasattr(module, '__file__') and module.__file__:
                        try:
                            file_path = Path(module.__file__).resolve()
                            # Check if this looks like our addon's __init__.py
                            if file_path.name == '__init__.py' and file_path.parent.name == 'framo-bridge':
                                addon_dir = file_path.parent
                                if addon_dir.exists() and (addon_dir / '__init__.py').exists():
                                    return addon_dir
                        except (OSError, ValueError):
                            pass
            
            # Method 1c: Search through all loaded modules for our addon
            for module_name, module in sys.modules.items():
                if hasattr(module, '__file__') and module.__file__:
                    try:
                        file_path = Path(module.__file__).resolve()
                        # Check if this is our addon's __init__.py
                        if file_path.name == '__init__.py' and 'framo-bridge' in str(file_path):
                            addon_dir = file_path.parent
                            if addon_dir.exists() and (addon_dir / '__init__.py').exists():
                                # Verify it's actually our addon by checking for a known file
                                if (addon_dir / 'updater.py').exists():
                                    return addon_dir
                    except (OSError, ValueError, AttributeError):
                        pass

            # Method 2: Try to get from bpy.context if available
            try:
                if hasattr(bpy.context, 'preferences'):
                    addon_prefs = bpy.context.preferences.addons.get('framo-bridge')
                    if addon_prefs and hasattr(addon_prefs, 'module'):
                        module = addon_prefs.module
                        if hasattr(module, '__file__') and module.__file__:
                            addon_dir = Path(module.__file__).parent
                            if addon_dir.exists():
                                return addon_dir
            except (AttributeError, RuntimeError):
                # bpy.context not available (common on macOS during startup)
                pass

            # Method 3: Try bpy.context.preferences if available (fallback)
            # Note: This may not work during startup on macOS
            try:
                if hasattr(bpy, 'context') and hasattr(bpy.context, 'preferences'):
                    prefs = bpy.context.preferences
                    addon_prefs = prefs.addons.get('framo-bridge')
                    if addon_prefs and hasattr(addon_prefs, 'module'):
                        module = addon_prefs.module
                        if hasattr(module, '__file__') and module.__file__:
                            addon_dir = Path(module.__file__).parent
                            if addon_dir.exists():
                                return addon_dir
            except (AttributeError, RuntimeError):
                # bpy.context not available - this is expected on macOS during startup
                pass

            # Method 4: Fallback to standard locations
            scripts_dir = Path(bpy.utils.user_resource('SCRIPTS'))
            
            # Check standard addons directory
            addon_dir = scripts_dir / "addons" / "framo-bridge"
            if addon_dir.exists() and (addon_dir / '__init__.py').exists():
                return addon_dir

            # Check contrib directory
            modules_dir = scripts_dir / "addons_contrib" / "framo-bridge"
            if modules_dir.exists() and (modules_dir / '__init__.py').exists():
                return modules_dir

            # Check system addons (macOS sometimes uses different locations)
            if hasattr(bpy.utils, 'script_path_user'):
                user_scripts = Path(bpy.utils.script_path_user())
                user_addon_dir = user_scripts / "addons" / "framo-bridge"
                if user_addon_dir.exists() and (user_addon_dir / '__init__.py').exists():
                    return user_addon_dir

            print("Framo Bridge: Could not locate addon directory")
            return None

        except Exception as e:
            print(f"Framo Bridge: Error getting addon directory: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def install_pending_update() -> bool:
        """
        Install the pending update by replacing addon files.
        Should be called before the addon is loaded.

        Returns:
            True if successful, False otherwise
        """
        try:
            import bpy

            metadata = UpdateInstaller.get_pending_update()
            if not metadata:
                print("Framo Bridge: No pending update metadata found")
                return False

            extracted_path = Path(metadata['extracted_path'])
            print(f"Framo Bridge: Installing update from {extracted_path}")

            if not extracted_path.exists():
                print(f"Framo Bridge: Pending update path not found: {extracted_path}")
                UpdateInstaller.clear_pending_update()
                return False

            # Get addon directory (platform-independent)
            addon_dir = UpdateInstaller.get_addon_directory()

            if not addon_dir:
                print("Framo Bridge: Could not determine addon directory")
                return False

            if not addon_dir.exists():
                print(f"Framo Bridge: Addon directory does not exist: {addon_dir}")
                return False

            print(f"Framo Bridge: Installing to addon directory: {addon_dir}")

            # Replace files
            # Delete old addon files (except user data if any)
            for item in addon_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir() and item.name != '__pycache__':
                    shutil.rmtree(item)

            # Copy new files
            for item in extracted_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, addon_dir / item.name)
                elif item.is_dir() and item.name != '__pycache__':
                    dest_path = addon_dir / item.name
                    # Remove existing directory if it exists
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(item, dest_path)

            print(f"Successfully installed update to {addon_dir}")

            # Clean up
            UpdateInstaller.clear_pending_update()

            # Try to delete temp extraction
            try:
                shutil.rmtree(extracted_path.parent)
            except:
                pass  # Cleanup is best-effort

            return True

        except Exception as e:
            print(f"Error installing pending update: {e}")
            return False

    @staticmethod
    def clear_pending_update():
        """Remove pending update metadata."""
        try:
            pending_file = UpdateInstaller.get_pending_update_file()
            if pending_file.exists():
                pending_file.unlink()
        except Exception as e:
            print(f"Error clearing pending update: {e}")
