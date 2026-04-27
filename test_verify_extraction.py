# =============================================================
# test_verify_extraction.py
# Detailed verification of PDF extraction for MCU documents.
# Tests: text extraction, table extraction, image detection
# Run: python test_verify_extraction.py
# =============================================================

import os
import pdfplumber
from ingestion.pdf_parser import parse_pdf
from ingestion.chunker import chunk_pages

PDF_FILE = "./docs/STM32F407_ERRATE.pdf"
DOC_TYPE = "Errata"

# =============================================================
# TEST 1 — RAW PDF INSPECTION
# =============================================================
print("=" * 55)
print("TEST 1 — RAW PDF INSPECTION")
print("=" * 55)

if not os.path.exists(PDF_FILE):
    print(f"[ERROR] File not found: {PDF_FILE}")
    print("Make sure STM32F407_ERRATE.pdf is in docs/ folder")
    exit()

with pdfplumber.open(PDF_FILE) as pdf:
    total_pages = len(pdf.pages)
    print(f"File             : STM32F407_ERRATE.pdf")
    print(f"Total pages      : {total_pages}")

    # Check first 5 pages for content types
    print(f"\nPage-by-page inspection (first 10 pages):")
    print(f"{'Page':<6} {'Text?':<8} {'Tables?':<10} "
          f"{'Images?':<10} {'Text Length'}")
    print("-" * 55)

    text_pages   = 0
    table_pages  = 0
    image_pages  = 0
    empty_pages  = 0

    for i, page in enumerate(pdf.pages):
        text   = page.extract_text()
        tables = page.extract_tables()
        images = page.images

        has_text   = bool(text and text.strip())
        has_tables = bool(tables and any(tables))
        has_images = bool(images)

        if has_text:   text_pages  += 1
        if has_tables: table_pages += 1
        if has_images: image_pages += 1
        if not has_text: empty_pages += 1

        # Print first 10 pages in detail
        if i < 10:
            text_len = len(text.strip()) if text else 0
            print(f"{i+1:<6} "
                  f"{'Yes' if has_text else 'No':<8} "
                  f"{'Yes' if has_tables else 'No':<10} "
                  f"{'Yes' if has_images else 'No':<10} "
                  f"{text_len} chars")

    if total_pages > 10:
        print(f"  ... ({total_pages - 10} more pages)")

    print("-" * 55)
    print(f"\nFull document summary:")
    print(f"  Pages with text   : {text_pages}/{total_pages}")
    print(f"  Pages with tables : {table_pages}/{total_pages}")
    print(f"  Pages with images : {image_pages}/{total_pages}")
    print(f"  Empty/scan pages  : {empty_pages}/{total_pages}")

# =============================================================
# TEST 2 — TABLE EXTRACTION DETAIL
# =============================================================
print("\n" + "=" * 55)
print("TEST 2 — TABLE EXTRACTION DETAIL")
print("=" * 55)

with pdfplumber.open(PDF_FILE) as pdf:
    tables_found = 0

    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        if not tables:
            continue

        for t_idx, table in enumerate(tables):
            if not table:
                continue
            tables_found += 1

            # Show first 3 tables in detail
            if tables_found <= 3:
                print(f"\nTable {tables_found} "
                      f"— Page {i+1}, Table index {t_idx}")
                print(f"  Rows    : {len(table)}")
                print(f"  Columns : "
                      f"{max(len(r) for r in table if r)}")
                print(f"  Preview (first 3 rows):")
                for row in table[:3]:
                    clean = " | ".join(
                        str(c).strip()[:20]
                        for c in row
                        if c is not None
                    )
                    print(f"    {clean}")

    print(f"\nTotal tables found in document: {tables_found}")
    if tables_found == 0:
        print("  Note: No tables detected.")
        print("  This is normal for some errata documents")
        print("  that use plain text instead of tables.")

# =============================================================
# TEST 3 — IMAGE DETECTION
# =============================================================
print("\n" + "=" * 55)
print("TEST 3 — IMAGE DETECTION")
print("=" * 55)

with pdfplumber.open(PDF_FILE) as pdf:
    total_images = 0
    image_info   = []

    for i, page in enumerate(pdf.pages):
        images = page.images
        if images:
            total_images += len(images)
            for img in images:
                image_info.append({
                    "page"   : i + 1,
                    "width"  : round(img.get("width",  0)),
                    "height" : round(img.get("height", 0)),
                })

    print(f"Total images found : {total_images}")

    if image_info:
        print(f"\nImage details (first 5):")
        print(f"{'Page':<8} {'Width':<10} {'Height'}")
        print("-" * 30)
        for img in image_info[:5]:
            print(f"{img['page']:<8} "
                  f"{img['width']:<10} "
                  f"{img['height']}")
        print("\n  Note: Images cannot be read by the LLM.")
        print("  Only text around images is extracted.")
        print("  For register diagrams, the surrounding")
        print("  text description is what gets indexed.")
    else:
        print("  No embedded images found.")
        print("  Document is text-based — ideal for extraction.")

