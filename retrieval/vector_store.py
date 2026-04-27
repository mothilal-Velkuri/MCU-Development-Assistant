# =============================================================
# retrieval/vector_store.py
# Stores document chunks as vectors and searches them.
#
# Why ChromaDB?
#   - Runs 100% locally — no server, no cloud
#   - Persistent — survives program restarts
#   - Fast — finds top-K similar chunks in milliseconds
#   - Simple API — add chunks, query by embedding
#
# Search functions:
#   search()              → all documents
#   search_errata_only()  → only Errata-labelled docs
#   search_by_doc_type()  → any specific doc type
#   search_by_source()    → specific PDF file
#
# All searches work across ALL indexed PDFs automatically.
# Adding more PDFs to docs/ improves answer quality.
# =============================================================

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

import chromadb
from Config import CHROMA_DB_PATH, CHROMA_COLLECTION, TOP_K_RESULTS
from retrieval.embedder import embed_texts, embed_query
from ingestion.chunker import Chunk


# =============================================================
# DATABASE CONNECTION
# =============================================================

def get_client() -> chromadb.PersistentClient:
    """
    Connect to the local ChromaDB database.
    Creates the database folder if it does not exist.
    """
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_collection(name: str = CHROMA_COLLECTION):
    """
    Get or create a ChromaDB collection.
    A collection is like a table — stores chunks + vectors.
    """
    client = get_client()
    return client.get_or_create_collection(
        name     = name,
        metadata = {"hnsw:space": "cosine"}   # use cosine similarity
    )


def get_chunk_count(collection_name: str = CHROMA_COLLECTION) -> int:
    """Return how many chunks are currently indexed."""
    return get_collection(collection_name).count()


# =============================================================
# INDEXING — Store chunks into ChromaDB
# =============================================================

def index_chunks(
    chunks: list[Chunk],
    collection_name: str = CHROMA_COLLECTION,
    clear_existing: bool = False
) -> int:
    """
    Embed all chunks and store them in ChromaDB.
    Call this once after parsing your PDFs.

    Parameters
    ----------
    chunks          : output from chunk_pages()
    collection_name : which ChromaDB collection to use
    clear_existing  : if True, wipe collection before indexing

    Returns
    -------
    Total number of chunks now in the collection.
    """
    collection = get_collection(collection_name)

    if clear_existing:
        client = get_client()
        client.delete_collection(collection_name)
        collection = get_collection(collection_name)
        print(f"  Cleared existing collection: {collection_name}")

    if not chunks:
        print("  No chunks to index.")
        return 0

    print(f"  Embedding {len(chunks)} chunks...")

    # Build unique IDs for each chunk
    # Format: filename_page_chunkindex
    ids = [
        f"{c.source_file}_p{c.page_num}_c{c.chunk_index}"
        for c in chunks
    ]

    texts     = [c.text for c in chunks]
    metadatas = [
        {
            "source"  : c.source_file,
            "doc_type": c.doc_type,
            "page"    : c.page_num,
        }
        for c in chunks
    ]

    # Embed all texts
    embeddings = embed_texts(texts)

    # ChromaDB works best with batches of 500
    batch_size = 500
    added      = 0

    for i in range(0, len(chunks), batch_size):
        batch_end = min(i + batch_size, len(chunks))

        collection.upsert(     # upsert = add or update if ID exists
            ids        = ids[i:batch_end],
            embeddings = embeddings[i:batch_end],
            documents  = texts[i:batch_end],
            metadatas  = metadatas[i:batch_end],
        )
        added += batch_end - i

        # Progress report for large documents
        if len(chunks) > 200:
            print(f"    Indexed {added}/{len(chunks)} chunks...")

    total = collection.count()
    print(f"  ✅ Indexed {added} new chunks. "
          f"Total in DB: {total}")
    return total


# =============================================================
# SEARCH — Find relevant chunks for a query
# =============================================================

def search(
    query: str,
    collection_name: str = CHROMA_COLLECTION,
    top_k: int = TOP_K_RESULTS,
    filter_doc_type: str = None
) -> list[dict]:
    """
    Find the most relevant chunks for a given query.
    Searches ALL indexed documents by default.

    Parameters
    ----------
    query           : user question e.g. "PLL config 168 MHz"
    collection_name : which collection to search
    top_k           : how many chunks to return
    filter_doc_type : optional — restrict by doc type
                      e.g. "Errata", "Reference Manual"

    Returns
    -------
    List of dicts, each containing:
        text     : the chunk content
        source   : source filename
        doc_type : document type label
        page     : page number
        score    : similarity score 0.0-1.0
    """
    collection = get_collection(collection_name)

    if collection.count() == 0:
        print("  ⚠️  Vector DB is empty. Run index_chunks() first.")
        return []

    # Embed the query
    query_embedding = embed_query(query)

    # Build optional filter
    where = None
    if filter_doc_type:
        where = {"doc_type": {"$eq": filter_doc_type}}

    # Search ChromaDB
    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = min(top_k, collection.count()),
        include          = ["documents", "metadatas", "distances"],
        where            = where,
    )

    # Format results
    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text"    : doc,
            "source"  : meta["source"],
            "doc_type": meta["doc_type"],
            "page"    : meta["page"],
            "score"   : round(1.0 - dist, 4),
        })

    return hits


