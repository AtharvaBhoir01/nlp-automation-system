# organizer.py
# Batch file organization engine.
# Responsible for: filesystem discovery, operation planning,
# pre-execution validation, and batch execution.
# The LLM provides only the source directory — this module
# discovers all files, builds the complete operation plan,
# and executes it with per-file feedback.
# Never called before schema validation and path resolution.

import os
import shutil
import ctypes
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# CATEGORY MAP
# Maps file extensions to human-readable folder names.
# Extensions are lowercase — comparison must normalize before lookup.
# ---------------------------------------------------------------------------

CATEGORY_MAP = {
    # Documents
    ".pdf": "PDFs",
    ".doc": "Documents",
    ".docx": "Documents",
    ".xls": "Documents",
    ".xlsx": "Documents",
    ".ppt": "Documents",
    ".pptx": "Documents",
    ".txt": "Documents",
    # Images
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".gif": "Images",
    ".bmp": "Images",
    ".webp": "Images",
    ".svg": "Images",
    # Videos
    ".mp4": "Videos",
    ".mov": "Videos",
    ".avi": "Videos",
    ".mkv": "Videos",
    # Audio
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".aac": "Audio",
    # Archives
    ".zip": "Archives",
    ".rar": "Archives",
    ".7z": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    # Code
    ".py": "Code",
    ".pyw": "Code",
    ".c": "Code",
    ".h": "Code",
    ".cpp": "Code",
    ".hpp": "Code",
    ".cc": "Code",
    ".cxx": "Code",
    ".java": "Code",
    ".class": "Code",
    ".js": "Code",
    ".jsx": "Code",
    ".ts": "Code",
    ".tsx": "Code",
    ".html": "Code",
    ".css": "Code",
    ".scss": "Code",
    ".json": "Code",
    ".xml": "Code",
    ".yaml": "Code",
    ".yml": "Code",
    ".php": "Code",
    ".rb": "Code",
    ".go": "Code",
    ".rs": "Code",
    ".swift": "Code",
    ".kt": "Code",
    ".sh": "Code",
    ".bat": "Code",
    ".ps1": "Code",
    ".sql": "Code",
    ".r": "Code",
}

# Explicit fallback — unknown extensions go here
FALLBACK_CATEGORY = "Other"


# ---------------------------------------------------------------------------
# DOMAIN MODEL
# ---------------------------------------------------------------------------


@dataclass
class FileOperation:
    source: str  # full resolved source path
    destination: str  # full resolved destination path (duplicate-safe)
    category: str  # human-readable category e.g. "PDFs"


@dataclass
class OperationPlan:
    source_directory: str
    operations: list = field(default_factory=list)  # list[FileOperation]
    category_counts: dict = field(default_factory=dict)  # {category: count}


@dataclass
class BatchResult:
    succeeded: list = field(default_factory=list)  # list[FileOperation]
    failed: list = field(default_factory=list)  # list[tuple[FileOperation, str]]

    @property
    def total(self) -> int:
        return len(self.succeeded) + len(self.failed)

    @property
    def success_count(self) -> int:
        return len(self.succeeded)

    @property
    def failure_count(self) -> int:
        return len(self.failed)


# ---------------------------------------------------------------------------
# FILE DISCOVERY
# Discovers eligible files in the source directory.
# Shallow only — root level files, no recursion.
# Excludes: subdirectories, hidden files, system files.
# ---------------------------------------------------------------------------


def _is_hidden_or_system(filepath: str) -> bool:
    """
    Returns True if file has Windows hidden or system attribute set.
    Uses ctypes to call Windows API directly — os module cannot do this.
    FILE_ATTRIBUTE_HIDDEN = 2
    FILE_ATTRIBUTE_SYSTEM = 4
    """
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(filepath)

        # GetFileAttributesW returns 0xFFFFFFFF (-1) on failure
        if attrs == -1:
            return False  # can't determine — don't exclude

        is_hidden = bool(attrs & 2)
        is_system = bool(attrs & 4)
        return is_hidden or is_system

    except Exception:
        return False  # safe default — don't exclude on error


def _get_category(filename: str) -> str:
    """
    Returns the category folder name for a given filename.
    Uses file extension only — content-based categorization is out of scope.
    Extension comparison is case-insensitive.
    Unknown extensions fall back to FALLBACK_CATEGORY.
    """
    # os.path.splitext splits "report.PDF" into ("report", ".PDF")
    _, ext = os.path.splitext(filename)
    return CATEGORY_MAP.get(ext.lower(), FALLBACK_CATEGORY)


def _resolve_duplicate(destination: str) -> str:
    """
    Generates a duplicate-safe destination path.
    If destination exists, appends (1), (2), etc. until a free name is found.

    Example:
        PDFs/report.pdf exists
        → PDFs/report (1).pdf
        → PDFs/report (2).pdf  (if (1) also exists)

    The counter is deterministic — same input always produces same output.
    """
    if not os.path.exists(destination):
        return destination

    # Split into directory, stem, and extension
    directory = os.path.dirname(destination)
    filename = os.path.basename(destination)
    stem, ext = os.path.splitext(filename)

    counter = 1
    while True:
        new_name = f"{stem} ({counter}){ext}"
        new_destination = os.path.join(directory, new_name)
        if not os.path.exists(new_destination):
            return new_destination
        counter += 1


