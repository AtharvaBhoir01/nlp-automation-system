# Architecture Decision Records

## ADR-001: Provider-Agnostic LLM Layer
**Decision:** Abstract base class pattern for LLM clients.
**Reason:** Enable hot-swapping between Gemini, Claude, OpenAI without 
modifying core system logic.
**Status:** Implemented

## ADR-002: Separate Path Resolution from Validation
**Decision:** path_resolver.py and validator.py are distinct modules.
**Reason:** Translation and validation are different responsibilities. 
Path resolver converts logical paths to real paths. Validator checks 
safety and correctness. Mixing them would violate SRP and make 
cross-platform support harder.
**Status:** Implemented

## ADR-003: Structured Error Codes over Formatted Strings
**Decision:** Executor returns "MOVE_SUCCESS" not "Moved file X to Y".
**Reason:** Presentation is main.py's responsibility. Status codes 
enable consistent handling across CLI, GUI, API, and tests without 
changing executor.
**Status:** Implemented

## ADR-004: Batch Schema — LLM Describes Intent, App Discovers Files
**Decision:** Batch operations schema contains filter rules, not 
actual filenames. Application resolves matching files from filesystem.
**Reason:** LLM cannot reliably enumerate real filenames. Keeping 
file discovery in application code ensures we validate against 
real filesystem state, not LLM-invented filenames.
**Status:** Planned — batch operations not yet implemented

## ADR-005: Dry Run Before Batch Execution
**Decision:** All batch operations require a preview step showing 
exact before/after for every affected file before any execution.
**Reason:** Batch mistakes multiply. A user must explicitly review 
and confirm the complete operation set before any file is touched.
**Status:** Planned