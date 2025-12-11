"""
Unit tests for configuration.
"""

import os
import unittest
from unittest.mock import patch

from src.config import VLMConfig, LLMConfig, Config, load_config


class TestVLMConfig(unittest.TestCase):
    def test_from_env(self):
        with patch.dict(os.environ, {"OPENAI_BASE_URL": "http://b", "OPENAI_MODEL": "m", "OPENAI_API_KEY": "k"}):
            cfg = VLMConfig.from_env()
            self.assertEqual(cfg.base_url, "http://b")
            self.assertEqual(cfg.model_name, "m")
            self.assertEqual(cfg.api_key, "k")

    def test_is_valid(self):
        self.assertTrue(VLMConfig(base_url="x", model_name="y").is_valid())
        self.assertFalse(VLMConfig(base_url=None, model_name="y").is_valid())


class TestLLMConfig(unittest.TestCase):
    def test_from_env(self):
        with patch.dict(os.environ, {"LLM_MODEL_NAME": "m", "LLM_KEY": "k", "LLM_API": "http://a", "LLM_version": "v"}):
            cfg = LLMConfig.from_env()
            self.assertEqual(cfg.model_name, "m")
            self.assertEqual(cfg.api_key, "k")
            self.assertEqual(cfg.api_base, "http://a")
            self.assertEqual(cfg.api_version, "v")

    def test_is_valid(self):
        self.assertTrue(LLMConfig(model_name="m", api_key="k", api_base="a").is_valid())
        self.assertFalse(LLMConfig(model_name=None, api_key="k", api_base="a").is_valid())


class TestConfig(unittest.TestCase):
    def test_load_config(self):
        with patch.dict(os.environ, {}):
            cfg = load_config()
            self.assertIsInstance(cfg, Config)


if __name__ == "__main__":
    unittest.main()

