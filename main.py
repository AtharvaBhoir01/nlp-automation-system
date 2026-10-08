# main.py
# Entry point for the NLP Automation System — handles the CLI input/output loop

import os  # Used to read environment variables
import logging  # needed for the type hint in run_cli signature

# Import our three core modules
from interpreter.llm_client import GeminiClient, LLMClient
from schema.command_schema import validate_command_structure
from resolver.path_resolver import resolve_command_paths
from validator.validator import validate_command
from executor.executor import execute_command
from logs.logger import get_logger
from batch.organizer import build_plan, validate_plan, execute_plan, OperationPlan


def print_command(command: dict) -> None:
    """
    Prints a parsed command dictionary in a clean, readable format.
    Keeps display logic separate from parsing logic.
    """
    print("\n--- Parsed Command ---")
    print(f"  Action      : {command.get('action')}")
    print(f"  Parameters  : {command.get('parameters')}")
    print(f"  Confirmation: {command.get('confirmation_required')}")
    print("----------------------")

def _handle_organize_folder(command: dict, logger) -> None:
    """
    Handles the full organize_folder batch flow.
    Separated from run_cli() to keep the main loop readable.
    """
    source = command.get("parameters", {}).get("source", "")

    # Build the plan — filesystem discovery happens here
    print("\nScanning folder...")
    plan = build_plan(source)

    if not plan.operations:
        print("[Info] No eligible files found to organize.\n")
        logger.info("organize_folder | NO_FILES_FOUND")
        return

    # Display preview
    _display_organize_preview(plan)

    # Confirmation
    confirm = input(
        f"\nType CONFIRM (uppercase) to organize {len(plan.operations)} files,"
        f" or anything else to cancel: "
    ).strip()

    if confirm != "CONFIRM":
        print("Cancelled — no files were moved.\n")
        logger.info("organize_folder | CANCELLED")
        return

    # Re-validate after confirmation
    print("\nRe-validating plan...")
    is_valid, stale = validate_plan(plan)

    if not is_valid:
        print("\n[Abort] Filesystem changed since preview was generated.")
        print("The following operations are no longer valid:")
        for operation, reason in stale:
            print(f"  {os.path.basename(operation.source)} — {reason}")
        print("\nPlease run the command again to generate a fresh plan.\n")
        logger.warning(
            f"organize_folder | PLAN_STALE | {len(stale)} operations invalidated"
        )
        return

    # Execute
    print("\nOrganizing files...\n")
    result = execute_plan(plan)

    # Summary
    print(f"\n{'─' * 40}")
    print(f"  Organized : {result.success_count}/{result.total} files")

    if result.failure_count > 0:
        print(f"  Failed    : {result.failure_count} files")
        for operation, code in result.failed:
            print(
                f"    ✗ {os.path.basename(operation.source)} — {code}"
            )

    print(f"{'─' * 40}\n")

    logger.info(
        f"organize_folder | SUCCESS:{result.success_count}"
        f" FAILED:{result.failure_count}"
    )


def _display_organize_preview(plan: OperationPlan) -> None:
    """
    Displays the operation plan before confirmation.
    ≤20 files: full file-by-file preview
    >20 files: category summary with option to expand
    """
    PREVIEW_THRESHOLD = 20

    print(f"\n--- Organize Preview ---")
    print(f"  Source : {plan.source_directory}")
    print(f"  Files  : {len(plan.operations)}")
    print(f"  Categories:")
    for category, count in sorted(plan.category_counts.items()):
        print(f"    {category:<15} {count} file(s)")

    if len(plan.operations) <= PREVIEW_THRESHOLD:
        # Full detail
        print(f"\n  Planned operations:")
        for op in plan.operations:
            source_name = os.path.basename(op.source)
            dest_name = os.path.basename(op.destination)
            if source_name != dest_name:
                # Name changed due to duplicate resolution — show both
                print(f"    {source_name} → {op.category}/{dest_name} ⚠ renamed")
            else:
                print(f"    {source_name} → {op.category}/")
    else:
        # Summary with expand option
        expand = input(
            f"\n  {len(plan.operations)} files found."
            f" Show full list? (yes/no): "
        ).strip().lower()

        if expand in ("yes", "y"):
            print(f"\n  Planned operations:")
            for op in plan.operations:
                source_name = os.path.basename(op.source)
                dest_name = os.path.basename(op.destination)
                if source_name != dest_name:
                    print(
                        f"    {source_name} → {op.category}/{dest_name} ⚠ renamed"
                    )
                else:
                    print(f"    {source_name} → {op.category}/")

    print(f"{'─' * 40}")

