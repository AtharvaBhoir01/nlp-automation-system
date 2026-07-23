# llm_client.py
# Defines the base LLM client interface and the Gemini implementation

from google import genai          # New official Gemini SDK
import json                       # Parses JSON strings into Python dicts
import os                         # Reads environment variables safely


# ---------------------------------------------------------------------------
# PROMPT TEMPLATE
# Sent to the LLM with every request — instructs it to return clean JSON only
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are a command interpreter for a file automation system.
Your job is to convert natural language instructions into structured JSON commands.

You must ONLY return a valid JSON object. No explanations, no markdown,
no code blocks, no extra text — only the raw JSON object itself.

The JSON must follow this exact structure:
{
    "action": "<action_name>",
    "parameters": {
        <action-specific fields>
    },
    "confirmation_required": <true or false>
}

Allowed actions and their required parameters:
- move_file: requires "source" and "destination" (full file paths)
- rename_file: requires "source" (full path) and "new_name" (just the filename)
- create_folder: requires "path" and "folder_name"

Rules:
- confirmation_required is true for move_file and rename_file
- confirmation_required is false for create_folder
- If the instruction is unclear or not a supported action, return:
  {"action": "unknown", "parameters": {}, "confirmation_required": false}
- Always use Windows-style file paths (backslashes)

Examples:
User: "move report.pdf from downloads to documents"
Response: {"action": "move_file", "parameters": {"source": "C:\\Users\\User\\Downloads\\report.pdf", "destination": "C:\\Users\\User\\Documents\\report.pdf"}, "confirmation_required": true}

User: "create a folder called Projects in documents"
Response: {"action": "create_folder", "parameters": {"path": "C:\\Users\\User\\Documents", "folder_name": "Projects"}, "confirmation_required": false}
"""


# ---------------------------------------------------------------------------
# BASE CLASS — The contract every LLM provider must follow
# ---------------------------------------------------------------------------

class LLMClient:
    """
    Abstract base class for all LLM clients.
    Any provider (Gemini, Claude, OpenAI) must inherit this class
    and implement the interpret() method.

    This keeps the system provider-agnostic — main.py only ever
    calls .interpret(), never anything provider-specific.
    """

    def interpret(self, user_input: str) -> dict:
        """
        Takes a natural language string.
        Returns a parsed command as a Python dictionary.
        Every subclass MUST implement this — it is not optional.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement the interpret() method"
        )


# ---------------------------------------------------------------------------
# GEMINI IMPLEMENTATION
# Concrete implementation of LLMClient using Google's new google-genai SDK
# ---------------------------------------------------------------------------

class GeminiClient(LLMClient):
    """
    LLM client implementation using Google's Gemini API (google-genai SDK).
    Reads the API key from environment variables — never hardcoded.
    To swap to Claude later: create ClaudeClient(LLMClient) and
    implement interpret(). Nothing else in the system needs to change.
    """

    def __init__(self):
        """
        Initialises the Gemini client.
        Reads API key from environment — raises a clear error if missing.
        """
        # Read API key from environment — never hardcode secrets in code
        api_key = os.environ.get("GEMINI_API_KEY")

        # If the key is missing, stop immediately with a helpful message
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Run: setx GEMINI_API_KEY your-key-here"
            )

        # Initialise the new google-genai client with our API key
        self.client = genai.Client(api_key=api_key)

    def interpret(self, user_input: str) -> dict:
        """
        Sends user's natural language input to Gemini.
        Returns a parsed Python dictionary of the structured command.

        Raises ValueError if Gemini returns something that isn't valid JSON.
        """
        # Send the user message to Gemini with our system prompt
        response = self.client.models.generate_content(
            model="gemini-3.1-flash-lite",       # current stable free-tier model
            contents=user_input,
            config={
                "system_instruction": SYSTEM_PROMPT
            }
        )

        # Pull out the raw text and strip whitespace
        raw_text = response.text.strip()

        # Try to parse as JSON — fail clearly if it doesn't work
        try:
            command = json.loads(raw_text)
            return command

        except json.JSONDecodeError:
            raise ValueError(
                f"Gemini returned a non-JSON response:\n{raw_text}"
            )