import requests


class OpenAIClient:
    def __init__(self, api_key, model="gpt-4o-mini", base_url="https://api.openai.com/v1"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def generate(self, prompt):
        if not self.api_key:
            print("[OpenAI] No API key configured")
            return None
        try:
            print(f"[OpenAI] Sending request to {self.model}...")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
                timeout=30,
            )
            if response.status_code == 200:
                result = response.json()["choices"][0]["message"]["content"].strip()
                print(f"[OpenAI] Got response: {result[:80]}...")
                return result
            print(f"[OpenAI] Error {response.status_code}: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"[OpenAI] Exception: {e}")
            return None
