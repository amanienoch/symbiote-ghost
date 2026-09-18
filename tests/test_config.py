"""Configuration validation and persistence tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.app.config import (
    MAX_CONFIG_BYTES,
    AppConfig,
    ConfigError,
    load_config,
    parse_config,
)


class ConfigurationTests(unittest.TestCase):
    def test_defaults_are_private_and_local(self) -> None:
        config = AppConfig()
        self.assertEqual(config.ai.provider, "ollama")
        self.assertFalse(config.ghost.enabled)
        self.assertFalse(config.voice.enabled)
        self.assertFalse(config.privacy.save_screenshots)

    def test_partial_configuration_uses_defaults(self) -> None:
        config = parse_config({"screen": {"capture_interval": 3}})
        self.assertEqual(config.screen.capture_interval, 3.0)
        self.assertEqual(config.screen.change_threshold, 0.08)
        self.assertEqual(config.ai, AppConfig().ai)

    def test_reference_configuration_matches_defaults(self) -> None:
        path = Path(__file__).resolve().parents[1] / "config" / "default.yaml"
        self.assertEqual(load_config(path), AppConfig())

    def test_unknown_fields_are_rejected(self) -> None:
        for document in (
            {"unknown": {}},
            {"screen": {"capturre_interval": 2}},
            {"ai": {"endpoint": "https://example.com"}},
        ):
            with self.subTest(document=document):
                with self.assertRaises(ConfigError):
                    parse_config(document)

    def test_invalid_documents_are_rejected(self) -> None:
        documents = (
            None,
            [],
            {"screen": None},
            {"ghost": {"enabled": "false"}},
            {"screen": {"capture_interval": True}},
            {"screen": {"capture_interval": 0}},
            {"screen": {"capture_interval": float("inf")}},
            {"screen": {"capture_interval": 10**400}},
            {"screen": {"change_threshold": float("nan")}},
            {"screen": {"change_threshold": 1.01}},
            {"ai": {"provider": "cloud"}},
            {"ai": {"general_model": 123}},
            {"ai": {"general_model": "bad\nname"}},
        )
        for document in documents:
            with self.subTest(document=document):
                with self.assertRaises(ConfigError):
                    parse_config(document)

    def test_default_file_is_created_and_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "config.yaml"
            config = load_config(path, create_if_missing=True)
            self.assertEqual(config, AppConfig())
            self.assertTrue(path.is_file())
            self.assertEqual(load_config(path), config)

    def test_missing_explicit_file_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.yaml"
            with self.assertRaises(ConfigError):
                load_config(path)
            self.assertFalse(path.exists())

    def test_invalid_existing_file_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            original = "screen:\n  capture_interval: invalid\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaises(ConfigError):
                load_config(path, create_if_missing=True)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_unsafe_or_ambiguous_yaml_is_rejected(self) -> None:
        examples = (
            "ghost:\n  enabled: false\n  enabled: true\n",
            "screen: [\n",
            "!!python/object/apply:os.system ['echo forbidden']",
            "1: value\n",
            "",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            for text in examples:
                with self.subTest(text=text):
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ConfigError):
                        load_config(path)

    def test_oversized_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.yaml"
            path.write_bytes(b" " * (MAX_CONFIG_BYTES + 1))
            with self.assertRaises(ConfigError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
