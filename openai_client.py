import requests
from text_utils import clean_llm_output


class OpenAICompatibleClient:
    def __init__(self, api_key, model="gpt-4o-mini", base_url="https://api.openai.com/v1", provider_name="OpenAI"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.provider_name = provider_name

    def generate(self, prompt):
        if not self.api_key:
            return None
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    # Low temperature for editing tasks — consistent, minimal
                    # rewrites rather than creative variation.
                    "temperature": 0.2,
                },
                timeout=30,
            )
            if response.status_code == 200:
                return clean_llm_output(response.json()["choices"][0]["message"]["content"].strip())
            return None
        except Exception:
            return None
