import requests
from text_utils import clean_llm_output


class OllamaClient:
    def __init__(self, model="llama3.2:3b", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt):
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    # Keep the model resident in memory between requests so the
                    # next correction doesn't pay the cold-start cost.
                    "keep_alive": "30m",
                    # Low temperature for editing tasks — we want consistent,
                    # minimal rewrites, not creative reinterpretations.
                    "options": {
                        "temperature": 0.2,
                        "top_p": 0.9,
                    },
                },
                timeout=180,
            )
            if response.status_code == 200:
                return clean_llm_output(response.json().get("response", "").strip())
            return None
        except Exception:
            return None

    def warm_up(self, timeout=60):
        """Fire a no-op request to load the model into memory.

        Returns True on success. Safe to call from a background thread on
        app start so the first real correction doesn't hit cold-start latency.
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "",
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {"num_predict": 1},
                },
                timeout=timeout,
            )
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def list_installed_models(base_url="http://localhost:11434", timeout=2):
        """Query Ollama for locally-installed models. Returns [] on failure."""
        _, models = OllamaClient.get_status(base_url=base_url, timeout=timeout)
        return models

    @staticmethod
    def get_status(base_url="http://localhost:11434", timeout=2):
        """Return (is_running, [model_names]).

        is_running=False means the daemon couldn't be reached.
        is_running=True with an empty list means Ollama is up but no models pulled.
        """
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=timeout)
            if response.status_code != 200:
                return (False, [])
            data = response.json() or {}
            names = [m.get("name") for m in data.get("models", []) if m.get("name")]
            return (True, names)
        except Exception:
            return (False, [])
