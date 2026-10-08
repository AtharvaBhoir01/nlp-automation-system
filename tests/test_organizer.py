# test_organizer.py
# Automated tests for the batch file organization engine.
# Tests cover: categorization, duplicate resolution, file discovery,
# plan building, plan validation, and batch execution.
# Uses tempfile.TemporaryDirectory() — never touches real user files.
# Run with: python -m unittest tests/test_organizer.py -v

import unittest
import os
import tempfile
from unittest.mock import patch

from batch.organizer import (
    _get_category,
    _resolve_duplicate,
    discover_files,
    build_plan,
    validate_plan,
    execute_plan,
    FileOperation,
    OperationPlan,
    BatchResult,
)

class TestGetCategory(unittest.TestCase):
    """
    Tests for extension-to-category mapping.
    _get_category() is pure logic — no filesystem involved.
    """

    def test_pdf_maps_to_pdfs(self):
        self.assertEqual(_get_category("report.pdf"), "PDFs")

    def test_docx_maps_to_documents(self):
        self.assertEqual(_get_category("notes.docx"), "Documents")

    def test_xlsx_maps_to_documents(self):
        self.assertEqual(_get_category("budget.xlsx"), "Documents")

    def test_pptx_maps_to_documents(self):
        self.assertEqual(_get_category("slides.pptx"), "Documents")

    def test_txt_maps_to_documents(self):
        self.assertEqual(_get_category("readme.txt"), "Documents")

    def test_jpg_maps_to_images(self):
        self.assertEqual(_get_category("photo.jpg"), "Images")

    def test_png_maps_to_images(self):
        self.assertEqual(_get_category("screenshot.png"), "Images")

    def test_mp3_maps_to_audio(self):
        self.assertEqual(_get_category("song.mp3"), "Audio")

    def test_wav_maps_to_audio(self):
        self.assertEqual(_get_category("recording.wav"), "Audio")

    def test_mp4_maps_to_videos(self):
        self.assertEqual(_get_category("clip.mp4"), "Videos")

    def test_zip_maps_to_archives(self):
        self.assertEqual(_get_category("backup.zip"), "Archives")

    def test_rar_maps_to_archives(self):
        self.assertEqual(_get_category("data.rar"), "Archives")

    def test_py_maps_to_code(self):
        self.assertEqual(_get_category("script.py"), "Code")

    def test_js_maps_to_code(self):
        self.assertEqual(_get_category("app.js"), "Code")

    def test_json_maps_to_code(self):
        self.assertEqual(_get_category("config.json"), "Code")

    def test_unknown_extension_maps_to_other(self):
        self.assertEqual(_get_category("file.xyz"), "Other")

    def test_no_extension_maps_to_other(self):
        self.assertEqual(_get_category("README"), "Other")

    def test_uppercase_extension_normalized(self):
        """Case-insensitive — .PDF must map same as .pdf"""
        self.assertEqual(_get_category("report.PDF"), "PDFs")

    def test_mixed_case_extension_normalized(self):
        self.assertEqual(_get_category("photo.JPG"), "Images")

class TestResolveDuplicate(unittest.TestCase):
    """
    Tests for deterministic duplicate-safe destination naming.
    Uses temporary directories — no real files touched.
    """

    def setUp(self):
        """
        setUp() runs before every test method in this class.
        Creates a fresh temporary directory for each test.
        """
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp.name

    def tearDown(self):
        """
        tearDown() runs after every test method.
        Cleans up the temporary directory automatically.
        """
        self.tmp.cleanup()

    def _make_file(self, filename: str) -> str:
        """Helper — creates an empty file in the temp directory."""
        path = os.path.join(self.tmp_path, filename)
        open(path, 'w').close()
        return path

    def test_no_conflict_returns_original(self):
        """If destination doesn't exist, return it unchanged."""
        destination = os.path.join(self.tmp_path, "report.pdf")
        result = _resolve_duplicate(destination)
        self.assertEqual(result, destination)

    def test_single_conflict_returns_1(self):
        """If destination exists, return name with (1)."""
        self._make_file("report.pdf")
        destination = os.path.join(self.tmp_path, "report.pdf")
        result = _resolve_duplicate(destination)
        expected = os.path.join(self.tmp_path, "report (1).pdf")
        self.assertEqual(result, expected)

    def test_two_conflicts_returns_2(self):
        """If (1) also exists, return (2)."""
        self._make_file("report.pdf")
        self._make_file("report (1).pdf")
        destination = os.path.join(self.tmp_path, "report.pdf")
        result = _resolve_duplicate(destination)
        expected = os.path.join(self.tmp_path, "report (2).pdf")
        self.assertEqual(result, expected)

    def test_multiple_conflicts_finds_next_available(self):
        """Counter increments until a free name is found."""
        self._make_file("report.pdf")
        self._make_file("report (1).pdf")
        self._make_file("report (2).pdf")
        self._make_file("report (3).pdf")
        destination = os.path.join(self.tmp_path, "report.pdf")
        result = _resolve_duplicate(destination)
        expected = os.path.join(self.tmp_path, "report (4).pdf")
        self.assertEqual(result, expected)

    def test_extension_preserved_in_duplicate(self):
        """Extension must stay at the end after counter insertion."""
        self._make_file("photo.jpg")
        destination = os.path.join(self.tmp_path, "photo.jpg")
        result = _resolve_duplicate(destination)
        self.assertTrue(result.endswith(".jpg"))
        self.assertIn("(1)", result)

