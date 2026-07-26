# main.py
# Entry point for the NLP Automation System — handles the CLI input/output loop

import os  # Used to read environment variables

# Import our three core modules
from interpreter.llm_client import GeminiClient, LLMClient
from schema.command_schema import validate_command_structure
from resolver.path_resolver import resolve_command_paths
from validator.validator import validate_command


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


def run_cli(client: LLMClient) -> None:
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
            continue    

        except Exception as e:
            # Catch-all for API-level errors — quota, network, auth, etc.
            # We check the string because ClientError isn't easily importable
            error_str = str(e)    
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print("\n[Service Error] Gemini quota or rate limit reached.")
                print("Please wait a moment and try again, or check your API quota at https://ai.dev/rate-limit")
            else:
                print(f"\n[Service Error] Unexpected API error: {e}")
            continue

        # STEP 2 — Validate the command structure against our schema
        is_valid, error_message = validate_command_structure(command)

        if not is_valid:
            # Command parsed as JSON but doesn't match our schema rules
            print(f"\n[Validation Error] {error_message}")
            continue

        # STEP 2.5 — Resolve placeholder paths to real system paths
        command = resolve_command_paths(command)

        # STEP 3 — Semantic validation
        is_valid, error_message = validate_command(command)
        if not is_valid:
            print(f"\n[Validation Error] {error_message}")
            continue

        # Non-blocking warning — print but continue
        if error_message:
            print(f"\n[Warning] {error_message}")

        # STEP 4 — Display
        print_command(command)
        print("[Preview only — execution not implemented yet]\n")        


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

    # Hand off to the CLI loop
    run_cli(client)


# ---------------------------------------------------------------------------
# ENTRY POINT GUARD
# This block only runs if you execute this file directly with:
#   python main.py
# It does NOT run if another file imports main.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()