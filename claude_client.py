import requests


class ClaudeClient:
    def __init__(self, api_key, model="claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt):
        if not self.api_key:
            print("[Claude] No API key configured")
            return None
        try:
            print(f"[Claude] Sending request to {self.model}...")
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            if response.status_code == 200:
                result = response.json()["content"][0]["text"].strip()
                print(f"[Claude] Got response: {result[:80]}...")
                return result
            print(f"[Claude] Error {response.status_code}: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"[Claude] Exception: {e}")
            return None
