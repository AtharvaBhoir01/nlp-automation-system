# NLP Automation System

> **Control your computer with natural language.**  
> Type plain English — the system figures out the file operation and executes it safely.

```
You: move report.pdf from downloads to documents
→ Parsing intent...
→ Resolving paths...
→ Preview: C:\Users\LENOVO\OneDrive\Downloads\report.pdf
         → C:\Users\LENOVO\OneDrive\Documents\report.pdf
Confirm? (yes/no): yes
✓ Done.
```

---

## What It Does

| Command | Example |
|---|---|
| Move a file | `move report.pdf from downloads to documents` |
| Rename a file | `rename notes.txt to final_notes.txt on desktop` |
| Create a folder | `create a folder called Projects in documents` |
| Organize a folder | `organize my downloads folder` |

The organize command scans a folder and sorts every file into category subfolders — PDFs, Images, Videos, Code, Archives, Documents, Audio, Other — with a dry-run preview before touching anything.

---

## Architecture

```
User Input (plain English)
        ↓
  LLM Interpreter           ← Gemini API → structured JSON command
        ↓
  Schema Validator          ← checks required fields, allowed actions
        ↓
  Path Resolver             ← "downloads" → C:\Users\...\OneDrive\Downloads
        ↓
  Semantic Validator        ← source exists? destination safe? no traversal?
        ↓
  Confirmation Gate         ← shows exact paths, waits uppercase "CONFIRM" confirmation 
        ↓
  Execution Engine          ← shutil.move, os.rename, os.makedirs
        ↓
  Logger                    ← appends to logs/commands.log
```

Every stage is a separate module. A failure at any stage aborts cleanly with a specific error code — no partial operations, no silent failures.

---

## Engineering Decisions

**1. Provider-agnostic LLM layer**  
`LLMClient` is an abstract base class. `GeminiClient` is one implementation. Switching to Claude API or any other LLM requires adding one new class — nothing else changes.

**2. Separate path resolution from validation**  
`path_resolver.py` is a pure translation layer: "downloads" → real path. `validator.py` is a safety layer: does the path exist, is it dangerous, is it trying a traversal attack? Single Responsibility Principle — each module has one job.

**3. Structured error codes, not formatted strings**  
Executors return codes like `SOURCE_NOT_FOUND`, `PERMISSION_DENIED`, `SAME_PATH`. The presentation layer in `main.py` owns all user-facing messages. This means the logic and the display are never coupled.

**4. Batch operations: LLM describes intent, Python discovers files**  
For `organize_folder`, the LLM only returns `{"action": "organize_folder", "source": "downloads"}`. Python's `discover_files()` does the actual filesystem scan. The LLM never guesses filenames.

**5. Post-confirmation re-validation**  
After the user confirms a batch plan, `validate_plan()` re-checks every source file before touching anything. If even one file has disappeared since the preview, the entire batch is aborted. The confirmation applies to the exact plan shown — not a best-effort approximation of it.

See [`DECISIONS.md`](DECISIONS.md) for the full Architecture Decision Record (11 ADRs).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| LLM | Google Gemini (`google-genai` SDK) |
| File ops | `shutil`, `os`, `pathlib` |
| Hidden file detection | `ctypes.windll.kernel32` (Windows API) |
| Testing | `unittest`, `unittest.mock`, `tempfile` |
| Logging | Python `logging` module |

---

## Project Structure

```
nlp-automation/
├── main.py                  # Entry point, CLI loop, orchestration
├── interpreter/
│   └── llm_client.py        # Abstract LLMClient + GeminiClient
├── schema/
│   └── command_schema.py    # ALLOWED_ACTIONS, COMMAND_SCHEMAS, validate_command_structure()
├── resolver/
│   └── path_resolver.py     # Placeholder → real path translation (OneDrive-aware)
├── validator/
│   └── validator.py         # Semantic safety checks, structured error codes
├── executor/
│   └── executor.py          # File operations, returns status codes only
├── batch/
│   └── organizer.py         # discover_files, build_plan, validate_plan, execute_plan
├── logs/
│   └── commands.log         # Append-only execution log (gitignored)
├── tests/
│   ├── test_schema.py       # 16 tests — schema validation
│   └── test_organizer.py    # 46 tests — batch pipeline (unit + integration)
└── DECISIONS.md             # 11 Architecture Decision Records
```

---

## Run Locally

```bash
git clone https://github.com/AtharvaBhoir01/nlp-automation-system.git
cd nlp-automation-system
pip install google-genai
```

Set your Gemini API key (Windows):
```
setx GEMINI_API_KEY "your-key-here"
```
Then open a new terminal and run:
```bash
python main.py
```

---

## Run Tests

```bash
python -m unittest tests/test_schema.py -v
python -m unittest tests/test_organizer.py -v
```

62 tests, 0 failures.

---

## Known Limitations

- **Windows only** — path resolution and hidden-file detection use Windows APIs
- **Shallow organize** — `organize_folder` scans one level deep, not recursive
- **No undo** — moves are permanent; no rollback mechanism
- **LLM latency** — each command takes few seconds for the Gemini round-trip
- **Free-tier quota** — Gemini free tier has rate limits; heavy use may hit them

---

## Status

MVP complete. All core commands working end-to-end on Windows with OneDrive.  
62 passing tests across schema validation and batch pipeline.

> Built as a placement project to demonstrate real system design: safety-first pipeline architecture, separation of concerns, structured error handling, and test-driven development.
