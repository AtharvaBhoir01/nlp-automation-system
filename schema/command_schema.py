# command_schema.py
# Defines the command schemas and allowed actions for the NLP Automation System


# ---------------------------------------------------------------------------
# ALLOWED ACTIONS
# The only actions the system will accept — acts as a whitelist
# ---------------------------------------------------------------------------

ALLOWED_ACTIONS = [
    "move_file",
    "rename_file",
    "create_folder",
    "organize_folder"
]


# ---------------------------------------------------------------------------
# COMMAND SCHEMAS
# Defines required parameters and confirmation rules per action
# ---------------------------------------------------------------------------

COMMAND_SCHEMAS = {
    "move_file": {
        "required_parameters": ["source", "destination"],
        "confirmation_required": True
    },
    "rename_file": {
        "required_parameters": ["source", "new_name"],
        "confirmation_required": True
    },
    "create_folder": {
        "required_parameters": ["path", "folder_name"],
        "confirmation_required": False
    },
    "organize_folder": {
        "required_parameters": ["source"],
        "confirmation_required": True
    }
}


# ---------------------------------------------------------------------------
# VALIDATOR HELPER
# Checks if a command dictionary matches the expected schema
# ---------------------------------------------------------------------------

def validate_command_structure(command: dict) -> tuple:
    """
    Checks if a parsed command dictionary has the correct structure.

    Returns a tuple: (is_valid: bool, error_message: str)
    - If valid:   (True, "")
    - If invalid: (False, "reason why")

    This does NOT check if files exist on disk — that is the executor's job.
    It only checks if the command is shaped correctly.
    """

    # CHECK 1 — Is the action one we recognise?
    action = command.get("action")
    if action not in ALLOWED_ACTIONS:
        return (False, f"Unknown action: '{action}'")

    # CHECK 2 — Does a 'parameters' block exist?
    parameters = command.get("parameters")
    if not isinstance(parameters, dict):
        return (False, "Missing or invalid 'parameters' block")

    # CHECK 3 — Are all required fields present inside parameters?
    required = COMMAND_SCHEMAS[action]["required_parameters"]
    for field in required:
        if field not in parameters:
            return (False, f"Missing required parameter: '{field}'")

    # All checks passed
    return (True, "")