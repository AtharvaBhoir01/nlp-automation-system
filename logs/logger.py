# logger.py
# Logging configuration for the NLP Automation System.
# Centralises all logging setup — import get_logger() wherever logging is needed.
# Keeps logging configuration out of business logic modules.

import logging
import os

# ---------------------------------------------------------------------------
# LOG FILE PATH
# Resolves the path to commands.log relative to this file's location.
# This works correctly regardless of where main.py is run from.
# ---------------------------------------------------------------------------

# __file__ is the path to logger.py itself
# dirname() gets the logs/ folder
# join() builds the full path to commands.log
LOG_FILE = os.path.join(os.path.dirname(__file__), "commands.log")


# ---------------------------------------------------------------------------
# LOGGER SETUP
# ---------------------------------------------------------------------------

def get_logger(name: str = "nlp_automation") -> logging.Logger:
    """
    Creates and returns a configured logger instance.
    Safe to call multiple times — returns the same logger if already configured.

    Args:
        name: Logger name — use module name for future distributed logging.
              Defaults to 'nlp_automation' for centralised use.

    Returns:
        A configured Logger instance writing to both file and console.
    """
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger() is called more than once
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # capture everything — handlers filter level

    # -----------------------------------------------------------------------
    # FILE HANDLER — writes to logs/commands.log
    # mode="a" means append — never overwrites previous sessions
    # -----------------------------------------------------------------------
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # log everything to file

    # -----------------------------------------------------------------------
    # FORMAT
    # Example output:
    # 2026-07-27 14:32:01 | INFO     | move_file | MOVE_SUCCESS
    # -----------------------------------------------------------------------
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)

    # Attach handler to logger
    logger.addHandler(file_handler)

    return logger