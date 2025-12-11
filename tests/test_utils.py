"""
Unit tests for utility functions.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from src.utils.language_detection import detect_text_language
from src.utils.image_processing import resize_image_for_vlm
from PIL import Image


class TestLanguageDetection(unittest.TestCase):
    def test_detect_with_fast_langdetect(self):
        with patch("src.utils.language_detection.fast_detect") as mock_detect:
            mock_detect.return_value = [{"lang": "en"}]
            self.assertEqual(detect_text_language("Hello"), "en")

    def test_detect_fallback_on_error(self):
        with patch("src.utils.language_detection.fast_detect") as mock_detect:
            mock_detect.side_effect = Exception("fail")
            self.assertEqual(detect_text_language("Hello", fallback_lang="ja"), "ja")

    def test_detect_empty_text(self):
        self.assertEqual(detect_text_language("", fallback_lang="en"), "en")

    def test_detect_unsupported_lang(self):
        with patch("src.utils.language_detection.fast_detect") as mock_detect:
            mock_detect.return_value = [{"lang": "xx"}]
            self.assertEqual(detect_text_language("Hello", fallback_lang="en"), "en")


class TestImageProcessing(unittest.TestCase):
    def test_resize_no_resize(self):
        img = Image.new("RGB", (100, 100), color="red")
        resized, was_resized = resize_image_for_vlm(img, max_long_edge=2048)
        self.assertFalse(was_resized)
        self.assertEqual(resized.size, (100, 100))

    def test_resize_downscale(self):
        img = Image.new("RGB", (3000, 2000), color="red")
        resized, was_resized = resize_image_for_vlm(img, max_long_edge=2048)
        self.assertTrue(was_resized)
        self.assertEqual(max(resized.size), 2048)


if __name__ == "__main__":
    unittest.main()

