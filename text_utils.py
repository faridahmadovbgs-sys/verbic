"""Post-processing helpers for LLM responses."""
import re


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_QUOTE_PAIRS = (('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"))
# Match content inside ```code fences``` or """triple-quoted blocks""".
_FENCE_RE = re.compile(r'```(?:\w+)?\s*\n?(.+?)\n?```', re.DOTALL)
_TRIPLE_QUOTE_RE = re.compile(r'"""\s*(.+?)\s*"""', re.DOTALL)


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


def clean_llm_output(text):
    if not text:
        return text
    return strip_wrapping_quotes(strip_fenced_block(strip_reasoning(text)))
