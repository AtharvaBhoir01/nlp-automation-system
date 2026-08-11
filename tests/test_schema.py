# test_schema.py
# Automated tests for the command schema validation system.
# Tests validate_command_structure() across valid commands,
# invalid commands, and edge cases.
# Run with: python -m pytest tests/ or python -m unittest tests/test_schema.py

import unittest

# Import the function we're testing
from schema.command_schema import validate_command_structure


class TestValidCommandStructure(unittest.TestCase):
    """
    Tests for commands that should pass validation.
    These represent the happy path — correctly formed commands.
    """

    def test_valid_move_file(self):
        """A complete, correctly structured move_file command."""
        command = {
            "action": "move_file",
            "parameters": {
                "source": "C:\\Users\\LENOVO\\Desktop\\test.txt",
                "destination": "C:\\Users\\LENOVO\\Documents\\test.txt"
            },
            "confirmation_required": True
        }
        result = validate_command_structure(command)
        self.assertEqual(result, (True, ""))

    def test_valid_rename_file(self):
        """A complete, correctly structured rename_file command."""
        command = {
            "action": "rename_file",
            "parameters": {
                "source": "C:\\Users\\LENOVO\\Desktop\\test.txt",
                "new_name": "test_renamed.txt"
            },
            "confirmation_required": True
        }
        result = validate_command_structure(command)
        self.assertEqual(result, (True, ""))

    def test_valid_create_folder(self):
        """A complete, correctly structured create_folder command."""
        command = {
            "action": "create_folder",
            "parameters": {
                "path": "C:\\Users\\LENOVO\\Documents",
                "folder_name": "TestFolder"
            },
            "confirmation_required": False
        }
        result = validate_command_structure(command)
        self.assertEqual(result, (True, ""))


class TestInvalidAction(unittest.TestCase):
    """
    Tests for commands with invalid or missing actions.
    """

    def test_unsupported_action(self):
        """Actions not in ALLOWED_ACTIONS must be rejected."""
        command = {
            "action": "delete_file",
            "parameters": {
                "source": "C:\\Users\\LENOVO\\Desktop\\test.txt"
            },
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)
        self.assertIn("delete_file", error)

    def test_missing_action_key(self):
        """Command with no action key at all."""
        command = {
            "parameters": {
                "source": "C:\\Users\\LENOVO\\Desktop\\test.txt"
            }
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)

    def test_unknown_action_string(self):
        """The 'unknown' fallback action from LLM must be rejected."""
        command = {
            "action": "unknown",
            "parameters": {},
            "confirmation_required": False
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)
        self.assertIn("unknown", error)


class TestInvalidParameters(unittest.TestCase):
    """
    Tests for commands with missing or malformed parameters.
    """

    def test_missing_parameters_block(self):
        """Command with no parameters key at all."""
        command = {
            "action": "move_file",
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)
        self.assertIn("parameters", error.lower())

    def test_parameters_is_none(self):
        """Parameters key exists but value is None."""
        command = {
            "action": "move_file",
            "parameters": None,
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)

    def test_missing_destination_in_move_file(self):
        """move_file missing its destination parameter."""
        command = {
            "action": "move_file",
            "parameters": {
                "source": "C:\\Users\\LENOVO\\Desktop\\test.txt"
                # destination deliberately missing
            },
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)
        self.assertIn("destination", error)

    def test_missing_source_in_rename_file(self):
        """rename_file missing its source parameter."""
        command = {
            "action": "rename_file",
            "parameters": {
                "new_name": "test_renamed.txt"
                # source deliberately missing
            },
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)
        self.assertIn("source", error)

    def test_missing_folder_name_in_create_folder(self):
        """create_folder missing its folder_name parameter."""
        command = {
            "action": "create_folder",
            "parameters": {
                "path": "C:\\Users\\LENOVO\\Documents"
                # folder_name deliberately missing
            },
            "confirmation_required": False
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)
        self.assertIn("folder_name", error)


class TestEdgeCases(unittest.TestCase):
    """
    Edge cases that could break the system in unexpected ways.
    """

    def test_empty_command(self):
        """Completely empty dictionary."""
        command = {}
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)

    def test_empty_parameters_block(self):
        """Parameters key exists but is an empty dict."""
        command = {
            "action": "move_file",
            "parameters": {},
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)
        # Should fail on missing required fields, not on empty dict itself
        self.assertIn("source", error)

    def test_extra_unexpected_parameters(self):
        """
        Extra parameters beyond what's required.
        System should still pass — extra fields are ignored.
        Strict rejection of extra fields would break forward compatibility.
        """
        command = {
            "action": "move_file",
            "parameters": {
                "source": "C:\\Users\\LENOVO\\Desktop\\test.txt",
                "destination": "C:\\Users\\LENOVO\\Documents\\test.txt",
                "unexpected_field": "some_value"  # extra — should be ignored
            },
            "confirmation_required": True
        }
        result = validate_command_structure(command)
        self.assertEqual(result, (True, ""))

    def test_action_is_wrong_type(self):
        """Action field is an integer instead of a string."""
        command = {
            "action": 123,
            "parameters": {
                "source": "C:\\Users\\LENOVO\\Desktop\\test.txt",
                "destination": "C:\\Users\\LENOVO\\Documents\\test.txt"
            },
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)

    def test_parameters_is_a_list(self):
        """Parameters is a list instead of a dict — wrong type entirely."""
        command = {
            "action": "move_file",
            "parameters": ["source", "destination"],
            "confirmation_required": True
        }
        is_valid, error = validate_command_structure(command)
        self.assertFalse(is_valid)


# ---------------------------------------------------------------------------
# ENTRY POINT
# Runs all tests when file is executed directly: python tests/test_schema.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)