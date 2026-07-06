"""Embedding + ChromaDB semantic search with citations.

Heavy dependencies (sentence-transformers, chromadb) are imported lazily
so the rest of the app and tests load fast.
"""
from __future__ import annotations

from . import config, repository

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        import chromadb

        client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        _collection = client.get_or_create_collection(
            config.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def index_insight(insight_id: str, text: str, metadata: dict) -> None:
    """Embed an approved insight and store it for semantic search."""
    embedding = _get_model().encode(text).tolist()
    _get_collection().upsert(
        ids=[insight_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata],
    )


def search(query: str, top_k: int = 5) -> list[dict]:
    """Return cited matches: each has insight text, metadata, similarity."""
    query_emb = _get_model().encode(query).tolist()
    res = _get_collection().query(query_embeddings=[query_emb], n_results=top_k)

    ids = res.get("ids", [[]])[0]
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]

    results = []
    for _id, doc, meta, dist in zip(ids, docs, metas, dists):
        results.append({
            "insight_id": _id,
            "insight": doc,
            "metadata": meta or {},
            "similarity": round(1.0 - float(dist), 3),  # cosine distance -> similarity
        })

    repository.log_search(query, ids)
    return results
