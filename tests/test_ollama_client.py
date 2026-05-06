import unittest
from unittest.mock import patch, MagicMock
from ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):
    def test_generate_returns_response_text(self):
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Hello, world!"}

        with patch("ollama_client.requests.post", return_value=mock_response):
            result = client.generate("Fix this: hello world")

        self.assertEqual(result, "Hello, world!")

    def test_generate_returns_none_when_ollama_not_running(self):
        client = OllamaClient()

        with patch("ollama_client.requests.post", side_effect=Exception("Connection refused")):
            result = client.generate("Fix this")

        self.assertIsNone(result)

    def test_generate_uses_correct_model(self):
        client = OllamaClient(model="llama3.2:3b")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "fixed"}

        with patch("ollama_client.requests.post", return_value=mock_response) as mock_post:
            client.generate("test prompt")

        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["json"]["model"], "llama3.2:3b")

    def test_generate_sends_prompt_in_body(self):
        client = OllamaClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "ok"}

        with patch("ollama_client.requests.post", return_value=mock_response) as mock_post:
            client.generate("my prompt text")

        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["json"]["prompt"], "my prompt text")

    def test_custom_model_name(self):
        client = OllamaClient(model="mistral:7b")
        self.assertEqual(client.model, "mistral:7b")


if __name__ == "__main__":
    unittest.main()
