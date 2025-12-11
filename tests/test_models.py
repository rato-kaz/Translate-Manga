"""
Unit tests for model prompt helpers and wrappers.
"""

import unittest
from unittest.mock import patch

from src.models.prompts import (
    build_vlm_prompt,
    build_llm_system_prompt,
    build_llm_user_prompt,
    clean_translation,
)
from src.config import VLMConfig, LLMConfig


class TestPrompts(unittest.TestCase):
    def test_vlm_prompt(self):
        prompt = build_vlm_prompt(["Hello", "World"])
        self.assertIn("Hello", prompt)
        self.assertIn("World", prompt)

    def test_llm_system_prompt(self):
        prompt = build_llm_system_prompt()
        self.assertIn("translator", prompt.lower())

    def test_llm_user_prompt_context(self):
        ctx = {"chapter": 1, "page": 2, "panel": 3, "bubble": 4, "speaker": {"type": "character", "character_name": "A"}, "caption": "desc"}
        prompt = build_llm_user_prompt("Hi", "en", "ja", ctx)
        self.assertIn("Chapter: 1", prompt)
        self.assertIn("Speaker", prompt)

    def test_clean_translation(self):
        self.assertEqual(clean_translation("Translation: Hello\nWorld"), "Hello World")
        self.assertEqual(clean_translation(""), "")


class TestConfigs(unittest.TestCase):
    def test_vlm_config_valid(self):
        cfg = VLMConfig(base_url="http://x", model_name="y")
        self.assertTrue(cfg.is_valid())

    def test_llm_config_valid(self):
        cfg = LLMConfig(model_name="m", api_key="k", api_base="http://a")
        self.assertTrue(cfg.is_valid())


if __name__ == "__main__":
    unittest.main()

