"""
Framo Bridge Auto-Update System
Handles checking for updates, downloading, and installing new versions from GitHub releases.
"""

import urllib.request
import urllib.error
import json
import os
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
        """
        try:
            # Create request with timeout
            req = urllib.request.Request(
                GITHUB_API_URL,
                headers={'Accept': 'application/vnd.github.v3+json'}
            )

            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    print(f"GitHub API returned status {response.status}")
                    return None

                data = json.loads(response.read().decode('utf-8'))

                # Parse release information
                tag_name = data.get('tag_name', '')
                latest_version = GitHubReleaseChecker.parse_version(tag_name)

                if not latest_version:
                    print(f"Could not parse version from tag: {tag_name}")
                    return None

                # Check if update is available
                if not GitHubReleaseChecker.is_newer_version(current_version, latest_version):
                    return None

                # Find the .zip asset
                assets = data.get('assets', [])
                zip_asset = None

                for asset in assets:
                    if asset.get('name', '').endswith('.zip'):
                        zip_asset = asset
                        break

                if not zip_asset:
                    print(f"No .zip asset found in release {tag_name}")
                    return None

                # Create UpdateInfo object
                update_info = UpdateInfo(
                    version=latest_version,
                    tag_name=tag_name,
                    download_url=zip_asset.get('browser_download_url', ''),
                    changelog=data.get('body', 'No changelog available.'),
                    published_at=data.get('published_at', '')
                )
                update_info.size_bytes = zip_asset.get('size', 0)

                return update_info

        except urllib.error.HTTPError as e:
            print(f"HTTP Error checking for updates: {e.code} {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"URL Error checking for updates: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing GitHub API response: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error checking for updates: {e}")
            return None


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
                return False

            extracted_path = Path(metadata['extracted_path'])

            if not extracted_path.exists():
                print(f"Pending update path not found: {extracted_path}")
                UpdateInstaller.clear_pending_update()
                return False

            # Get addon directory
            addon_dir = Path(bpy.utils.user_resource('SCRIPTS')) / "addons" / "framo-bridge"

            if not addon_dir.exists():
                print(f"Addon directory not found: {addon_dir}")
                return False

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
                    shutil.copytree(item, addon_dir / item.name)

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
