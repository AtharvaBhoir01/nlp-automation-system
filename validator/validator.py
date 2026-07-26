# validator.py
# Semantic validation layer — checks safety and correctness of resolved commands.
# Runs after schema validation and path resolution.
# Never executes commands — only judges whether they are safe to execute.

import os

# ---------------------------------------------------------------------------
# DANGEROUS LOCATIONS
# Paths that must never be touched — system-critical directories on Windows.
# Stored as lowercase for case-insensitive comparison.
# ---------------------------------------------------------------------------

DANGEROUS_PATHS = [
    "c:\\windows",
    "c:\\windows\\system32",
    "c:\\program files",
    "c:\\program files (x86)",
    "c:\\programdata",
]

# ---------------------------------------------------------------------------
# ILLEGAL FILENAME CHARACTERS
# Windows does not allow these characters in file or folder names.
# ---------------------------------------------------------------------------

ILLEGAL_CHARACTERS = set('\\/:*?"<>|')

# ---------------------------------------------------------------------------
# SHARED SAFETY CHECKS
# These apply regardless of action type — pure logic, no OS calls needed.
# ---------------------------------------------------------------------------

def _is_dangerous_path(path: str) -> bool:
    """
    Returns True if path targets a protected system directory.
    Case-insensitive comparison — Windows paths are not case-sensitive.
    """
    normalized = path.lower().strip()
    for dangerous in DANGEROUS_PATHS:
        if normalized.startswith(dangerous):
            return True
    return False


def _has_directory_traversal(path: str) -> bool:
    """
    Returns True if path contains directory traversal sequences.
    e.g. ../ or ..\\ — used to escape intended directories.
    This is a real security vulnerability if left unchecked.
    """
    return ".." in path


def _has_illegal_characters(name: str) -> bool:
    """
    Returns True if a filename contains characters Windows forbids.
    Checks the filename only — not the full path (slashes are valid in paths).
    """
    for char in name:
        if char in ILLEGAL_CHARACTERS:
            return True
    return False

# ---------------------------------------------------------------------------
# ACTION-SPECIFIC VALIDATORS
# Each action gets its own validator — modular and scalable.
# Adding a new action later means adding one function here.
# ---------------------------------------------------------------------------

def _validate_move_file(parameters: dict) -> tuple:
    """Validates a move_file command's parameters."""

    source = parameters.get("source", "")
    destination = parameters.get("destination", "")

    # Safety: directory traversal
    if _has_directory_traversal(source) or _has_directory_traversal(destination):
        return (False, "TRAVERSAL_ATTEMPT: Path contains directory traversal sequence (..)")

    # Safety: dangerous system locations
    if _is_dangerous_path(source) or _is_dangerous_path(destination):
        return (False, "DANGEROUS_PATH: Path targets a protected system directory")

    # Logic: source and destination are identical
    if source.lower() == destination.lower():
        return (False, "SAME_PATH: Source and destination paths are identical")

    # OS check: source file must exist
    if not os.path.isfile(source):
        return (False, f"SOURCE_NOT_FOUND: Source file does not exist: {source}")

    # OS check: destination folder must exist
    destination_folder = os.path.dirname(destination)
    if not os.path.isdir(destination_folder):
        return (False, f"DEST_FOLDER_NOT_FOUND: Destination folder does not exist: {destination_folder}")

    # OS check: file already exists at destination — prevent silent overwrite
    if os.path.exists(destination):
        return (False, f"DEST_EXISTS: A file already exists at destination: {destination}")

    return (True, "")


def _validate_rename_file(parameters: dict) -> tuple:
    """Validates a rename_file command's parameters."""

    source = parameters.get("source", "")
    new_name = parameters.get("new_name", "")

    # Safety: directory traversal
    if _has_directory_traversal(source):
        return (False, "TRAVERSAL_ATTEMPT: Path contains directory traversal sequence (..)")

    # Safety: dangerous location
    if _is_dangerous_path(source):
        return (False, "DANGEROUS_PATH: Path targets a protected system directory")

    # OS check: source file must exist
    if not os.path.isfile(source):
        return (False, f"SOURCE_NOT_FOUND: Source file does not exist: {source}")

    # Semantic: new_name should be a filename, not a full path
    if "\\" in new_name or "/" in new_name:
        return (False, "INVALID_NAME: new_name should be a filename only, not a full path")

    # Safety: illegal characters in new filename
    if _has_illegal_characters(new_name):
        return (False, f"ILLEGAL_CHARACTERS: Filename contains forbidden characters: {new_name}")

    # Warning: extension change — allowed but flagged
    source_ext = os.path.splitext(source)[-1].lower()
    new_ext = os.path.splitext(new_name)[-1].lower()
    if source_ext != new_ext:
        # Not blocking — just informational in the error string
        return (True, f"EXTENSION_CHANGED: File extension changed from {source_ext} to {new_ext}")

    return (True, "")


def _validate_create_folder(parameters: dict) -> tuple:
    """Validates a create_folder command's parameters."""

    path = parameters.get("path", "")
    folder_name = parameters.get("folder_name", "")

    # Safety: directory traversal
    if _has_directory_traversal(path):
        return (False, "TRAVERSAL_ATTEMPT: Path contains directory traversal sequence (..)")

    # Safety: dangerous location
    if _is_dangerous_path(path):
        return (False, "DANGEROUS_PATH: Path targets a protected system directory")

    # Safety: illegal characters in folder name
    if _has_illegal_characters(folder_name):
        return (False, f"ILLEGAL_CHARACTERS: Folder name contains forbidden characters: {folder_name}")

    # OS check: parent path must exist
    if not os.path.isdir(path):
        return (False, f"PATH_NOT_FOUND: Parent directory does not exist: {path}")

    # OS check: folder already exists
    full_path = os.path.join(path, folder_name)
    if os.path.exists(full_path):
        return (False, f"ALREADY_EXISTS: Folder already exists: {full_path}")

    return (True, "")

# ---------------------------------------------------------------------------
# MAIN DISPATCHER
# Public interface — routes to the correct action-specific validator.
# This is the only function other modules should call.
# ---------------------------------------------------------------------------

def validate_command(command: dict) -> tuple:
    """
    Main validation entry point.
    Routes to the correct action-specific validator based on command action.

    Returns (True, "") if valid.
    Returns (False, "ERROR_CODE: reason") if invalid.
    Returns (True, "WARNING_CODE: reason") for non-blocking warnings.

    Assumes command has already passed validate_command_structure()
    and path resolution — do not call this before those steps.
    """
    action = command.get("action")
    parameters = command.get("parameters", {})

    # Dispatch to the correct validator
    if action == "move_file":
        return _validate_move_file(parameters)

    elif action == "rename_file":
        return _validate_rename_file(parameters)

    elif action == "create_folder":
        return _validate_create_folder(parameters)

    else:
        # Should never reach here if schema validation ran first
        return (False, f"UNKNOWN_ACTION: No validator found for action: {action}")