class TestDiscoverFiles(unittest.TestCase):
    """
    Tests for filesystem discovery — shallow, filtered.
    Uses temporary directories with controlled file structure.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _make_file(self, filename: str) -> str:
        path = os.path.join(self.tmp_path, filename)
        open(path, 'w').close()
        return path

    def _make_subdir(self, dirname: str) -> str:
        path = os.path.join(self.tmp_path, dirname)
        os.makedirs(path)
        return path

    def test_discovers_root_level_files(self):
        """Files at root level are discovered."""
        self._make_file("report.pdf")
        self._make_file("photo.jpg")
        result = discover_files(self.tmp_path)
        filenames = [os.path.basename(f) for f in result]
        self.assertIn("report.pdf", filenames)
        self.assertIn("photo.jpg", filenames)

    def test_ignores_subdirectories(self):
        """Directories are never included in results."""
        self._make_subdir("PDFs")
        result = discover_files(self.tmp_path)
        for path in result:
            self.assertTrue(
                os.path.isfile(path),
                f"Expected only files but found directory: {path}"
            )

    def test_ignores_files_inside_subdirectories(self):
        """Files inside subdirectories are not discovered — shallow only."""
        subdir = self._make_subdir("SubFolder")
        nested_file = os.path.join(subdir, "nested.pdf")
        open(nested_file, 'w').close()
        result = discover_files(self.tmp_path)
        result_names = [os.path.basename(f) for f in result]
        self.assertNotIn("nested.pdf", result_names)

    def test_empty_directory_returns_empty_list(self):
        """No files → empty list, not an error."""
        result = discover_files(self.tmp_path)
        self.assertEqual(result, [])

    def test_includes_unknown_extensions(self):
        """Files with unknown extensions are included — categorized as Other."""
        self._make_file("mystery.xyz")
        result = discover_files(self.tmp_path)
        filenames = [os.path.basename(f) for f in result]
        self.assertIn("mystery.xyz", filenames)

    def test_includes_files_without_extension(self):
        """Files with no extension are included."""
        self._make_file("README")
        result = discover_files(self.tmp_path)
        filenames = [os.path.basename(f) for f in result]
        self.assertIn("README", filenames)

class TestBuildPlan(unittest.TestCase):
    """
    Tests for OperationPlan construction from filesystem state.
    Verifies plan structure, category counts, and duplicate resolution.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _make_file(self, filename: str) -> str:
        path = os.path.join(self.tmp_path, filename)
        open(path, 'w').close()
        return path

    def test_correct_source_directory(self):
        """Plan records the source directory accurately."""
        self._make_file("report.pdf")
        plan = build_plan(self.tmp_path)
        self.assertEqual(plan.source_directory, self.tmp_path)

    def test_one_operation_per_file(self):
        """Each discovered file produces exactly one FileOperation."""
        self._make_file("report.pdf")
        self._make_file("photo.jpg")
        self._make_file("song.mp3")
        plan = build_plan(self.tmp_path)
        self.assertEqual(len(plan.operations), 3)

    def test_correct_category_assignment(self):
        """Each operation has the correct category."""
        self._make_file("report.pdf")
        plan = build_plan(self.tmp_path)
        pdf_ops = [op for op in plan.operations
                   if os.path.basename(op.source) == "report.pdf"]
        self.assertEqual(len(pdf_ops), 1)
        self.assertEqual(pdf_ops[0].category, "PDFs")

    def test_destination_inside_category_subfolder(self):
        """Destination path must be inside source/category/."""
        self._make_file("report.pdf")
        plan = build_plan(self.tmp_path)
        op = plan.operations[0]
        expected_prefix = os.path.join(self.tmp_path, "PDFs")
        self.assertTrue(op.destination.startswith(expected_prefix))

    def test_category_counts_match_operations(self):
        """category_counts must reflect actual operations — no redundant state."""
        self._make_file("report.pdf")
        self._make_file("notes.pdf")
        self._make_file("photo.jpg")
        plan = build_plan(self.tmp_path)
        self.assertEqual(plan.category_counts.get("PDFs"), 2)
        self.assertEqual(plan.category_counts.get("Images"), 1)
        # Sum of all counts must equal total operations
        total_from_counts = sum(plan.category_counts.values())
        self.assertEqual(total_from_counts, len(plan.operations))

    def test_duplicate_destinations_resolved(self):
        """Two files with same name get unique destinations."""
        # Create a pre-existing file in the PDFs subfolder
        pdfs_folder = os.path.join(self.tmp_path, "PDFs")
        os.makedirs(pdfs_folder)
        existing = os.path.join(pdfs_folder, "report.pdf")
        open(existing, 'w').close()

        # Now build plan with a file that would conflict
        self._make_file("report.pdf")
        plan = build_plan(self.tmp_path)

        pdf_ops = [op for op in plan.operations
                   if os.path.basename(op.source) == "report.pdf"]
        self.assertEqual(len(pdf_ops), 1)
        # Destination must NOT be the conflicting path
        self.assertNotEqual(pdf_ops[0].destination, existing)
        # Must end with (1)
        self.assertIn("(1)", os.path.basename(pdf_ops[0].destination))

    def test_empty_folder_produces_empty_plan(self):
        """Empty source directory → plan with no operations."""
        plan = build_plan(self.tmp_path)
        self.assertEqual(len(plan.operations), 0)
        self.assertEqual(plan.category_counts, {})

