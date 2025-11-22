import threading
from contextlib import contextmanager

# Thread-safe globals
_state_lock = threading.Lock()

# Private storage
_update_state = {
    "checking": False,
    "update_available": False,
    "latest_version": None,
    "update_info": None,
    "downloading": False,
    "installing": False,
    "download_progress": 0.0,
    "download_error": None,
    "pending_restart": False,
    "last_check_time": None
}

_framo_user_info = {
    "name": None,
    "email": None,
    "last_connected": None
}

_material_expanded_states = {}

@contextmanager
def safe_update_state_access():
    """Thread-safe access to update state"""
    with _state_lock:
        yield _update_state

def get_update_state_copy():
    """Get a copy of update state without lock (for reading only if consistency isn't critical)"""
    with _state_lock:
        return _update_state.copy()

@contextmanager
def safe_user_info_access():
    """Thread-safe access to user info"""
    with _state_lock:
        yield _framo_user_info

def get_user_info_copy():
    with _state_lock:
        return _framo_user_info.copy()

@contextmanager
def safe_material_states_access():
    """Thread-safe access to material expanded states"""
    with _state_lock:
        yield _material_expanded_states