def discover_files(source_directory: str) -> list:
    """
    Returns a list of absolute paths for all eligible files
    in the root of source_directory.

    Eligible means:
      - Is a regular file (not a directory)
      - Is not hidden or system (Windows attributes)
      - Is at root level only — no recursion

    Returns empty list if no eligible files found.
    """
    eligible = []

    try:
        entries = os.listdir(source_directory)
    except PermissionError:
        return []  # can't read the folder — return empty, caller handles it

    for entry in entries:
        full_path = os.path.join(source_directory, entry)

        # Skip subdirectories — shallow operation only
        if os.path.isdir(full_path):
            continue

        # Skip hidden and system files — Windows attribute check
        if _is_hidden_or_system(full_path):
            continue

        eligible.append(full_path)

    return eligible


# ---------------------------------------------------------------------------
# PLAN BUILDER
# Builds a complete OperationPlan from filesystem state.
# Called after validation — source is confirmed to exist.
# ---------------------------------------------------------------------------


def build_plan(source_directory: str) -> OperationPlan:
    """
    Discovers all eligible files and builds a complete OperationPlan.
    Resolves duplicate destination names deterministically.
    Returns an OperationPlan — never modifies the filesystem.

    The plan contains everything needed for preview and execution.
    No file is touched during plan building.
    """
    plan = OperationPlan(source_directory=source_directory)

    # Step 1 — discover eligible files
    files = discover_files(source_directory)

    # Step 2 — build operation for each file
    for filepath in files:
        filename = os.path.basename(filepath)
        category = _get_category(filename)

        # Destination folder = source_directory/category/
        category_folder = os.path.join(source_directory, category)

        # Destination file path before duplicate check
        raw_destination = os.path.join(category_folder, filename)

        # Resolve duplicate — returns safe name if conflict exists
        safe_destination = _resolve_duplicate(raw_destination)

        # Build the operation
        operation = FileOperation(
            source=filepath, destination=safe_destination, category=category
        )
        plan.operations.append(operation)

        # Update category count
        plan.category_counts[category] = plan.category_counts.get(category, 0) + 1

    return plan


# ---------------------------------------------------------------------------
# PLAN VALIDATOR
# Re-validates the plan after user confirmation.
# Called after CONFIRM, before first file is touched.
# If ANY operation is stale — abort entirely, nothing is modified.
# ---------------------------------------------------------------------------


def validate_plan(plan: OperationPlan) -> tuple:
    """
    Re-checks every planned operation against current filesystem state.
    Returns (True, []) if all operations are still valid.
    Returns (False, [stale_operations]) if any operation is stale.

    Stale means:
      - Source file no longer exists
      - Destination path is now occupied (conflict appeared since preview)
    """
    stale = []

    for operation in plan.operations:
        # Check source still exists
        if not os.path.isfile(operation.source):
            stale.append((operation, "SOURCE_DISAPPEARED"))
            continue

        # Check destination is still free
        # Note: we allow the category folder to not exist yet —
        # it will be created during execution
        if os.path.exists(operation.destination):
            stale.append((operation, "DESTINATION_CONFLICT"))

    if stale:
        return (False, stale)

    return (True, [])


# ---------------------------------------------------------------------------
# PLAN EXECUTOR
# Executes a validated OperationPlan with per-file feedback.
# Creates category folders before moving files.
# Collects failures without stopping — reports at end.
# ---------------------------------------------------------------------------

from executor.executor import _move_file_raw  # shared raw operation


def execute_plan(plan: OperationPlan) -> BatchResult:
    """
    Executes every operation in the plan.
    Creates category folders as needed before moving files.
    Reports per-file result in real-time via print().
    Collects failures without aborting — returns complete BatchResult.

    Assumes validate_plan() has already passed.
    """
    result = BatchResult()

    # Step 1 — create all needed category folders upfront
    # Collect unique destination folders first
    needed_folders = set(os.path.dirname(op.destination) for op in plan.operations)

    for folder in needed_folders:
        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except Exception as e:
                # If we can't create a folder, all files going there will fail
                # We continue — per-file execution will catch individual failures
                print(f"  [Warning] Could not create folder '{folder}': {e}")

    # Step 2 — execute per-file with real-time feedback
    for operation in plan.operations:
        filename = os.path.basename(operation.source)
        dest_display = os.path.basename(operation.destination)

        # Show what we're about to do
        print(f"  Moving '{filename}' → {operation.category}/", end="")

        # Show if name changed due to duplicate resolution
        if filename != dest_display:
            print(f"{dest_display}", end="")

        success, code = _move_file_raw(operation.source, operation.destination)

        if success:
            print(" ✓")
            result.succeeded.append(operation)
        else:
            print(f" ✗ ({code})")
            result.failed.append((operation, code))

    return result