def run_cli(client: LLMClient, logger: logging.Logger) -> None:
    """
    The main CLI loop.
    Accepts user input, interprets it, validates it, and displays the result.
    Runs until the user types 'exit' or 'quit'.

    Takes a client object — any LLMClient subclass works here.
    This is provider-agnostic design in action.
    """
    print("\n NLP Automation System")
    print("Type a file command in plain English.")
    print("Type 'exit' to quit.\n")

    while True:
        # Get input from the user
        user_input = input("You: ").strip()

        # Allow graceful exit
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            logger.info("Session ended")
            break

        # Skip empty input
        if not user_input:
            continue

        # STEP 1 — Send to LLM and get structured command back
        try:
            command = client.interpret(user_input)

        except ValueError as e:
            # Gemini returned something we couldn't parse as JSON
            print(f"\n[Interpreter Error] {e}")
            logger.error(f"interpreter_error | {e}")
            continue    

        except Exception as e:
            # Catch-all for API-level errors — quota, network, auth, etc.
            # We check the string because ClientError isn't easily importable
            error_str = str(e)    
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print("\n[Service Error] Gemini quota or rate limit reached.")
                print("Please wait a moment and try again, or check your API quota at https://ai.dev/rate-limit")
                logger.warning(f"service_error | QUOTA_EXHAUSTED")
            else:
                print(f"\n[Service Error] Unexpected API error: {e}")
                logger.error(f"service_error | {e}")
            continue

        # STEP 2 — Validate the command structure against our schema
        is_valid, error_message = validate_command_structure(command)

        if not is_valid:
            # Command parsed as JSON but doesn't match our schema rules
            print(f"\n[Validation Error] {error_message}")
            logger.warning(f"schema_validation_failed | {error_message}")
            continue

        # STEP 2.5 — Resolve placeholder paths to real system paths
        command = resolve_command_paths(command)

        # STEP 3 — Semantic validation
        is_valid, error_message = validate_command(command)
        if not is_valid:
            print(f"\n[Validation Error] {error_message}")
            logger.warning(f"semantic_validation_failed | {error_message}")
            continue

        # Non-blocking warning — print but continue
        if error_message:
            print(f"\n[Warning] {error_message}")

        # STEP 4 — Route by action type
        action = command.get("action")

        if action == "organize_folder":        
            _handle_organize_folder(command, logger)
        else:
            # STEP 5 — Display preview
            print_command(command)

            # STEP 6 — Confirmation gate
            if command.get("confirmation_required"):
                confirm = input("Confirm execution? (yes/no): ").strip().lower()
                if confirm not in ("yes", "y"):
                    print("Command cancelled.\n")
                    continue

            # STEP 7 — Execute
            success, status_code = execute_command(command)
            parameters = command.get("parameters", {})

            if success:
                # main.py formats the success message using command data
                if status_code == "MOVE_SUCCESS":
                    print(f"\n[Success] Moved '{parameters.get('source')}'"
                          f" → '{parameters.get('destination')}'\n")

                elif status_code == "RENAME_SUCCESS":
                    print(f"\n[Success] Renamed '{parameters.get('source')}'"
                          f" → '{parameters.get('new_name')}'\n")

                elif status_code == "CREATE_SUCCESS":
                    print(f"\n[Success] Created folder"
                          f" '{parameters.get('folder_name')}'"
                          f" in '{parameters.get('path')}'\n")

                logger.info(f"{command.get('action')} | {status_code}")

            else:
                # main.py formats the error message from the status code
                error_messages = {
                    "PERMISSION_DENIED": "Permission denied — check file access rights",
                    "OS_ERROR":          "OS error — file may be in use by another process",
                    "ALREADY_EXISTS":    "Already exists — no action taken",
                    "UNEXPECTED_ERROR":  "Unexpected error — check system logs",
                    "UNKNOWN_ACTION":    "Unknown action — no executor available"
                }
                reason = error_messages.get(status_code, status_code)
                print(f"\n[Execution Error] {reason}\n")  

                logger.error(f"{command.get('action')} | {status_code}")      

                


def main():
    """
    Initialises the system and starts the CLI loop.
    All setup happens here — run_cli() stays clean and focused.
    """
    # Initialise the Gemini client
    # If the API key is missing, this raises a clear ValueError and stops
    try:
        client = GeminiClient()
    except ValueError as e:
        print(f"\n[Setup Error] {e}")
        return  # exit cleanly — no point continuing without a client

    # Initialise logger — shared across the session
    logger = get_logger()
    logger.info("Session started")


    # Hand off to the CLI loop
    run_cli(client, logger)  # pass logger into run_cli


# ---------------------------------------------------------------------------
# ENTRY POINT GUARD
# This block only runs if you execute this file directly with:
#   python main.py
# It does NOT run if another file imports main.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()