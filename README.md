# NLP Automation System

A Natural Language Programming Interface for performing computer file-system
operations using plain English.

The system converts natural-language instructions into structured commands,
validates them through multiple safety layers, resolves system-specific paths,
asks for confirmation when required, executes the operation, and records the
result through centralized logging.

---

## Project Goal

The goal is to explore how natural language can be used as an interface for
computer automation, particularly for users who may not be comfortable with
command-line tools or scripting.

Instead of using commands such as:

```text
move file.pdf C:\Users\User\Documents\
```

the user can simply provide:

```text
move file.pdf from desktop to documents
```

The system interprets the instruction and safely converts it into a structured
file-system operation.

---

## Current Status

### MVP Complete ✅

The core pipeline is fully implemented and tested.

- Natural-language command interpretation
- Provider-agnostic LLM integration
- JSON command schema
- Structural/schema validation
- Runtime path resolution
- OneDrive-aware common-location detection
- Semantic and safety validation
- User confirmation for destructive operations
- File execution engine
- Centralized operational logging
- Automated schema tests

**Test status: 16/16 tests passing**

---

## Architecture

```text
User
 │
 ▼
main.py
 │
 ▼
LLM Interpretation
interpreter/
 │
 ▼
Schema Validation
schema/
 │
 ▼
Path Resolution
resolver/
 │
 ▼
Semantic Validation
validator/
 │
 ▼
Confirmation
 │
 ▼
Execution
executor/
 │
 ▼
File System
 │
 ▼
Logging
logs/
```

Each module has a separate responsibility, following a modular architecture
and the Single Responsibility Principle.

---

## Supported Operations

### Move File

```text
move test.txt from desktop to documents
```

### Rename File

```text
rename test.txt to test_renamed.txt on desktop
```

### Create Folder

```text
create a folder called TestFolder in documents
```

These operations form the controlled foundation of the MVP. The long-term goal
is to support more complex natural-language automation tasks.

---

## Safety Pipeline

The LLM does **not** directly execute file-system operations.

Commands pass through multiple layers:

```text
Natural Language
      ↓
LLM Interpretation
      ↓
Schema Validation
      ↓
Path Resolution
      ↓
Semantic & Safety Validation
      ↓
User Confirmation
      ↓
Execution
```

### Schema Validation

Checks whether the generated command is structurally valid:

- Supported action
- Required parameters
- Correct command structure
- Valid parameter types

### Path Resolution

Detects the user's actual system paths instead of relying on hardcoded
usernames or assumed OneDrive configuration.

Common locations such as Desktop and Documents are checked individually so the
resolver can handle standard Windows and OneDrive-based setups.

### Semantic Validation

Checks conditions such as:

- Source existence
- Destination validity
- Dangerous system locations
- Directory traversal attempts
- Illegal characters
- Source/destination conflicts
- Extension-change warnings

### Confirmation

Destructive operations such as moving and renaming files require explicit
user confirmation before execution.

---

## Provider-Agnostic LLM Architecture

The LLM integration is designed around an abstraction layer:

```text
              LLMClient
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
   GeminiClient ClaudeClient OpenAIClient
```

The core pipeline communicates through the common interface, allowing the LLM
provider to be changed without modifying the schema, resolver, validator, or
executor layers.

The current implementation uses Google's Gemini API.

---

## Execution Engine

The executor performs the actual file-system operations using Python's
standard library:

```text
move_file     → shutil.move()
rename_file   → os.rename()
create_folder → os.makedirs()
```

The executor returns concise status codes rather than user-facing messages,
keeping execution logic separate from presentation.

Examples:

```text
MOVE_SUCCESS
RENAME_SUCCESS
CREATE_SUCCESS
PERMISSION_DENIED
OS_ERROR
ALREADY_EXISTS
```

---

## Logging

The project uses Python's built-in `logging` module.

Operational events are recorded in:

```text
logs/commands.log
```

The log records timestamps, log levels, and operation results.

Runtime logs are excluded from Git because they may contain machine-specific
paths and local system information.

---

## Testing

Automated tests use Python's built-in `unittest` framework.

Run the tests with:

```bash
python -m unittest tests/test_schema.py -v
```

Current result:

```text
16 tests
16 passed
0 failures
```

Tests cover:

- Valid commands
- Unsupported actions
- Missing fields
- Invalid parameter structures
- Invalid parameter types
- Empty commands
- Extra parameters
- Edge cases

The tests provide regression protection when the system is modified or
extended.

---

## Known Limitation

The system validates whether an operation is technically and semantically safe,
but it cannot always prove that the interpreted command matches the user's
exact intention.

For example, if multiple files have the same name:

```text
Desktop\test.txt
Desktop\TestFolder\test.txt
```

and the user says:

```text
move test.txt to documents
```

the LLM may select one valid path even though the user intended the other.

The operation could therefore pass every technical validation layer while
still producing an unintended result.

A future enhancement is a semantic disambiguation layer that can detect
multiple possible matches and ask the user to select the intended file.

---

## Future Direction

The MVP establishes the core natural-language automation engine.

Future development will be driven by **real user problems rather than feature
count**.

Potential directions include:

- Semantic file disambiguation
- Natural-language file search
- Bulk file operations
- Automated folder organization
- Multi-step automation plans
- Additional computer automation capabilities
- Alternative user interfaces beyond CLI
- Additional LLM providers

These are planned directions and are **not currently implemented**.

The long-term goal is to evolve from simple file operations into a broader
natural-language automation engine capable of safely handling complex,
multi-step computer tasks.

---

## Technology Stack

- **Language:** Python 3
- **LLM:** Google Gemini API
- **SDK:** `google-genai`
- **Testing:** `unittest`
- **Version Control:** Git & GitHub
- **Interface:** Command Line Interface
- **Standard Library:** `os`, `shutil`, `json`, `logging`

---

## Design Principles

- Separation of concerns
- Single Responsibility Principle
- Provider-agnostic architecture
- Layered validation
- Defensive programming
- Explicit confirmation for destructive operations
- Structured status/error codes
- Modular and extensible design
- Automated regression testing

---

## Status

```text
MVP: COMPLETE ✅

Core pipeline:       COMPLETE
Execution engine:    COMPLETE
Logging:             COMPLETE
Automated tests:     COMPLETE
Tests passing:       16/16
```

The next development milestone will begin with use-case analysis to identify
the highest-value real-world automation capability to build next.
