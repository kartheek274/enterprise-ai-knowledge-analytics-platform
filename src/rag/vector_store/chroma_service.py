import logging
import math
from typing import List, Dict, Any, Optional
from src.common.config.settings import get_settings
from src.common.errors.exceptions import DatabaseConnectionError

logger = logging.getLogger("eakap.database.chroma")


class _InMemoryCollection:
    """Minimal Chroma-compatible collection used when local ChromaDB is unavailable."""

    def __init__(self, name: str, store: Dict[str, Dict[str, Any]]) -> None:
        self.name = name
        self._store = store

    def add(
        self,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        for index, doc_id in enumerate(ids):
            self._store[doc_id] = {
                "document": documents[index],
                "embedding": embeddings[index],
                "metadata": metadatas[index],
            }

    def count(self) -> int:
        return len(self._store)


class _InMemoryChromaClient:
    """Small vector-store fallback with the subset of Chroma APIs this project uses."""

    _collections: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def get_or_create_collection(self, name: str) -> _InMemoryCollection:
        self._collections.setdefault(name, {})
        return _InMemoryCollection(name, self._collections[name])

    def get_collection(self, name: str) -> _InMemoryCollection:
        if name not in self._collections:
            raise KeyError(f"Collection '{name}' does not exist.")
        return _InMemoryCollection(name, self._collections[name])

    def delete_collection(self, name: str) -> None:
        self._collections.pop(name, None)

    def list_collections(self) -> List[_InMemoryCollection]:
        return [
            _InMemoryCollection(name, store)
            for name, store in self._collections.items()
        ]

    def query(
        self,
        name: str,
        query_embedding: List[float],
        n_results: int,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        rows = []
        for doc_id, record in self._collections.get(name, {}).items():
            metadata = record["metadata"]
            if where_filter and any(metadata.get(key) != value for key, value in where_filter.items()):
                continue
            distance = math.dist(query_embedding, record["embedding"])
            rows.append(
                {
                    "id": doc_id,
                    "document": record["document"],
                    "metadata": metadata,
                    "distance": distance,
                }
            )
        rows.sort(key=lambda row: row["distance"])
        return rows[:n_results]


class ChromaService:
    """
    Service wrapper for a Persistent ChromaDB Vector Store.
    Encapsulates all vector space modifications, indexes, and similarity queries.
    """
    
    def __init__(self) -> None:
        settings = get_settings()
        self.chroma_dir = str(settings.CHROMA_DB_DIR.resolve())
        self._use_fallback = False
        try:
            import chromadb
            # Instantiate persistent client linking to local disk paths
            self.client = chromadb.PersistentClient(path=self.chroma_dir)
        except Exception as e:
            logger.warning(
                "ChromaDB initialization failed; using in-memory vector store fallback: %s",
                str(e),
            )
            self.client = _InMemoryChromaClient()
            self._use_fallback = True

    def create_collection(self, name: str) -> Any:
        """
        Creates a collection, returning the collection object.
        """
        try:
            return self.client.get_or_create_collection(name=name)
        except Exception as e:
            raise DatabaseConnectionError(
                message=f"Failed to create/get collection '{name}' in ChromaDB.",
                original_exception=e
            )

    def delete_collection(self, name: str) -> None:
        """
        Deletes the target collection from storage metadata.
        """
        try:
            self.client.delete_collection(name=name)
            logger.info(f"Deleted collection '{name}' from ChromaDB.")
        except Exception as e:
            raise DatabaseConnectionError(
                message=f"Failed to delete collection '{name}' from ChromaDB.",
                original_exception=e
            )

    def list_collections(self) -> List[str]:
        """
        Returns a list of all existing collection names.
        """
        try:
            return [col.name for col in self.client.list_collections()]
        except Exception as e:
            raise DatabaseConnectionError(
                message="Failed to retrieve ChromaDB collection index listings.",
                original_exception=e
            )

    def count_documents(self, collection_name: str) -> int:
        """
        Returns the number of elements contained in the target collection.
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception as e:
            raise DatabaseConnectionError(
                message=f"Failed to count documents in collection '{collection_name}'.",
                original_exception=e
            )

    def add_documents(
        self,
        collection_name: str,
        ids: List[str],
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        Inserts document segments, text embeddings, and corresponding metadata records.
        """
        try:
            collection = self.client.get_collection(name=collection_name)
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            logger.info(f"Successfully inserted {len(ids)} entries into collection '{collection_name}'.")
        except Exception as e:
            raise DatabaseConnectionError(
                message=f"ChromaDB insert failed on collection '{collection_name}'.",
                original_exception=e
            )

    def similarity_search(
        self,
        collection_name: str,
        query_embedding: List[float],
        n_results: int = 5,
        where_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a vector query and returns nearest neighbor document matches.
        """
        try:
            if self._use_fallback:
                return self.client.query(
                    name=collection_name,
                    query_embedding=query_embedding,
                    n_results=n_results,
                    where_filter=where_filter,
                )

            collection = self.client.get_collection(name=collection_name)
            query_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter
            )
            
            # Format raw Chroma outputs into clean maps
            formatted_matches = []
            if query_results and query_results.get("ids") and len(query_results["ids"]) > 0:
                ids = query_results["ids"][0]
                docs = query_results["documents"][0]
                metas = query_results["metadatas"][0]
                dists = query_results["distances"][0] if query_results.get("distances") else [0.0] * len(ids)
                
                for idx in range(len(ids)):
                    formatted_matches.append({
                        "id": ids[idx],
                        "document": docs[idx],
                        "metadata": metas[idx],
                        "distance": dists[idx]
                    })
            return formatted_matches
        except Exception as e:
            raise DatabaseConnectionError(
                message=f"Vector search failed on collection '{collection_name}'.",
                original_exception=e
            )

    def get_all_chunks(self, collection_name: str = "healthcare_knowledge") -> List[Dict[str, Any]]:
        """
        Retrieves all document content, IDs, and metadata from the specified collection.
        """
        try:
            if self._use_fallback:
                store = self.client._collections.get(collection_name, {})
                return [
                    {
                        "id": doc_id,
                        "document": record["document"],
                        "metadata": record["metadata"],
                    }
                    for doc_id, record in store.items()
                ]

            collection = self.client.get_collection(name=collection_name)
            data = collection.get(include=["documents", "metadatas"])
            results = []
            if data and data.get("ids"):
                ids = data["ids"]
                docs = data.get("documents") or [""] * len(ids)
                metas = data.get("metadatas") or [{}] * len(ids)
                for idx in range(len(ids)):
                    results.append({
                        "id": ids[idx],
                        "document": docs[idx],
                        "metadata": metas[idx] or {},
                    })
            return results
        except Exception as e:
            logger.warning(f"Could not retrieve chunks from collection '{collection_name}': {e}")
            return []
