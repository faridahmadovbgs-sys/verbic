class PromptBuilder:
    def build(self, text, options, context=None):
        instructions = []

        if options.get("grammar"):
            instructions.append("- Fix all grammar, spelling, and punctuation errors")
        if options.get("formal"):
            instructions.append("- Rewrite in a formal, professional tone")
        if options.get("casual"):
            instructions.append("- Rewrite in a casual, friendly, conversational tone")
        if options.get("concise"):
            instructions.append("- Make the text more concise while keeping the meaning")
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
