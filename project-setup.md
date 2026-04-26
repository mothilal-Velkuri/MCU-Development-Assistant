**Step 1:**
    run in cd C:\mcu_assistant.
    create empty folders for setup.
      mkdir ingestion
      mkdir retrieval
      mkdir llm
      mkdir workflow
      mkdir docs
    create __init__.py file in each directory and verify (except in docs directory).
**Step 2:**
    Create config.py
Copy below code and save in config.py
      # =============================================================
      # config.py — Central settings for MCU Dev Assistant
      # All project-wide constants are defined here.
      # =============================================================
      
      import os
      from dotenv import load_dotenv
      
      # Load .env file — reads ANTHROPIC_API_KEY if present
      load_dotenv()
      
      # ── LLM Backend ───────────────────────────────────────────────
      # "ollama"     → free local model, no API key needed
      # "anthropic"  → Claude API, requires ANTHROPIC_API_KEY in .env
      LLM_BACKEND = "ollama"
      
      # ── Ollama Settings ───────────────────────────────────────────
      OLLAMA_MODEL = "mistral"
      OLLAMA_URL   = "http://localhost:11434/api/chat"
      
      # ── Anthropic Settings (ignored when LLM_BACKEND = "ollama") ──
      ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
      ANTHROPIC_MODEL   = "claude-sonnet-4-20250514"
      
      # ── Embedding Model ───────────────────────────────────────────
      # Runs locally — downloaded once to ~/.cache
      # No internet needed after first download
      EMBEDDING_MODEL = "all-MiniLM-L6-v2"
      
      # ── Vector Database ───────────────────────────────────────────
      # ChromaDB stores all document chunks on disk here
      CHROMA_DB_PATH      = "./chroma_store"
      CHROMA_COLLECTION   = "mcu_docs"
      
      # ── Chunking Settings ─────────────────────────────────────────
      # CHUNK_SIZE    : characters per chunk (500 is a good balance)
      # CHUNK_OVERLAP : overlap between chunks (preserves context
      #                 at boundaries — important for register tables)
      CHUNK_SIZE    = 500
      CHUNK_OVERLAP = 80
      
      # ── Retrieval Settings ────────────────────────────────────────
      # How many chunks to retrieve per query
      # More = more context for LLM but slower
      TOP_K_RESULTS = 6
      
      # ── Document Types ────────────────────────────────────────────
      # Valid labels for uploaded PDF documents
      DOC_TYPES = [
          "Datasheet",
          "User Manual",
          "Reference Manual",
          "Errata",
          "App Note",
      ]
      
      # ── Paths ─────────────────────────────────────────────────────
      DOCS_FOLDER = "./docs"
      
