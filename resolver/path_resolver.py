# path_resolver.py
# Translates logical or placeholder paths into real system paths.
# Pure translation layer — does not validate, does not execute.
# Designed to be OS-aware for future cross-platform support.

import os
import platform  # Reserved for future OS-specific resolver routing


# ---------------------------------------------------------------------------
# COMMON LOCATION MAP
# Detects OneDrive paths at runtime — handles both standard and
# OneDrive-synced Desktop/Documents locations automatically.
# ---------------------------------------------------------------------------

HOME = os.path.expanduser("~")

def _resolve_common_locations() -> dict:
    """
    Builds the common locations map at runtime.
    Prefers OneDrive paths when they exist — handles Windows + OneDrive setups.
    Falls back to standard paths for non-OneDrive systems.
    This makes the resolver work correctly across different Windows setups.
    """
    onedrive = os.path.join(HOME, "OneDrive")

    # If OneDrive exists, prefer those paths — they're the real locations
    if os.path.isdir(onedrive):
        base = onedrive
    else:
        base = HOME

    return {
        "Desktop":   os.path.join(base, "Desktop"),
        "Documents": os.path.join(base, "Documents"),
        "Downloads": os.path.join(HOME, "Downloads"),  # Downloads rarely syncs
        "Pictures":  os.path.join(base, "Pictures"),
        "Music":     os.path.join(base, "Music"),
        "Videos":    os.path.join(base, "Videos"),
    }

# Build the map once at import time — not on every function call
COMMON_LOCATIONS = _resolve_common_locations()


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------

def _normalize_path(path: str) -> str:
    """
    Cleans raw path string before processing.
    Private — use resolve_path() externally, not this directly.
    """
    path = path.strip()
    path = path.replace("/", "\\")
    while "\\\\" in path[2:]:
        path = path[:2] + path[2:].replace("\\\\", "\\")
    return path


# ---------------------------------------------------------------------------
# PUBLIC INTERFACE
# ---------------------------------------------------------------------------

def resolve_path(path: str) -> str:
    """
    Translates a logical or placeholder path into a real system path.
    Returns path unchanged if no known location is found.
    Never crashes — unknown paths pass through safely.
    """
    path = _normalize_path(path)

    for location_name, real_path in COMMON_LOCATIONS.items():
        marker = "\\" + location_name
        if marker in path:
            remainder = path.split(marker, 1)[-1]
            return real_path + remainder

    return path


def resolve_command_paths(command: dict) -> dict:
    """
    Applies resolve_path() to all path fields in a command dictionary.
    Returns a new dict — never mutates the original.
    """
    path_fields = ["source", "destination", "path"]
    parameters = command.get("parameters", {})

    resolved_parameters = {}
    for key, value in parameters.items():
        if key in path_fields and isinstance(value, str):
            resolved_parameters[key] = resolve_path(value)
        else:
            resolved_parameters[key] = value

    return {
        "action": command.get("action"),
        "parameters": resolved_parameters,
        "confirmation_required": command.get("confirmation_required")
    }