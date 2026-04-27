# test_client.py — Phase 3 Test 2
# Run: python test_client.py
# NOTE: Requires Ollama to be running with mistral model

from llm.client import (
    ask_llm, stream_llm,
    check_ollama_running,
    check_model_available,
)
from llm.prompts import build_context_block

print("=" * 50)
print("CLIENT.PY TEST")
print("=" * 50)

# ── Test 1: Ollama server check ────────────────────────────
print("\nTest 1 — Ollama server running")
running = check_ollama_running()
print(f"  Ollama running  : {running}")
if not running:
    print("  ❌ FAIL — Start Ollama first: ollama serve")
    exit()
print(f"  PASS")

# ── Test 2: Model available ────────────────────────────────
print("\nTest 2 — Mistral model available")
available = check_model_available("mistral")
print(f"  Mistral available: {available}")
if not available:
    print("  ❌ FAIL — Run: ollama pull mistral")
    exit()
print(f"  PASS")

# ── Test 3: Basic LLM response ────────────────────────────
print("\nTest 3 — Basic LLM response")
print("  Sending test message to Ollama...")
response = ask_llm(
    system_prompt = (
        "You are a helpful assistant. "
        "Reply only with exactly what is asked. "
        "No extra words."
    ),
    conversation_history = [],
    user_message = "Reply with only the word: CONNECTED",
)
print(f"  Response        : '{response.strip()}'")
pass3 = "CONNECTED" in response.upper()
print(f"  PASS" if pass3 else "  FAIL — unexpected response")

# ── Test 4: Document grounded response ────────────────────
print("\nTest 4 — Document grounded response")
chunks = [
    {
        "text"    : "Section 6.3.2: To configure PLL for 168 MHz, "
                    "set RCC_PLLCFGR register: PLLM=8, PLLN=168, "
                    "PLLP=0 (div by 2). Input must be HSE 8 MHz. "
                    "Flash latency must be set to 5 WS.",
        "source"  : "RM0090.pdf",
        "doc_type": "Reference Manual",
        "page"    : 148,
        "score"   : 0.95,
    }
]
ctx = build_context_block(chunks)
system = f"""You are an embedded systems assistant.
STRICT RULE: Only use information from the DOCUMENT CONTEXT.
Always cite the source file and page number.

DOCUMENT CONTEXT:
{ctx}"""

response = ask_llm(
    system_prompt        = system,
    conversation_history = [],
    user_message         = (
        "What value should PLLM be set to for 168 MHz? "
        "Cite your source."
    ),
)
print(f"  Question: What value for PLLM at 168 MHz?")
print(f"  Response preview: {response[:200]}")
has_pllm  = "PLLM" in response or "pllm" in response.lower()
has_val   = "8" in response
has_cite  = "RM0090" in response or "148" in response
print(f"  Mentions PLLM   : {has_pllm}")
print(f"  Mentions value 8: {has_val}")
print(f"  Cites source    : {has_cite}")
pass4 = has_pllm and has_val
print(f"  PASS" if pass4 else "  FAIL — check LLM response")

# ── Test 5: Conversation history ──────────────────────────
print("\nTest 5 — Conversation history maintained")
history = [
    {"role": "user",      "content": "My target frequency is 168 MHz"},
    {"role": "assistant", "content": "Understood. 168 MHz target noted."},
]
response2 = ask_llm(
    system_prompt        = "You are a helpful assistant. Be very brief.",
    conversation_history = history,
    user_message         = "What target frequency did I mention?",
)
print(f"  Response: {response2.strip()[:100]}")
remembers = "168" in response2
print(f"  Remembers 168 MHz: {remembers}")
print(f"  PASS" if remembers else "  FAIL")

# ── Test 6: Streaming ─────────────────────────────────────
print("\nTest 6 — Streaming response")
print("  Streaming: ", end="", flush=True)
full_response = ""
token_count   = 0
for token in stream_llm(
    system_prompt        = "Be very brief. One sentence only.",
    conversation_history = [],
    user_message         = "Say: STREAMING WORKS",
):
    print(token, end="", flush=True)
    full_response += token
    token_count   += 1
print()
print(f"  Tokens received : {token_count}")
pass6 = token_count > 0 and len(full_response) > 0
print(f"  PASS" if pass6 else "  FAIL")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 50)
all_ok = pass3 and pass4 and remembers and pass6
print("RESULT: client.py OK ✅" if all_ok
      else "RESULT: client.py FAILED ❌")
print("=" * 50)