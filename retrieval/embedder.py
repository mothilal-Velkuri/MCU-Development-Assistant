# =============================================================
# retrieval/embedder.py
# Converts text into numerical vectors (embeddings).
#
# Why embeddings?
#   "PLL clock multiplier" and "phase-locked loop frequency"
#   mean the same thing but share no words. Embeddings capture
#   meaning so similarity search works across paraphrases.
#   This is what makes RAG better than keyword search.
#
# Model: all-MiniLM-L6-v2
#   - Size        : ~90 MB (downloads once, cached locally)
#   - Output dim  : 384 floats per chunk
#   - Speed       : ~500 chunks/sec on CPU
#   - No internet needed after first download
# =============================================================

from sentence_transformers import SentenceTransformer
from Config import EMBEDDING_MODEL
import numpy as np

# ── Singleton model — loaded once at startup ──────────────────
# Loading takes ~2 seconds. Keeping it global avoids
# reloading on every function call.
_model = None


def get_embedder() -> SentenceTransformer:
    """
    Load the embedding model (once).
    Subsequent calls return the already-loaded model.
    """
    global _model
    if _model is None:
        print(f"  Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"  Model loaded. Output dimension: "
              f"{_model.get_sentence_embedding_dimension()}")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a list of text strings into embedding vectors.
    Used during document indexing.

    Parameters
    ----------
    texts : list of strings (your document chunks)

    Returns
    -------
    list of float vectors — one per input text
    Each vector has 384 dimensions.
    """
    if not texts:
        return []

    model = get_embedder()

    # Batch encode — much faster than encoding one at a time
    vectors = model.encode(
        texts,
        batch_size        = 32,
        show_progress_bar = len(texts) > 100,
        convert_to_numpy  = True,
    )

    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    """
    Convert a single user query into an embedding vector.
    Used at search time.

    Parameters
    ----------
    query : the user's question

    Returns
    -------
    A single float vector of 384 dimensions.
    """
    model = get_embedder()
    vector = model.encode(query, convert_to_numpy=True)
    return vector.tolist()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Measure how similar two vectors are.
    Returns a score between 0.0 (different) and 1.0 (identical).
    Used in testing to verify embedding quality.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))