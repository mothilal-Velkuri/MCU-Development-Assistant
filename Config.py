# =============================================================
# config.py — Central settings for MCU Dev Assistant
# Designed for both Q&A mode and Code Generation mode.
# Only edit this file to change project-wide settings.
# =============================================================

import os
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
from dotenv import load_dotenv

load_dotenv()
# ── LLM Backend ───────────────────────────────────────────────
# "ollama"     → free local model, no API key needed
# "anthropic"  → Claude API, requires key in .env
LLM_BACKEND  = "ollama"
OLLAMA_MODEL = "mistral"
OLLAMA_URL   = "http://localhost:11434/api/chat"

# ── Anthropic (ignored when LLM_BACKEND = "ollama") ──────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = "claude-sonnet-4-20250514"

# ── Embedding Model ───────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── Vector Database ───────────────────────────────────────────
CHROMA_DB_PATH    = "./chroma_store"
CHROMA_COLLECTION = "mcu_docs"

# ── Chunking ──────────────────────────────────────────────────
CHUNK_SIZE    = 500
CHUNK_OVERLAP = 80
TOP_K_RESULTS = 6

# ── Document Types ────────────────────────────────────────────
DOC_TYPES = [
    "Datasheet",
    "User Manual",
    "Reference Manual",
    "Errata",
    "App Note",
]

# ── Paths ─────────────────────────────────────────────────────
DOCS_FOLDER          = "./docs"
GENERATED_CODE_PATH  = "./generated"

# ── Output Mode ───────────────────────────────────────────────
# "qa"   → Q&A with citations (current phase)
# "code" → generate C code from docs (Phase 8)
# "both" → answer + code in same response (Phase 9)
OUTPUT_MODE = "qa"

# ── Code Generation Settings (Phase 8) ───────────────────────
DEFAULT_MCU_FAMILY = ""        # e.g. "STM32F4"
TARGET_IDE         = ""        # e.g. "Keil", "STM32CubeIDE"
CODE_STYLE         = "bare_metal"  # "bare_metal", "hal", "cmsis"