# test_embedder.py — Phase 2 Test 1
# Run: python test_embedder.py

from retrieval.embedder import (
    get_embedder, embed_texts,
    embed_query, cosine_similarity
)

print("=" * 50)
print("EMBEDDER.PY TEST")
print("=" * 50)

# ── Test 1: Model loads ────────────────────────────────────
print("\nTest 1 — Model loading")
model = get_embedder()
dim = model.get_sentence_embedding_dimension()
print(f"  Model loaded     : OK")
print(f"  Output dimension : {dim}")
print(f"  PASS" if dim == 384 else "  FAIL — expected 384")

# ── Test 2: Single query embedding ────────────────────────
print("\nTest 2 — Single query embedding")
vec = embed_query("PLL clock configuration STM32")
print(f"  Vector length    : {len(vec)}")
print(f"  First 5 values   : {[round(v,4) for v in vec[:5]]}")
print(f"  PASS" if len(vec) == 384 else "  FAIL")

# ── Test 3: Batch text embedding ──────────────────────────
print("\nTest 3 — Batch text embedding")
texts = [
    "Configure PLL multiplier for 168 MHz system clock",
    "USART baud rate register BRR configuration",
    "ADC conversion sequencer modification",
    "SPI BSY flag behavior in slave mode",
    "RCC peripheral clock enable delay",
]
vectors = embed_texts(texts)
print(f"  Input texts      : {len(texts)}")
print(f"  Output vectors   : {len(vectors)}")
print(f"  Each dim         : {len(vectors[0])}")
print(f"  PASS" if len(vectors) == 5 and len(vectors[0]) == 384
      else "  FAIL")

# ── Test 4: Similarity — related texts ────────────────────
print("\nTest 4 — Semantic similarity (related texts)")
q1 = "PLL phase locked loop clock multiplier"
q2 = "configure system clock frequency using PLL"
q3 = "USART baud rate serial communication"

v1 = embed_query(q1)
v2 = embed_query(q2)
v3 = embed_query(q3)

sim_related   = cosine_similarity(v1, v2)
sim_unrelated = cosine_similarity(v1, v3)

print(f"  PLL vs PLL desc  : {sim_related:.4f}  (should be > 0.70)")
print(f"  PLL vs USART     : {sim_unrelated:.4f} (should be < 0.70)")
pass4 = sim_related > 0.70 and sim_unrelated < sim_related
print(f"  PASS" if pass4 else "  FAIL — similarity scores unexpected")

# ── Test 5: MCU specific terms ────────────────────────────
print("\nTest 5 — MCU terminology similarity")
pairs = [
    ("USART baud rate",          "serial communication speed",   0.30),
    ("GPIO alternate function",  "pin multiplexing AF number",   0.15),
    ("DMA transfer error",       "direct memory access fault",   0.30),
    ("errata workaround",        "silicon bug fix",              0.25),
]
all_pass = True
for text_a, text_b, threshold in pairs:
    va = embed_query(text_a)
    vb = embed_query(text_b)
    sim = cosine_similarity(va, vb)
    ok  = sim > threshold
    if not ok:
        all_pass = False
    print(f"  '{text_a[:20]}' ↔ '{text_b[:20]}'")
    print(f"    Similarity: {sim:.4f} {'✅' if ok else '❌'}")

print(f"  PASS" if all_pass else "  FAIL — check similarity scores")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 50)
all_ok = (
    dim == 384 and
    len(vec) == 384 and
    len(vectors) == 5 and
    pass4 and
    all_pass
)
print("RESULT: embedder.py OK ✅" if all_ok
      else "RESULT: embedder.py FAILED ❌")
print("=" * 50)