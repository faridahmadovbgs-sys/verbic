import requests


class OpenAICompatibleClient:
    def __init__(self, api_key, model="gpt-4o-mini", base_url="https://api.openai.com/v1", provider_name="OpenAI"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.provider_name = provider_name

    def generate(self, prompt):
        if not self.api_key:
            print(f"[{self.provider_name}] No API key configured")
            return None
        try:
            print(f"[{self.provider_name}] Sending request to {self.model}...")
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
                print(f"[{self.provider_name}] Got response: {result[:80]}...")
                return result
            print(f"[{self.provider_name}] Error {response.status_code}: {response.text[:200]}")
            return None
        except Exception as e:
            print(f"[{self.provider_name}] Exception: {e}")
            return None
