from __future__ import annotations

import unittest

from script_imports import import_script


provider = import_script(".github/scripts/validate_ai_provider.py", "validate_ai_provider")


class ValidateAIProviderTest(unittest.TestCase):
    def test_default_codex_and_explicit_codex(self) -> None:
        self.assertEqual(provider.validate("", "key", "", ""), "codex")
        self.assertEqual(provider.validate("codex", "key", "", ""), "codex")

    def test_claude_uses_only_its_own_credentials(self) -> None:
        self.assertEqual(provider.validate("claude", "", "key", "claude-sonnet-4-5"), "claude")

    def test_missing_selected_credential_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "CODEX_API_KEY"):
            provider.validate("", "", "key", "claude-sonnet-4-5")
        with self.assertRaisesRegex(ValueError, "ANTHROPIC_API_KEY"):
            provider.validate("claude", "key", "", "claude-sonnet-4-5")

    def test_claude_model_must_be_safe_for_action_arguments(self) -> None:
        for model in ("", "model name", 'model" --foo', "model\n--foo"):
            with self.subTest(model=model), self.assertRaisesRegex(ValueError, "CLAUDE_MODEL"):
                provider.validate("claude", "", "key", model)

    def test_unknown_provider_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "AI_PROVIDER"):
            provider.validate("other", "key", "key", "claude-sonnet-4-5")


if __name__ == "__main__":
    unittest.main()
