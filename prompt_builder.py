class PromptBuilder:
    def build(self, text, options):
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

        return (
            f"You are a text correction assistant. Apply the following transformations to the text below:\n"
            f"{instruction_block}\n\n"
            f"IMPORTANT: Return ONLY the corrected text. No explanations, no quotes, no prefixes.\n\n"
            f"Text to correct:\n"
            f'"""\n{text}\n"""'
        )
