"""Ollama LLM provider implementation."""

import json
import logging
import urllib.error
import urllib.request
from typing import Iterator, Optional, Tuple

from src.common.config.settings import get_settings
from src.common.errors.exceptions import LLMProviderError
from src.rag.llm.base import BaseLLMProvider

logger = logging.getLogger("eakap.rag.llm.ollama")


class OllamaLLMProvider(BaseLLMProvider):
    """Generate responses using a locally hosted Ollama HTTP API."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._model = model or getattr(settings, "LLM_MODEL_NAME", "llama3.2")

    @property
    def provider_name(self) -> str:
        """Return the provider identifier."""
        return "ollama"

    @property
    def model_name(self) -> str:
        """Return the configured Ollama model name."""
        return self._model

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Tuple[str, int, int]:
        """Generate one non-streaming completion from Ollama."""
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        response = self._post_json("/api/generate", payload, timeout=60)
        text = str(response.get("response", "")).strip()
        prompt_tokens = int(response.get("prompt_eval_count", max(1, len(prompt) // 4)))
        completion_tokens = int(response.get("eval_count", max(1, len(text) // 4 if text else 0)))
        logger.info(
            "Ollama generation completed | model=%s | prompt_tokens=%s | completion_tokens=%s",
            self._model,
            prompt_tokens,
            completion_tokens,
        )
        return text, prompt_tokens, completion_tokens

    def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> Iterator[str]:
        """Stream generated text fragments from Ollama."""
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        request = self._build_request("/api/generate", payload)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    fragment = data.get("response")
                    if fragment:
                        yield str(fragment)
                    if data.get("done") is True:
                        break
        except urllib.error.URLError as exc:
            raise LLMProviderError(message="Ollama streaming request failed.", original_exception=exc)
        except Exception as exc:
            raise LLMProviderError(message="Unexpected Ollama streaming failure.", original_exception=exc)

    def _post_json(self, endpoint: str, payload: dict, timeout: int) -> dict:
        """Post JSON to Ollama and return the decoded response body."""
        request = self._build_request(endpoint, payload)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise LLMProviderError(message="Ollama generation request failed.", original_exception=exc)
        except Exception as exc:
            raise LLMProviderError(message="Unexpected Ollama generation failure.", original_exception=exc)

    def _build_request(self, endpoint: str, payload: dict) -> urllib.request.Request:
        """Build a JSON POST request for an Ollama endpoint."""
        return urllib.request.Request(
            f"{self._base_url}{endpoint}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
