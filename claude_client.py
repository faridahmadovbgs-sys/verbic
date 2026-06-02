import requests
from text_utils import clean_llm_output
from version import APP_VERSION


class ClaudeClient:
    def __init__(self, api_key, model="claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt):
        if not self.api_key:
            return None
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                    "User-Agent": f"Verbic/{APP_VERSION}",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    # Low temperature for editing tasks — consistent, minimal
                    # rewrites rather than creative variation.
                    "temperature": 0.2,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            if response.status_code == 200:
                return clean_llm_output(response.json()["content"][0]["text"].strip())
            return None
        except Exception:
            return None
