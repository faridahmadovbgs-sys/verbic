import unittest
from prompt_builder import PromptBuilder


class TestPromptBuilder(unittest.TestCase):
    def test_grammar_only(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("i dont no what to do", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("i dont no what to do", prompt)
        self.assertNotIn("formal", prompt.lower().split("text to correct")[0])
        self.assertNotIn("concise", prompt.lower().split("text to correct")[0])

    def test_grammar_and_formal(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": True, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("hey whats up", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("formal", prompt.lower())

    def test_grammar_and_concise(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": True, "expand": False}
        prompt = builder.build("some long text here", options)

        self.assertIn("concise", prompt.lower())

    def test_casual_tone(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": True, "concise": False, "expand": False}
        prompt = builder.build("Dear Sir", options)

        self.assertIn("casual", prompt.lower())

    def test_expand_option(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": True}
        prompt = builder.build("short text", options)

        self.assertIn("elaborate", prompt.lower())

    def test_all_options_combined(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": True, "casual": False, "concise": True, "expand": False}
        prompt = builder.build("test", options)

        self.assertIn("Fix all grammar", prompt)
        self.assertIn("formal", prompt.lower())
        self.assertIn("concise", prompt.lower())

    def test_prompt_includes_return_only_instruction(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("test", options)

        self.assertIn("Return ONLY the corrected text", prompt)

    def test_empty_text(self):
        builder = PromptBuilder()
        options = {"grammar": True, "formal": False, "casual": False, "concise": False, "expand": False}
        prompt = builder.build("", options)

        self.assertIn('"""\n\n"""', prompt)


if __name__ == "__main__":
    unittest.main()
