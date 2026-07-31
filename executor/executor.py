# executor.py
# Execution engine — performs validated file system operations.
# Returns concise status codes only — presentation is main.py's responsibility.
# Only called after schema validation, path resolution, and semantic validation.
# This module actually modifies the file system — handle with care.

import os
import shutil


# ---------------------------------------------------------------------------
# ACTION EXECUTORS
# ---------------------------------------------------------------------------

def _execute_move_file(parameters: dict) -> tuple:
    """
    Moves a file from source to destination.
    Returns status code only — no user-facing messages.
    """
    source = parameters.get("source")
    destination = parameters.get("destination")

    try:
        shutil.move(source, destination)
        return (True, "MOVE_SUCCESS")

    except PermissionError:
        return (False, "PERMISSION_DENIED")

    except OSError:
        return (False, "OS_ERROR")

    except Exception:
        return (False, "UNEXPECTED_ERROR")


def _execute_rename_file(parameters: dict) -> tuple:
    """
    Renames a file in place within the same directory.
    Constructs full destination path from source directory + new name.
    """
    source = parameters.get("source")
    new_name = parameters.get("new_name")

    source_directory = os.path.dirname(source)
    destination = os.path.join(source_directory, new_name)

    try:
        os.rename(source, destination)
        return (True, "RENAME_SUCCESS")

    except PermissionError:
        return (False, "PERMISSION_DENIED")

    except OSError:
        return (False, "OS_ERROR")

    except Exception:
        return (False, "UNEXPECTED_ERROR")


def _execute_create_folder(parameters: dict) -> tuple:
    """
    Creates a new folder at path/folder_name.
    Uses os.makedirs() to handle nested directory creation.
    """
    path = parameters.get("path")
    folder_name = parameters.get("folder_name")
    full_path = os.path.join(path, folder_name)

    try:
        os.makedirs(full_path)
        return (True, "CREATE_SUCCESS")

    except PermissionError:
        return (False, "PERMISSION_DENIED")

    except FileExistsError:
        return (False, "ALREADY_EXISTS")

    except OSError:
        return (False, "OS_ERROR")

    except Exception:
        return (False, "UNEXPECTED_ERROR")


# ---------------------------------------------------------------------------
# MAIN DISPATCHER
# ---------------------------------------------------------------------------

def execute_command(command: dict) -> tuple:
    """
    Routes to the correct action executor.
    Returns (True, status_code) on success.
    Returns (False, error_code) on failure.
    Trusts that input has passed full validation pipeline.
    """
    action = command.get("action")
    parameters = command.get("parameters", {})

    if action == "move_file":
        return _execute_move_file(parameters)

    elif action == "rename_file":
        return _execute_rename_file(parameters)

    elif action == "create_folder":
        return _execute_create_folder(parameters)

    else:
        return (False, "UNKNOWN_ACTION")