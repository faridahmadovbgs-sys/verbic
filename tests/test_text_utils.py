import unittest
from text_utils import (
    clean_llm_output,
    strip_preambles,
    strip_input_delimiters,
    strip_label_lines,
    strip_trailing_explanation,
)


class TestStripPreambles(unittest.TestCase):
    def test_here_is_the_corrected(self):
        self.assertEqual(
            strip_preambles("Here is the corrected text: I am happy."),
            "I am happy.",
        )

    def test_heres_the_revised_version(self):
        self.assertEqual(
            strip_preambles("Here's the revised version: She runs daily."),
            "She runs daily.",
        )

    def test_corrected_label(self):
        self.assertEqual(strip_preambles("Corrected: He went home."), "He went home.")

    def test_sure_preamble(self):
        self.assertEqual(
            strip_preambles("Sure! Here is the corrected text: It works."),
            "It works.",
        )

    def test_ive_corrected(self):
        self.assertEqual(
            strip_preambles("I've corrected the text: Looks good now."),
            "Looks good now.",
        )

    def test_no_preamble_passthrough(self):
        self.assertEqual(strip_preambles("This is fine."), "This is fine.")


class TestStripInputDelimiters(unittest.TestCase):
    def test_strips_triple_angle_brackets(self):
        self.assertEqual(strip_input_delimiters("<<<\nHello.\n>>>"), "Hello.")

    def test_passthrough_without_delimiters(self):
        self.assertEqual(strip_input_delimiters("Hello."), "Hello.")


class TestStripLabelLines(unittest.TestCase):
    def test_drops_original_label_line(self):
        self.assertEqual(
            strip_label_lines("Original: foo\nCorrected text here."),
            "Corrected text here.",
        )


class TestStripTrailingExplanation(unittest.TestCase):
    def test_drops_changes_made_section(self):
        result = strip_trailing_explanation(
            "She runs daily.\n\nChanges made: fixed verb agreement."
        )
        self.assertEqual(result, "She runs daily.")

    def test_drops_explanation_section(self):
        result = strip_trailing_explanation(
            "He went home.\nExplanation: 'went' is the correct past tense."
        )
        self.assertEqual(result, "He went home.")


class TestCleanLLMOutputIntegration(unittest.TestCase):
    def test_combined_preamble_and_quotes(self):
        out = clean_llm_output('Here is the corrected text: "Hello world."')
        self.assertEqual(out, "Hello world.")

    def test_fence_with_preamble(self):
        out = clean_llm_output(
            "Here is the corrected text:\n```\nHello world.\n```"
        )
        self.assertEqual(out, "Hello world.")

    def test_think_block_with_preamble(self):
        out = clean_llm_output(
            "<think>let me fix this</think>\nHere is the corrected text: Hello world."
        )
        self.assertEqual(out, "Hello world.")

    def test_echoed_delimiters(self):
        out = clean_llm_output("<<<\nHello world.\n>>>")
        self.assertEqual(out, "Hello world.")

    def test_passthrough_clean_output(self):
        self.assertEqual(clean_llm_output("Hello world."), "Hello world.")

    def test_empty_input(self):
        self.assertEqual(clean_llm_output(""), "")
        self.assertIsNone(clean_llm_output(None))


if __name__ == "__main__":
    unittest.main()
