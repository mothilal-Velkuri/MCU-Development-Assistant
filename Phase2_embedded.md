following steps are involved in embedded vector.
retrieval\embedder.py      ← Step 1
retrieval\vector_store.py  ← Step 2
test_embedder.py           ← Step 3
test_vector_store.py       ← Step 4

**Step 1:**  **creating Embedder.py**
  create embedded.py under retrieval folder and copy below code.
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
**Step 2:**  **Vector_store.py**
  create vector_store.py file and copy below script.
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
  # How it works:
  #   index_chunks() → embeds all chunks → saves to disk
  #   search()       → embeds query → finds closest chunks
  #                 → LLM reads those chunks to answer
  # =============================================================
  
  import chromadb
  from chromadb.config import Settings
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
      chunks         : output from chunk_pages()
      collection_name: which ChromaDB collection to use
      clear_existing : if True, wipe the collection before indexing
  
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
  
      Parameters
      ----------
      query          : user question e.g. "PLL configuration 168 MHz"
      collection_name: which collection to search
      top_k          : how many chunks to return
      filter_doc_type: optional filter e.g. "Errata" to search only errata
  
      Returns
      -------
      List of dicts, each containing:
          text     : the chunk content
          source   : source filename
          doc_type : document type label
          page     : page number
          score    : similarity score 0.0-1.0 (higher = more relevant)
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
              "score"   : round(1.0 - dist, 4),  # distance → similarity
          })
  
      return hits
  
  
  def search_errata_only(query: str) -> list[dict]:
      """
      Convenience function — search only errata documents.
      Used by the LLM to check for known silicon bugs.
      """
      return search(query, filter_doc_type="Errata")
  
  
  # =============================================================
  # UTILITIES
  # =============================================================
  
  def list_indexed_sources(
      collection_name: str = CHROMA_COLLECTION
  ) -> list[str]:
      """
      Return a list of unique source files currently indexed.
      Useful to confirm which PDFs have been ingested.
      """
      collection = get_collection(collection_name)
  
      if collection.count() == 0:
          return []
  
      # Fetch a sample to get metadata
      result = collection.get(
          limit   = collection.count(),
          include = ["metadatas"],
      )
  
      sources = sorted(set(
          m["source"] for m in result["metadatas"]
      ))
      return sources
  
  
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
