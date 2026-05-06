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
                f"The user copied the following conversation/context before typing their reply. "
                f"Use it to understand tone, topic, and intent — but do NOT include it in your output.\n\n"
                f"Conversation context:\n"
                f'"""\n{context}\n"""\n\n'
            )

        return (
            f"You are a text correction assistant. Apply the following transformations to the text below:\n"
            f"{instruction_block}\n\n"
            f"{context_block}"
            f"IMPORTANT: Return ONLY the corrected text. No explanations, no quotes, no prefixes.\n\n"
            f"Text to correct:\n"
            f'"""\n{text}\n"""'
        )
