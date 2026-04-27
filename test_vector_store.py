# test_vector_store.py — Phase 2 Test 2
# Run: python test_vector_store.py

import os
from ingestion.pdf_parser import parse_pdf, PageContent
from ingestion.chunker import chunk_pages
from retrieval.vector_store import (
    get_collection, index_chunks, search,
    search_errata_only, list_indexed_sources,
    get_chunk_count, clear_collection
)

print("=" * 50)
print("VECTOR_STORE.PY TEST")
print("=" * 50)

# ── Test 1: Collection creates ────────────────────────────
print("\nTest 1 — Collection creation")
col = get_collection("test_collection")
print(f"  Collection created : OK")
print(f"  Initial count      : {col.count()}")
print(f"  PASS")

# ── Test 2: Index small test chunks ───────────────────────
print("\nTest 2 — Index test chunks")
test_pages = [
    PageContent(1,
        "PLL configuration: Set PLLN=168, PLLM=8, PLLP=2 "
        "for 168 MHz system clock. RCC_PLLCFGR register. "
        "Section 6.3.2 page 148. HSE 8 MHz crystal required.",
        "test_rm.pdf", "Reference Manual"),
    PageContent(2,
        "USART baud rate: BRR register value for 115200 baud "
        "at 84 MHz APB2 clock. USART1->BRR = 0x0683. "
        "Section 27.6.3 page 871. 8N1 format.",
        "test_rm.pdf", "Reference Manual"),
    PageContent(3,
        "Errata 2.2.13: Delay after RCC peripheral clock enabling. "
        "A delay may be observed between RCC clock enable and "
        "effective peripheral enabling. Workaround: insert dummy "
        "read or use DSB instruction.",
        "test_errata.pdf", "Errata"),
    PageContent(4,
        "SPI BSY flag workaround: BSY bit may stay high when SPI "
        "is disabled in master transmit mode. Disable SPI when "
        "TXE=1 and BSY=0. Section 2.12.1.",
        "test_errata.pdf", "Errata"),
    PageContent(5,
        "GPIO alternate function table: PA9 AF7 = USART1_TX. "
        "PA10 AF7 = USART1_RX. PB6 AF7 = USART1_TX alternate. "
        "Set MODER=10, OTYPER=0, OSPEEDR=11, AFR[1]=7.",
        "test_ds.pdf", "Datasheet"),
]
test_chunks = chunk_pages(test_pages)
total = index_chunks(
    test_chunks,
    collection_name = "test_collection",
    clear_existing  = True
)
print(f"  Chunks indexed : {total}")
print(f"  PASS" if total > 0 else "  FAIL")

# ── Test 3: Basic search ──────────────────────────────────
print("\nTest 3 — Basic search")
results = search("PLL clock 168 MHz configuration",
                 collection_name="test_collection", top_k=3)
print(f"  Query           : 'PLL clock 168 MHz configuration'")
print(f"  Results count   : {len(results)}")
if results:
    print(f"  Top result score: {results[0]['score']}")
    print(f"  Top result page : {results[0]['page']}")
    print(f"  Contains PLL    : {'PLL' in results[0]['text']}")
pass3 = len(results) > 0 and results[0]['score'] > 0.5
print(f"  PASS" if pass3 else "  FAIL — no results or low score")

# ── Test 4: Errata filter ─────────────────────────────────
print("\nTest 4 — Errata-only search filter")
errata_results = search(
    "workaround peripheral clock delay",
    collection_name = "test_collection",
    filter_doc_type = "Errata"
)
print(f"  Results          : {len(errata_results)}")
all_errata = all(r["doc_type"] == "Errata" for r in errata_results)
print(f"  All doc_type=Errata: {all_errata}")
print(f"  PASS" if all_errata and len(errata_results) > 0
      else "  FAIL")

# ── Test 5: Semantic relevance ────────────────────────────
print("\nTest 5 — Semantic relevance ordering")
results = search("serial communication baud rate",
                 collection_name="test_collection", top_k=3)
top_text = results[0]["text"] if results else ""
usart_first = "USART" in top_text or "baud" in top_text.lower()
print(f"  Query: 'serial communication baud rate'")
print(f"  Top result contains USART/baud : {usart_first}")
print(f"  Top result score               : "
      f"{results[0]['score'] if results else 'N/A'}")
print(f"  PASS" if usart_first else "  FAIL — wrong result ranked first")

# ── Test 6: List sources ──────────────────────────────────
print("\nTest 6 — List indexed sources")
sources = list_indexed_sources("test_collection")
print(f"  Sources found : {sources}")
pass6 = len(sources) == 3   # test_rm, test_errata, test_ds
print(f"  PASS" if pass6 else f"  FAIL — expected 3, got {len(sources)}")

# ── Test 7: Persistence ───────────────────────────────────
print("\nTest 7 — Persistence check")
count_before = get_chunk_count("test_collection")
# Re-open collection (simulates program restart)
col2 = get_collection("test_collection")
count_after = col2.count()
print(f"  Count before : {count_before}")
print(f"  Count after  : {count_after}")
print(f"  PASS" if count_before == count_after
      else "  FAIL — data not persisted")

# ── Test 8: Real PDF (if available) ───────────────────────
print("\nTest 8 — Real errata PDF index and search")
pdfs = [f for f in os.listdir('./docs') if f.endswith('.pdf')]
if pdfs:
    print(f"  Found: {pdfs[0]}")
    pages  = parse_pdf(f"./docs/{pdfs[0]}", "Errata")
    chunks = chunk_pages(pages)
    total  = index_chunks(chunks, clear_existing=True)

    # Search for something we know is in the errata
    hits = search("RCC peripheral clock enable delay workaround")
    print(f"  Indexed chunks  : {total}")
    print(f"  Search results  : {len(hits)}")
    if hits:
        print(f"  Top score       : {hits[0]['score']}")
        print(f"  Top page        : {hits[0]['page']}")
        print(f"  Top preview     : {hits[0]['text'][:80]}...")
    print(f"  PASS" if len(hits) > 0 and hits[0]['score'] > 0.4
          else "  FAIL")
else:
    print("  No PDF in docs/ — skipping real PDF test")

# ── Cleanup test collection ───────────────────────────────
clear_collection("test_collection")
print("\n  Test collection cleared.")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 50)
all_ok = (
    total > 0 and
    pass3 and
    all_errata and
    usart_first and
    pass6 and
    count_before == count_after
)
print("RESULT: vector_store.py OK ✅" if all_ok
      else "RESULT: vector_store.py FAILED ❌")
print("=" * 50)