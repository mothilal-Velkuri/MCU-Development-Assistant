# test_chunker.py — Phase 1 Test 3 (Updated with merge fix tests)
# Run: python test_chunker.py

from ingestion.pdf_parser import PageContent
from ingestion.chunker import chunk_pages, forward_fill_table
from Config import CHUNK_SIZE, CHUNK_OVERLAP

print("=" * 50)
print("CHUNKER.PY TEST — Including Merge Fix")
print("=" * 50)

# ── Test 1: Basic chunking ─────────────────────────────────
print("\nTest 1 — Basic chunking")
fake_page = PageContent(
    page_num    = 1,
    text        = "A" * 1200,
    source_file = "test.pdf",
    doc_type    = "Datasheet"
)
chunks = chunk_pages([fake_page])
print(f"  Input length    : 1200 chars")
print(f"  Chunks produced : {len(chunks)}")
print(f"  Source file     : {chunks[0].source_file}")
print(f"  PASS" if len(chunks) >= 2 else "  FAIL")

# ── Test 2: Overlap verification ───────────────────────────
print("\nTest 2 — Overlap verification")
overlap_ok = chunks[0].text[-(CHUNK_OVERLAP):] in chunks[1].text[:120]
print(f"  Overlap working : {overlap_ok}")
print(f"  PASS" if overlap_ok else "  FAIL")

# ── Test 3: Forward fill — merged cells ────────────────────
print("\nTest 3 — Forward fill (merged cell fix)")
table_with_merges = """Some text before.

[TABLE]
Register name | Bit number | Bit name
ETH_DMAOMR | 26 | DTCEFD
 |  25 | RSF
 |  20 | FTF
 |  7 | FEF
ETH_DMABMR | 7 | EDFE
 |  5 | SOME_BIT
[/TABLE]

Text after table."""

fixed = forward_fill_table(table_with_merges)
print(f"  Original has empty cells : {'| |' in table_with_merges}")
print(f"  After fix — ETH_DMAOMR propagated to sub-rows:")
for line in fixed.split('\n'):
    if 'RSF' in line or 'FTF' in line or 'FEF' in line:
        print(f"    {line.strip()}")
propagated = 'ETH_DMAOMR' in fixed.split('\n')[5]
print(f"  Propagation worked : {propagated}")
print(f"  PASS" if propagated else "  FAIL — check forward_fill_table()")

# ── Test 4: Function label propagation ─────────────────────
print("\nTest 4 — Function label propagation (Table 3 style)")
table_func = """[TABLE]
Function | Section | Limitation
Core | 2.1.1 | Interrupted loads
 | 2.1.2 | VDIV instructions
 | 2.1.3 | Store immediate
System | 2.2.1 | ART Accelerator
 | 2.2.2 | MCU device ID
[/TABLE]"""

fixed_func = forward_fill_table(table_func)
lines = fixed_func.split('\n')
core_propagated = all(
    'Core' in l for l in lines
    if '2.1.2' in l or '2.1.3' in l
)
system_propagated = any('System' in l for l in lines if '2.2.2' in l)
print(f"  Core propagated to 2.1.2 and 2.1.3 : {core_propagated}")
print(f"  System propagated to 2.2.2          : {system_propagated}")
print(f"  PASS" if core_propagated and system_propagated
      else "  FAIL")

# ── Test 5: Real errata PDF ────────────────────────────────
import os
print("\nTest 5 — Real errata PDF chunking")
pdfs = [f for f in os.listdir('./docs') if f.endswith('.pdf')]
if pdfs:
    from ingestion.pdf_parser import parse_pdf
    pages = parse_pdf(f'./docs/{pdfs[0]}', 'Errata')
    chunks_real = chunk_pages(pages)

    # Check ETH_DMAOMR propagation in real doc
    eth_chunks = [
        c for c in chunks_real
        if 'ETH_DMAOMR' in c.text
    ]
    reg_chunks = [
        c for c in chunks_real
        if 'RSF' in c.text and 'ETH_DMAOMR' in c.text
    ]
    errata_kw = ['WORKAROUND','LIMITATION','ERRAT']
    errata_chunks = [
        c for c in chunks_real
        if any(k in c.text.upper() for k in errata_kw)
    ]

    print(f"  Total chunks          : {len(chunks_real)}")
    print(f"  ETH_DMAOMR chunks     : {len(eth_chunks)}")
    print(f"  RSF+ETH_DMAOMR chunks : {len(reg_chunks)}")
    print(f"  Errata keyword chunks : {len(errata_chunks)}")
    print(f"  PASS" if len(chunks_real) > 0 else "  FAIL")
else:
    print("  No PDF in docs/ — skipping real doc test")

# ── Test 6: Section-aware splitting ───────────────────────
print("\nTest 6 — Section-aware splitting")
section_text = """2.1.1 Interrupted loads to SP
This limitation is registered under Arm ID 752770.
Description: If an interrupt occurs during SP load erroneous.
Workaround: Replace direct load with intermediate register.

2.1.2 VDIV or VSQRT instructions
This limitation is registered under Arm ID 776924.
Description: VDIV takes 14 cycles to execute.
Workaround: Disable lazy context save by clearing LSPEN.""" * 3

sec_page = PageContent(
    page_num=5, text=section_text,
    source_file="test.pdf", doc_type="Errata"
)
sec_chunks = chunk_pages([sec_page])
print(f"  Section text length : {len(section_text)} chars")
print(f"  Chunks produced     : {len(sec_chunks)}")
has_2_1_1 = any('2.1.1' in c.text for c in sec_chunks)
has_2_1_2 = any('2.1.2' in c.text for c in sec_chunks)
print(f"  2.1.1 in chunks     : {has_2_1_1}")
print(f"  2.1.2 in chunks     : {has_2_1_2}")
print(f"  PASS" if has_2_1_1 and has_2_1_2 else "  FAIL")

# ── Summary ────────────────────────────────────────────────
print("\n" + "=" * 50)
all_pass = (
    len(chunks) >= 2 and
    overlap_ok and
    propagated and
    core_propagated and
    system_propagated and
    has_2_1_1 and
    has_2_1_2
)
print("RESULT: chunker.py OK — All tests passed ✅"
      if all_pass else
      "RESULT: chunker.py FAILED — check output above ❌")
print("=" * 50)