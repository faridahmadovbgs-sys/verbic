from config import TONE_PROMPTS, LANGUAGE_KEYS


class PromptBuilder:
    def build(self, text, options, context=None, writing_context=None):
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

        writing_context_block = ""
        if writing_context and writing_context.strip():
            writing_context_block = (
                f"Writing context — use this to shape tone, format, and vocabulary:\n"
                f'"""\n{writing_context.strip()}\n"""\n\n'
            )

        context_block = ""
        if context and context.strip() != text.strip():
            context_block = (
                f"Surrounding document for tone/topic reference only. "
                f"DO NOT correct, repeat, or include any part of this in your output.\n\n"
                f"Surrounding context:\n"
                f'"""\n{context}\n"""\n\n'
            )

        # Translations legitimately change the character count (Chinese or
        # Japanese compress Latin text to a fraction of its length), so the
        # length rule only applies when no target language is selected.
        translating = any(options.get(key) for key in LANGUAGE_KEYS)
        length_rule = "" if translating else \
            "- Output length should be similar to input length.\n"

        return (
            f"You are a text correction assistant. Apply these transformations:\n"
            f"{instruction_block}\n\n"
            f"{writing_context_block}"
            f"{context_block}"
            f"CRITICAL RULES:\n"
            f"- Output ONLY the corrected text. Plain text only.\n"
            f"- Do NOT wrap your answer in quotes, triple quotes, code fences, or any delimiter.\n"
            f"- Do NOT add preambles like \"Here is\", \"The corrected version\", or any explanation.\n"
            f"- Do NOT include any surrounding context.\n"
            f"{length_rule}\n"
            f"Snippet to correct:\n"
            f"<<<\n{text}\n>>>"
        )

    def build_predict(self, text, writing_context=None):
        """Prompt for predicting how the user would continue `text`.

        Returns ONLY the continuation (the text that should come *after* what
        the user has typed), so it can be inserted at the caret.
        """
        guidance_block = ""
        if writing_context and writing_context.strip():
            guidance_block = (
                f"Context for what the user is writing (tone, audience, topic):\n"
                f'"""\n{writing_context.strip()}\n"""\n\n'
            )

        return (
            f"You are an autocomplete engine. Continue the user's text naturally "
            f"with the next few words or the rest of the sentence.\n\n"
            f"{guidance_block}"
            f"CRITICAL RULES:\n"
            f"- Output ONLY the continuation — the text that comes AFTER what's shown.\n"
            f"- Do NOT repeat any of the user's existing text.\n"
            f"- Do NOT wrap in quotes or add explanations.\n"
            f"- Start with a leading space if the user's text doesn't end with one.\n"
            f"- Keep it short: finish the current thought, at most one sentence.\n\n"
            f"User's text so far:\n"
            f"<<<\n{text}\n>>>"
        )

    def build_answer(self, question, writing_context=None):
        """Prompt for drafting a full reply to `question`.

        `writing_context` (when set, and different from the question) carries
        any extra guidance the user pinned — desired tone, audience, or
        background — so the answer is shaped to their situation.
        """
        guidance_block = ""
        if writing_context and writing_context.strip() and writing_context.strip() != (question or "").strip():
            guidance_block = (
                f"Additional context to honor (audience, tone, background):\n"
                f'"""\n{writing_context.strip()}\n"""\n\n'
            )

        return (
            f"You are helping the user write a reply. Draft a clear, natural, "
            f"ready-to-send answer to the message or question below.\n\n"
            f"{guidance_block}"
            f"CRITICAL RULES:\n"
            f"- Output ONLY the answer text the user can send. Plain text only.\n"
            f"- Do NOT wrap your answer in quotes, code fences, or any delimiter.\n"
            f"- Do NOT add preambles like \"Here is\", \"Sure\", or any explanation.\n"
            f"- Do NOT restate the question.\n"
            f"- Keep it concise and appropriate to the message.\n\n"
            f"Message/question to answer:\n"
            f"<<<\n{question}\n>>>"
        )
