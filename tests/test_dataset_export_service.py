import json
import os
import sqlite3
import tempfile
import unittest

from dataset_export_service import (
    EXPORT_FORMATS,
    ExportValidationError,
    export_file_path,
    inspect_for_web,
    list_exports,
    normalize_export_options,
    run_export,
)


class DatasetExportServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = os.path.join(self.temp_dir.name, "calls.db")
        raw_dir = os.path.join(self.temp_dir.name, "data", "calls", "api.example.com", "2026", "07", "18")
        os.makedirs(raw_dir)
        self.raw_path = os.path.join(raw_dir, "call-test.json")
        with open(self.raw_path, "w", encoding="utf-8") as f:
            json.dump({
                "request": {
                    "model": "test-model",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
                "response": {
                    "id": "chat-test",
                    "choices": [{
                        "message": {"role": "assistant", "content": "Hi"},
                        "finish_reason": "stop",
                    }],
                },
            }, f)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE calls (
                    call_id TEXT PRIMARY KEY,
                    protocol TEXT,
                    upstream_provider TEXT,
                    upstream_model TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_ms INTEGER,
                    upstream_status INTEGER,
                    stop_reason TEXT,
                    raw_path TEXT,
                    is_stream INTEGER
                )
            """)
            conn.execute(
                "INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "call-test", "openai-chat", "api.example.com", "test-model",
                    "2026-07-18T12:00:00", "2026-07-18T12:00:01", 1000,
                    200, "stop", os.path.relpath(self.raw_path, self.temp_dir.name), 0,
                ),
            )
            second_raw_path = os.path.join(raw_dir, "call-second.json")
            with open(second_raw_path, "w", encoding="utf-8") as f:
                json.dump({
                    "request": {
                        "model": "second-model",
                        "messages": [{"role": "user", "content": "Second"}],
                    },
                    "response": {
                        "id": "chat-second",
                        "choices": [{
                            "message": {"role": "assistant", "content": "Second answer"},
                            "finish_reason": "stop",
                        }],
                    },
                }, f)
            conn.execute(
                "INSERT INTO calls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "call-second", "openai-chat", "api.example.com", "second-model",
                    "2026-07-18T13:00:00", "2026-07-18T13:00:01", 900,
                    200, "stop", os.path.relpath(second_raw_path, self.temp_dir.name), 0,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def test_rejects_invalid_options_and_download_paths(self):
        with self.assertRaisesRegex(ExportValidationError, "unsupported"):
            normalize_export_options({"format": "pickle"})
        with self.assertRaisesRegex(ExportValidationError, "limit"):
            normalize_export_options({"limit": 0})
        with self.assertRaisesRegex(ExportValidationError, "max_seq_len"):
            normalize_export_options({"max_seq_len": 64})
        self.assertIsNone(export_file_path(self.db_path, "../calls.db"))
        self.assertIsNone(export_file_path(self.db_path, "dataset.jsonl"))

    def test_inspect_returns_dataset_summary_without_previews(self):
        report = inspect_for_web(self.db_path, include_window_budget=True)
        self.assertEqual(report["calls"], 2)
        self.assertEqual(report["episodes"], 2)
        self.assertEqual(report["previews"], [])
        self.assertEqual(report["window_budget"]["assistant_targets"], 2)

    def test_explicit_selection_controls_inspection_and_every_export_format(self):
        report = inspect_for_web(
            self.db_path,
            call_ids=["call-second"],
            include_window_budget=True,
        )
        self.assertEqual(report["calls"], 1)
        self.assertEqual(report["models"], {"second-model": 1})

        for export_format in sorted(EXPORT_FORMATS):
            with self.subTest(export_format=export_format):
                result = run_export(self.db_path, {
                    "format": export_format,
                    "call_ids": ["call-second"],
                    "max_seq_len": 512,
                })
                self.assertEqual(result["selected_count"], 1)
                self.assertIn("-selected1", result["filename"])
                self.assertEqual(result["written"], 1)

    def test_selection_rejects_empty_or_missing_calls(self):
        with self.assertRaisesRegex(ExportValidationError, "select at least one"):
            run_export(self.db_path, {"call_ids": []})
        with self.assertRaisesRegex(ExportValidationError, "no longer exist"):
            run_export(self.db_path, {"call_ids": ["call-missing"]})

    def test_generates_and_lists_every_supported_format(self):
        generated = []
        for export_format in sorted(EXPORT_FORMATS):
            with self.subTest(export_format=export_format):
                result = run_export(self.db_path, {
                    "format": export_format,
                    "max_seq_len": 512,
                })
                generated.append(result["filename"])
                self.assertEqual(result["written"], 2)
                path = export_file_path(self.db_path, result["filename"])
                self.assertIsNotNone(path)
                self.assertTrue(os.path.isfile(path))
                self.assertGreater(result["size_bytes"], 0)
                if export_format == "openai_windowed":
                    self.assertLessEqual(result["max_estimated_units"], result["max_seq_len"])

        rows = list_exports(self.db_path)
        self.assertEqual({row["filename"] for row in rows}, set(generated))

    def test_context_limit_is_available_for_every_primary_format(self):
        for export_format in ("canonical", "tool_sft", "openai", "sharegpt"):
            with self.subTest(export_format=export_format):
                result = run_export(self.db_path, {
                    "format": export_format,
                    "context_limit": True,
                    "max_seq_len": 512,
                })
                self.assertTrue(result["context_limited"])
                self.assertIn(f"-{export_format}-limited-", result["filename"])
                self.assertEqual(result["written"], 2)
                self.assertLessEqual(result["max_estimated_units"], 512)


if __name__ == "__main__":
    unittest.main()
