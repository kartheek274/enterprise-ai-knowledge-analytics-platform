import abc
import json
import urllib.request
import urllib.error
from typing import List
from src.common.config.settings import get_settings
from src.common.errors.exceptions import ConfigurationError

class BaseEmbeddingProvider(abc.ABC):
    """
    Abstract Interface defining essential embedding methods.
    Hides internal provider SDK calls from ingestion components.
    """
    
    @abc.abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Calculates embeddings for multiple document strings."""
        pass
        
    @abc.abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Calculates embedding for a single prompt query."""
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Lightweight, deterministic mock embedding generator.
    Avoids loading heavy deep-learning frameworks in testing environments.
    """
    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def _generate_vector(self, text: str) -> List[float]:
        import hashlib
        checksum = hashlib.md5(text.encode("utf-8")).digest()
        vector = []
        for i in range(self.dimension):
            byte_val = float(checksum[i % 16]) / 255.0
            # Generate negative and positive float distributions deterministically
            vector.append(byte_val * (1.0 if i % 2 == 0 else -1.0))
        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._generate_vector(text)


class SentenceTransformersProvider(BaseEmbeddingProvider):
    """
    Local embedding provider leveraging PyTorch/SentenceTransformers.
    """
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError as e:
            raise ConfigurationError(
                message="Failed to initialize Local Embeddings. 'sentence-transformers' package is missing.",
                original_exception=e
            )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode(text)
        return embedding.tolist()


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """
    HTTP integration provider routing embedding calls to a local Ollama server.
    """
    def __init__(self, base_url: str, model_name: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def _post_request(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = json.dumps({"model": self.model_name, "prompt": text}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                return resp_data["embedding"]
        except urllib.error.URLError as e:
            raise ConfigurationError(
                message=f"Failed to connect to Ollama service at endpoint: {url}",
                original_exception=e
            )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._post_request(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._post_request(text)


class EmbeddingService:
    """
    Centralized controller selecting and executing the active embedding adapter.
    """
    def __init__(self) -> None:
        settings = get_settings()
        provider = settings.EMBEDDING_PROVIDER.lower()
        model_name = settings.EMBEDDING_MODEL_NAME

        # Force mock provider in test context to avoid network/model initialization overheads
        if settings.APP_ENV == "testing" or provider in ["mock", "testing"]:
            self.provider: BaseEmbeddingProvider = MockEmbeddingProvider()
        elif provider == "sentence-transformers":
            self.provider = SentenceTransformersProvider(model_name)
        elif provider == "ollama":
            self.provider = OllamaEmbeddingProvider(settings.OLLAMA_BASE_URL, model_name)
        else:
            raise ConfigurationError(
                message=f"Unknown embedding provider: '{provider}'."
            )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Calculates embeddings for a list of texts."""
        if not texts:
            return []
        return self.provider.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Calculates embedding for a query string."""
        return self.provider.embed_query(text)
