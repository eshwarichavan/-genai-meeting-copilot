"""Session 3: chunking, local embeddings, a persistent vector store, top-k retrieval."""
import chromadb
from chromadb.utils import embedding_functions

from . import config

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
        ef = embedding_functions.DefaultEmbeddingFunction()
        _collection = _client.get_or_create_collection(
            config.COLLECTION_NAME, embedding_function=ef
        )
    return _collection


def _chunk_text(text: str, chunk_size: int = 220, overlap: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(chunk_size - overlap, 1)
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break
    return chunks


def add_meeting(meeting_id: str, title: str, date: str, summary_json: dict, transcript_text: str) -> None:
    collection = _get_collection()
    chunks = _chunk_text(transcript_text)

    documents = [summary_json["summary"]] + chunks
    metadatas = [{"meeting_id": meeting_id, "title": title, "date": date, "type": "summary"}]
    metadatas += [
        {"meeting_id": meeting_id, "title": title, "date": date, "type": "transcript_chunk", "chunk_index": i}
        for i in range(len(chunks))
    ]
    ids = [f"{meeting_id}-summary"] + [f"{meeting_id}-chunk-{i}" for i in range(len(chunks))]

    # Re-ingesting the same meeting_id should replace, not duplicate, its rows.
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)


def query(question: str, top_k: int | None = None) -> dict:
    collection = _get_collection()
    return collection.query(query_texts=[question], n_results=top_k or config.TOP_K)
