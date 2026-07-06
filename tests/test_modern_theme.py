import unittest

from src.ui.modern_theme import get_theme, THEMES
from src.ui.styles import button_style, input_style


class ModernThemeTests(unittest.TestCase):
    def test_supported_themes_available(self):
        self.assertIn("dark", THEMES)
        self.assertIn("light", THEMES)
        self.assertIn("glass", THEMES)

    def test_get_theme_defaults_to_dark(self):
        self.assertEqual(get_theme().name, "dark")

    def test_get_theme_rejects_invalid(self):
        with self.assertRaises(ValueError):
            get_theme("invalid")

    def test_styles_produce_expected_primary_tokens(self):
        dark = get_theme("dark")
        button = button_style(dark, is_primary=True)
        inp = input_style(dark)
        self.assertEqual(button["fg_color"], dark.primary)
        self.assertEqual(inp["border_color"], dark.border)


if __name__ == "__main__":
    unittest.main()
