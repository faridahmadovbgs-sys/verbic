from config import TONE_PROMPTS


class PromptBuilder:
    def build(self, text, options, context=None):
        instructions = []

        if options.get("grammar"):
            instructions.append("- Fix all grammar, spelling, and punctuation errors")
        # Tones are mutually exclusive in the UI, but emit whatever is enabled.
        for key, prompt in TONE_PROMPTS.items():
            if options.get(key):
                instructions.append(f"- {prompt}")
        if options.get("expand"):
            instructions.append("- Elaborate and expand the text with more detail")

        instruction_block = "\n".join(instructions)

        context_block = ""
        if context and context.strip() != text.strip():
            context_block = (
                f"Surrounding document for tone/topic reference only. "
                f"DO NOT correct, repeat, or include any part of this in your output.\n\n"
                f"Surrounding context:\n"
                f'"""\n{context}\n"""\n\n'
            )

        return (
            f"You are a text correction assistant. Apply these transformations:\n"
            f"{instruction_block}\n\n"
            f"{context_block}"
            f"CRITICAL RULES:\n"
            f"- Output ONLY the corrected text. Plain text only.\n"
            f"- Do NOT wrap your answer in quotes, triple quotes, code fences, or any delimiter.\n"
            f"- Do NOT add preambles like \"Here is\", \"The corrected version\", or any explanation.\n"
            f"- Do NOT include any surrounding context.\n"
            f"- Output length should be similar to input length.\n\n"
            f"Snippet to correct:\n"
            f"<<<\n{text}\n>>>"
        )
