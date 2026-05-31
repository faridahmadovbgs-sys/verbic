"""Post-processing helpers for LLM responses."""
import re


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_QUOTE_PAIRS = (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"))
# Match content inside ```code fences``` or """triple-quoted blocks""".
_FENCE_RE = re.compile(r'```(?:\w+)?\s*\n?(.+?)\n?```', re.DOTALL)
_TRIPLE_QUOTE_RE = re.compile(r'"""\s*(.+?)\s*"""', re.DOTALL)

# Common preamble phrases models emit despite "no preamble" instructions.
# Matched case-insensitively at the start of the response, optionally
# followed by a colon and content. We strip up to the first newline so the
# real answer below survives.
_PREAMBLE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^\s*(?:here(?:'s|\s+is)|here\s+are)\s+(?:the\s+)?(?:corrected|revised|edited|improved|updated|polished|rewritten)[^\n:]*[:\-—]\s*",
        r"^\s*(?:the\s+)?(?:corrected|revised|edited|improved|rewritten)\s+(?:text|version|sentence|paragraph)\s*(?:is|would\s+be)?\s*[:\-—]\s*",
        r"^\s*(?:corrected|revised|fixed|output|result)\s*[:\-—]\s*",
        r"^\s*sure[!\.,]?\s+here[^\n]*[:\-—]\s*",
        r"^\s*okay[!\.,]?\s+here[^\n]*[:\-—]\s*",
        r"^\s*(?:i(?:'ve|\s+have))\s+(?:corrected|fixed|revised|edited|rewritten)[^\n]*[:\-—]\s*",
    )
]

# Lines we drop entirely if they appear at the start of the response (labels
# for the model's own structured output that leaked through).
_LABEL_LINE_RE = re.compile(
    r"^\s*(?:original|input|before|raw|user)\s*[:\-—].*$",
    re.IGNORECASE | re.MULTILINE,
)

# Lines drop at the END if they're trailing explanations after the answer.
_TRAILING_EXPLANATION_RE = re.compile(
    r"\n\s*(?:explanation|note|notes?|changes?\s+made|what\s+changed|i\s+(?:changed|fixed|corrected|revised))\b.*\Z",
    re.IGNORECASE | re.DOTALL,
)

# The <<< >>> delimiters the prompt wraps the input in. If the model echoes
# them, peel them off.
_INPUT_DELIM_RE = re.compile(r"^<<<\s*\n?(.*?)\n?\s*>>>\s*$", re.DOTALL)


def strip_reasoning(text):
    """Remove <think>...</think> blocks emitted by reasoning models."""
    if not text:
        return text
    return _THINK_RE.sub("", text).strip()


def strip_fenced_block(text):
    """If the response contains a ``` code fence or \"\"\" triple-quoted block,
    pull out its inner content (favoring the last block, which is usually the answer)."""
    if not text:
        return text
    matches = _TRIPLE_QUOTE_RE.findall(text)
    if matches:
        return matches[-1].strip()
    matches = _FENCE_RE.findall(text)
    if matches:
        return matches[-1].strip()
    return text


def strip_wrapping_quotes(text):
    """Remove a single layer of matched quotes wrapping the entire string."""
    if not text or len(text) < 2:
        return text
    s = text.strip()
    for open_q, close_q in _QUOTE_PAIRS:
        if s.startswith(open_q) and s.endswith(close_q):
            inner = s[len(open_q): -len(close_q)].strip()
            if open_q not in inner and close_q not in inner:
                return inner
    return s


def strip_preambles(text):
    """Drop leading meta-phrases like "Here is the corrected text:" that small
    and medium models still emit despite explicit instructions not to."""
    if not text:
        return text
    s = text.lstrip()
    # Strip up to a few stacked preambles ("Sure! Here is the corrected text:").
    for _ in range(3):
        matched = False
        for pat in _PREAMBLE_PATTERNS:
            m = pat.match(s)
            if m:
                s = s[m.end():].lstrip()
                matched = True
                break
        if not matched:
            break
    return s


def strip_input_delimiters(text):
    """If the model echoed the prompt's <<< >>> wrapper around its answer,
    peel it back off."""
    if not text:
        return text
    m = _INPUT_DELIM_RE.match(text.strip())
    if m:
        return m.group(1).strip()
    return text


def strip_label_lines(text):
    """Drop "Original: ..." style label lines that sometimes precede the
    real answer when the model treats the task as a labeled transformation."""
    if not text:
        return text
    cleaned = _LABEL_LINE_RE.sub("", text)
    return cleaned.strip()


def strip_trailing_explanation(text):
    """Drop trailing meta commentary ("Changes made: ...") that some models
    append after the correction itself."""
    if not text:
        return text
    return _TRAILING_EXPLANATION_RE.sub("", text).rstrip()


def clean_llm_output(text):
    if not text:
        return text
    cleaned = strip_reasoning(text)
    cleaned = strip_fenced_block(cleaned)
    cleaned = strip_input_delimiters(cleaned)
    cleaned = strip_label_lines(cleaned)
    cleaned = strip_preambles(cleaned)
    cleaned = strip_trailing_explanation(cleaned)
    cleaned = strip_wrapping_quotes(cleaned)
    return cleaned.strip() if cleaned else cleaned
