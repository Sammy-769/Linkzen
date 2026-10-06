import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import settings


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.settings_path_patch = patch.object(
            settings, "SETTINGS_FILE", Path(self.temp_directory.name) / "settings.json"
        )
        self.settings_path_patch.start()

    def tearDown(self):
        self.settings_path_patch.stop()
        self.temp_directory.cleanup()

    def test_global_prompt_persists_and_preserves_other_settings(self):
        settings.update_settings(automatic_memory=False, global_prompt="Be concise.")

        reloaded = settings.get_settings()

        self.assertEqual(reloaded["global_prompt"], "Be concise.")
        self.assertFalse(reloaded["automatic_memory"])
        self.assertTrue(reloaded["rag_enabled"])
        self.assertEqual(
            json.loads(settings.SETTINGS_FILE.read_text(encoding="utf-8"))["global_prompt"],
            "Be concise.",
        )

    def test_empty_prompt_is_a_supported_persisted_value(self):
        settings.update_settings(global_prompt="A temporary instruction")
        settings.update_settings(global_prompt="")

        self.assertEqual(settings.get_settings()["global_prompt"], "")

    def test_prompt_is_limited_to_supported_length(self):
        settings.update_settings(global_prompt="x" * (settings.MAX_GLOBAL_PROMPT_LENGTH + 1))

        self.assertEqual(
            len(settings.get_settings()["global_prompt"]),
            settings.MAX_GLOBAL_PROMPT_LENGTH,
        )

    def test_linkedin_prompts_merge_and_persist_without_shared_preferences(self):
        settings.update_settings(linkedin_prompts={"analyze_profile": "Use concise profile feedback."})

        reloaded = settings.get_settings()

        self.assertEqual(
            reloaded["linkedin_prompts"]["analyze_profile"],
            "Use concise profile feedback.",
        )
        self.assertEqual(
            reloaded["linkedin_prompts"]["create_post"],
            settings.DEFAULT_LINKEDIN_PROMPTS["create_post"],
        )
        self.assertNotIn("linkedin_preferences", reloaded)
        self.assertEqual(reloaded["global_prompt"], "")

    def test_linkedin_reset_can_restore_default_system_prompt(self):
        settings.update_settings(linkedin_prompts={"post_ideas": "Custom ideas prompt."})
        settings.update_settings(
            linkedin_prompts={
                "post_ideas": settings.DEFAULT_LINKEDIN_PROMPTS["post_ideas"]
            }
        )

        self.assertEqual(
            settings.get_settings()["linkedin_prompts"]["post_ideas"],
            settings.DEFAULT_LINKEDIN_PROMPTS["post_ideas"],
        )

    def test_empty_custom_linkedin_prompt_remains_empty(self):
        settings.update_settings(linkedin_prompts={"create_post": ""})

        self.assertEqual(settings.get_settings()["linkedin_prompts"]["create_post"], "")

    def test_reply_prompt_is_action_specific_and_can_be_reset(self):
        default_prompt = settings.DEFAULT_LINKEDIN_PROMPTS["reply_to_message"]
        settings.update_settings(linkedin_prompts={"reply_to_message": "Custom reply prompt."})
        self.assertEqual(
            settings.get_settings()["linkedin_prompts"]["reply_to_message"],
            "Custom reply prompt.",
        )

        settings.update_settings(linkedin_prompts={"reply_to_message": default_prompt})

        self.assertEqual(
            settings.get_settings()["linkedin_prompts"]["reply_to_message"],
            default_prompt,
        )


if __name__ == "__main__":
    unittest.main()