class TestValidatePlan(unittest.TestCase):
    """
    Tests for post-confirmation plan re-validation.
    Critical: verifies the safety invariant that confirmation applies
    only to the exact previewed plan, not general intent.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _make_file(self, filename: str) -> str:
        path = os.path.join(self.tmp_path, filename)
        open(path, 'w').close()
        return path

    def _make_operation(self, source: str, destination: str,
                        category: str = "PDFs") -> FileOperation:
        """Helper — builds a FileOperation directly for testing."""
        return FileOperation(
            source=source,
            destination=destination,
            category=category
        )

    def test_fresh_plan_is_valid(self):
        """A plan where all sources exist and destinations are free → valid."""
        source = self._make_file("report.pdf")
        destination = os.path.join(self.tmp_path, "PDFs", "report.pdf")
        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[self._make_operation(source, destination)],
            category_counts={"PDFs": 1}
        )
        is_valid, stale = validate_plan(plan)
        self.assertTrue(is_valid)
        self.assertEqual(stale, [])

    def test_source_disappeared_makes_plan_stale(self):
        """
        CRITICAL SAFETY TEST.
        If a source file disappears after preview, the plan is stale.
        validate_plan() must catch this before any file is touched.
        This verifies: confirmation applies only to what was previewed.
        """
        source = self._make_file("report.pdf")
        destination = os.path.join(self.tmp_path, "PDFs", "report.pdf")
        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[self._make_operation(source, destination)],
            category_counts={"PDFs": 1}
        )

        # Simulate file disappearing after preview, before execution
        os.remove(source)

        is_valid, stale = validate_plan(plan)
        self.assertFalse(is_valid)
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0][1], "SOURCE_DISAPPEARED")

    def test_any_stale_operation_fails_entire_plan(self):
        """
        Even one stale operation aborts the entire batch.
        Partial staleness is not acceptable — user confirmed exact plan.
        """
        source_good = self._make_file("photo.jpg")
        source_bad = self._make_file("report.pdf")

        dest_good = os.path.join(self.tmp_path, "Images", "photo.jpg")
        dest_bad = os.path.join(self.tmp_path, "PDFs", "report.pdf")

        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[
                self._make_operation(source_good, dest_good, "Images"),
                self._make_operation(source_bad, dest_bad, "PDFs"),
            ],
            category_counts={"Images": 1, "PDFs": 1}
        )

        # Only remove one file — the other is still there
        os.remove(source_bad)

        is_valid, stale = validate_plan(plan)
        self.assertFalse(is_valid)  # entire plan fails
        self.assertEqual(len(stale), 1)  # one stale operation reported

    def test_empty_plan_is_valid(self):
        """Empty plan has nothing to validate — returns valid."""
        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[],
            category_counts={}
        )
        is_valid, stale = validate_plan(plan)
        self.assertTrue(is_valid)
        self.assertEqual(stale, [])

class TestExecutePlan(unittest.TestCase):
    """
    Tests for batch execution with per-file feedback and failure tolerance.
    Uses unittest.mock to simulate filesystem operations deterministically.
    Real filesystem only used to verify actual file movement in success path.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _make_file(self, filename: str) -> str:
        path = os.path.join(self.tmp_path, filename)
        open(path, 'w').close()
        return path

    def _make_operation(self, source: str,
                        destination: str,
                        category: str = "PDFs") -> FileOperation:
        return FileOperation(
            source=source,
            destination=destination,
            category=category
        )

    def test_all_success_populates_succeeded(self):
        """All operations succeed → all in BatchResult.succeeded."""
        source = self._make_file("report.pdf")
        destination = os.path.join(self.tmp_path, "PDFs", "report.pdf")
        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[self._make_operation(source, destination)],
            category_counts={"PDFs": 1}
        )

        with patch("batch.organizer._move_file_raw") as mock_move:
            mock_move.return_value = (True, "MOVE_SUCCESS")
            result = execute_plan(plan)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failure_count, 0)
        self.assertEqual(result.total, 1)

    def test_single_failure_recorded_in_failed(self):
        """One failed operation → recorded in BatchResult.failed."""
        source = self._make_file("report.pdf")
        destination = os.path.join(self.tmp_path, "PDFs", "report.pdf")
        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[self._make_operation(source, destination)],
            category_counts={"PDFs": 1}
        )

        with patch("batch.organizer._move_file_raw") as mock_move:
            mock_move.return_value = (False, "PERMISSION_DENIED")
            result = execute_plan(plan)

        self.assertEqual(result.failure_count, 1)
        self.assertEqual(result.success_count, 0)
        self.assertEqual(result.failed[0][1], "PERMISSION_DENIED")

    def test_failure_does_not_stop_remaining_operations(self):
        """
        Partial failure tolerance — one failure must not abort the batch.
        Remaining operations execute regardless of earlier failures.
        """
        source1 = self._make_file("report.pdf")
        source2 = self._make_file("photo.jpg")
        dest1 = os.path.join(self.tmp_path, "PDFs", "report.pdf")
        dest2 = os.path.join(self.tmp_path, "Images", "photo.jpg")

        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[
                self._make_operation(source1, dest1, "PDFs"),
                self._make_operation(source2, dest2, "Images"),
            ],
            category_counts={"PDFs": 1, "Images": 1}
        )

        # First call fails, second succeeds
        with patch("batch.organizer._move_file_raw") as mock_move:
            mock_move.side_effect = [
                (False, "PERMISSION_DENIED"),  # first call
                (True, "MOVE_SUCCESS"),         # second call
            ]
            result = execute_plan(plan)

        self.assertEqual(result.success_count, 1)
        self.assertEqual(result.failure_count, 1)
        self.assertEqual(result.total, 2)

    def test_batch_result_properties_are_correct(self):
        """total, success_count, failure_count are computed correctly."""
        source1 = self._make_file("a.pdf")
        source2 = self._make_file("b.pdf")
        source3 = self._make_file("c.pdf")
        dest1 = os.path.join(self.tmp_path, "PDFs", "a.pdf")
        dest2 = os.path.join(self.tmp_path, "PDFs", "b.pdf")
        dest3 = os.path.join(self.tmp_path, "PDFs", "c.pdf")

        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[
                self._make_operation(source1, dest1),
                self._make_operation(source2, dest2),
                self._make_operation(source3, dest3),
            ],
            category_counts={"PDFs": 3}
        )

        with patch("batch.organizer._move_file_raw") as mock_move:
            mock_move.side_effect = [
                (True, "MOVE_SUCCESS"),
                (True, "MOVE_SUCCESS"),
                (False, "OS_ERROR"),
            ]
            result = execute_plan(plan)

        self.assertEqual(result.total, 3)
        self.assertEqual(result.success_count, 2)
        self.assertEqual(result.failure_count, 1)

    def test_files_actually_reach_destination(self):
        """
        Integration-level test — real filesystem.
        Verifies files physically move to correct destination folders.
        No mocking — uses real shutil.move() via _move_file_raw.
        """
        source = self._make_file("report.pdf")
        pdfs_folder = os.path.join(self.tmp_path, "PDFs")
        os.makedirs(pdfs_folder)
        destination = os.path.join(pdfs_folder, "report.pdf")

        plan = OperationPlan(
            source_directory=self.tmp_path,
            operations=[self._make_operation(source, destination)],
            category_counts={"PDFs": 1}
        )

        result = execute_plan(plan)

        self.assertEqual(result.success_count, 1)
        # File must exist at destination
        self.assertTrue(os.path.isfile(destination))
        # File must no longer exist at source
        self.assertFalse(os.path.isfile(source))

# Entry point for running tests directly from this script.
if __name__ == "__main__":
    unittest.main(verbosity=2)