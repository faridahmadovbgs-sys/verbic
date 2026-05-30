import unittest
from prompt_builder import PromptBuilder


class TestPromptBuilder(unittest.TestCase):
    def test_grammar_only(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "expand": False}
        prompt = builder.build("i dont no what to do", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("i dont no what to do", prompt)
        self.assertNotIn("formal", prompt.lower().split("text to correct")[0])

    def test_grammar_and_formal(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": True, "casual": False, "expand": False}
        prompt = builder.build("hey whats up", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("formal", prompt.lower())

    def test_casual_tone(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": True, "expand": False}
        prompt = builder.build("Dear Sir", options)

        self.assertIn("casual", prompt.lower())

    def test_expand_option(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "expand": True}
        prompt = builder.build("short text", options)

        self.assertIn("elaborate", prompt.lower())

    def test_all_options_combined(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": True, "casual": False, "expand": True}
        prompt = builder.build("test", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("formal", prompt.lower())
        self.assertIn("elaborate", prompt.lower())

    def test_concise_tone(self):
        # Concise is one of the expanded tone set — enabling it must inject a
        # concise instruction into the prompt.
        builder = PromptBuilder()
        options = {"grammar": True, "concise": True}
        prompt = builder.build("text", options)
        self.assertIn("concise", prompt.lower())

    def test_new_tones_emit_instructions(self):
        # Each newly-added tone should contribute its instruction line.
        from config import TONE_PROMPTS
        builder = PromptBuilder()
        for key in ("professional", "friendly", "confident", "persuasive",
                    "empathetic", "academic", "playful"):
            prompt = builder.build("text", {key: True})
            self.assertIn(TONE_PROMPTS[key], prompt)

    def test_tones_are_independent_in_prompt(self):
        # The builder emits whatever options are set; mutual-exclusivity is a
        # UI concern (tray menu), not the builder's job.
        builder = PromptBuilder()
        prompt = builder.build("text", {"formal": True, "casual": True})
        self.assertIn("formal", prompt.lower())
        self.assertIn("casual", prompt.lower())

    def test_prompt_includes_return_only_instruction(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "expand": False}
        prompt = builder.build("test", options)

        self.assertIn("Output ONLY the corrected", prompt)

    def test_empty_text(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "expand": False}
        prompt = builder.build("", options)

        self.assertIn("<<<\n\n>>>", prompt)


if __name__ == "__main__":
    unittest.main()