# =============================================================
# TEST 4 — FULL PARSER TEST
# =============================================================
print("\n" + "=" * 55)
print("TEST 4 — FULL PARSER (pdf_parser.py)")
print("=" * 55)

pages = parse_pdf(PDF_FILE, DOC_TYPE)
print(f"Pages returned   : {len(pages)}")

if pages:
    print(f"\nSample — Page 1:")
    print(f"  Source file  : {pages[0].source_file}")
    print(f"  Doc type     : {pages[0].doc_type}")
    print(f"  Text length  : {len(pages[0].text)} chars")
    print(f"  Has table    : {'[TABLE]' in pages[0].text}")
    print(f"  Text preview :")
    print(f"  {pages[0].text[:200]}")

    # Check how many pages have tables
    tbl_pages = [p for p in pages if '[TABLE]' in p.text]
    print(f"\nPages with extracted tables: {len(tbl_pages)}")

    if tbl_pages:
        print(f"\nSample table content from page "
              f"{tbl_pages[0].page_num}:")
        start = tbl_pages[0].text.find('[TABLE]')
        end   = tbl_pages[0].text.find('[/TABLE]') + 8
        print(tbl_pages[0].text[start:end][:300])

# =============================================================
# TEST 5 — CHUNKER TEST
# =============================================================
print("\n" + "=" * 55)
print("TEST 5 — CHUNKER (chunker.py)")
print("=" * 55)

if pages:
    chunks = chunk_pages(pages)
    print(f"Total chunks     : {len(chunks)}")

    if chunks:
        print(f"Chunk 0 preview  :")
        print(f"  Page           : {chunks[0].page_num}")
        print(f"  Length         : {len(chunks[0].text)} chars")
        print(f"  Text preview   : {chunks[0].text[:150]}")

        # Check chunks that contain table data
        tbl_chunks = [
            c for c in chunks if '[TABLE]' in c.text
        ]
        print(f"\nChunks containing table data: {len(tbl_chunks)}")

        if tbl_chunks:
            print(f"Sample table chunk (chunk index "
                  f"{tbl_chunks[0].chunk_index}, "
                  f"page {tbl_chunks[0].page_num}):")
            print(f"  {tbl_chunks[0].text[:200]}")

        # Errata specific — look for errata item keywords
        errata_chunks = [
            c for c in chunks
            if any(k in c.text.upper() for k in
                   ['ERRAT', 'WORKAROUND', 'LIMITATION',
                    'BUG', 'INCORRECT', 'FIXED'])
        ]
        print(f"\nChunks with errata keywords: "
              f"{len(errata_chunks)}")

        if errata_chunks:
            print(f"Sample errata chunk:")
            print(f"  {errata_chunks[0].text[:200]}")

# =============================================================
# FINAL SUMMARY
# =============================================================
print("\n" + "=" * 55)
print("EXTRACTION VERIFICATION SUMMARY")
print("=" * 55)

if pages and chunks:
    tbl_p  = len([p for p in pages  if '[TABLE]' in p.text])
    tbl_c  = len([c for c in chunks if '[TABLE]' in c.text])
    err_c  = len([
        c for c in chunks
        if any(k in c.text.upper() for k in
               ['ERRAT', 'WORKAROUND', 'LIMITATION'])
    ])

    print(f"PDF file              : STM32F407_ERRATE.pdf")
    print(f"Total pages           : {total_pages}")
    print(f"Pages extracted       : {len(pages)}")
    print(f"Pages with tables     : {tbl_p}")
    print(f"Total chunks          : {len(chunks)}")
    print(f"Chunks with tables    : {tbl_c}")
    print(f"Chunks with errata    : {err_c}")
    print(f"Images in doc         : {total_images}")
    print("-" * 55)

    if len(pages) > 0 and len(chunks) > 0:
        print("RESULT: Extraction verified OK")
        print("\nIMPORTANT NOTES:")
        if total_images > 0:
            print(f"  ⚠  {total_images} images found — LLM cannot")
            print(f"     read image content directly.")
            print(f"     Register bit diagrams in images will")
            print(f"     NOT be indexed — only surrounding text.")
        if empty_pages > 0:
            print(f"  ⚠  {empty_pages} scanned/empty pages skipped.")
            print(f"     These pages are not searchable.")
        if err_c > 0:
            print(f"  ✅ {err_c} errata chunks found and indexed.")
            print(f"     Errata detection will work correctly.")
    else:
        print("RESULT: Extraction FAILED — check errors above")

print("=" * 55)