# =============================================================
# FILTERED SEARCH HELPERS
# =============================================================

def search_errata_only(
    query: str,
    top_k: int = TOP_K_RESULTS
) -> list[dict]:
    """
    Search ONLY errata documents for known silicon bugs.

    Works across ALL errata PDFs in docs/ — not just one file.
    Any PDF labelled doc_type="Errata" is included.

    Example
    -------
    search_errata_only("DMA AHB APB concurrent access")
    → Finds errata across STM32F407_ERRATE.pdf,
      STM32F429_ERRATE.pdf, etc. if all are indexed.
    """
    return search(
        query,
        filter_doc_type = "Errata",
        top_k           = top_k
    )


def search_by_doc_type(
    query: str,
    doc_type: str,
    top_k: int = TOP_K_RESULTS
) -> list[dict]:
    """
    Search only documents of a specific type.

    Parameters
    ----------
    doc_type : one of:
               "Datasheet"        — electrical specs, pinout
               "Reference Manual" — register-level details
               "User Manual"      — usage and configuration
               "Errata"           — known silicon bugs
               "App Note"         — application examples

    Example
    -------
    search_by_doc_type("PLL configuration", "Reference Manual")
    → Only searches Reference Manual chunks from all
      reference manual PDFs in docs/ folder.
    """
    return search(
        query,
        filter_doc_type = doc_type,
        top_k           = top_k
    )


def search_by_source(
    query: str,
    source_file: str,
    top_k: int = TOP_K_RESULTS
) -> list[dict]:
    """
    Search only a specific PDF file by its filename.

    Useful when you have datasheets for multiple controllers
    and want to restrict answers to one specific document.

    Parameters
    ----------
    source_file : exact filename e.g. "RM0090.pdf"
                  Must match the filename in docs/ folder.

    Example
    -------
    search_by_source("USART baud rate", "RM0090.pdf")
    → Only searches chunks from RM0090.pdf specifically.
    """
    collection = get_collection()

    if collection.count() == 0:
        print("  ⚠️  Vector DB is empty.")
        return []

    query_embedding = embed_query(query)

    results = collection.query(
        query_embeddings = [query_embedding],
        n_results        = min(top_k, collection.count()),
        include          = ["documents", "metadatas", "distances"],
        where            = {"source": {"$eq": source_file}},
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text"    : doc,
            "source"  : meta["source"],
            "doc_type": meta["doc_type"],
            "page"    : meta["page"],
            "score"   : round(1.0 - dist, 4),
        })
    return hits


# =============================================================
# UTILITIES
# =============================================================

def list_indexed_sources(
    collection_name: str = CHROMA_COLLECTION
) -> list[str]:
    """
    Return a list of unique source files currently indexed.
    Useful to confirm which PDFs have been ingested.

    Returns
    -------
    Sorted list of filenames e.g.
    ['RM0090.pdf', 'STM32F407_ERRATE.pdf', 'datasheet.pdf']
    """
    collection = get_collection(collection_name)

    if collection.count() == 0:
        return []

    result = collection.get(
        limit   = collection.count(),
        include = ["metadatas"],
    )

    sources = sorted(set(
        m["source"] for m in result["metadatas"]
    ))
    return sources


def list_indexed_doc_types(
    collection_name: str = CHROMA_COLLECTION
) -> dict[str, int]:
    """
    Return count of chunks per doc_type.
    Useful to see what document types are indexed.

    Returns
    -------
    Dict e.g.
    {
        "Reference Manual" : 850,
        "Errata"           : 429,
        "Datasheet"        : 312,
    }
    """
    collection = get_collection(collection_name)

    if collection.count() == 0:
        return {}

    result = collection.get(
        limit   = collection.count(),
        include = ["metadatas"],
    )

    counts: dict[str, int] = {}
    for m in result["metadatas"]:
        dt = m.get("doc_type", "Unknown")
        counts[dt] = counts.get(dt, 0) + 1

    return dict(sorted(counts.items()))


def clear_collection(
    collection_name: str = CHROMA_COLLECTION
) -> None:
    """
    Delete all chunks from the collection.
    Use this when you want to re-index from scratch.
    """
    client = get_client()
    client.delete_collection(collection_name)
    print(f"  Collection '{collection_name}' cleared.")