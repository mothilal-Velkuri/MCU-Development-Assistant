# =============================================================
# ingestion/pdf_parser.py
# Extracts text and tables from PDF files page by page.
# Designed for technical docs: datasheets, user manuals,
# errata sheets and application notes.
# =============================================================

import pdfplumber
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PageContent:
    """Single page of extracted PDF content with metadata."""
    page_num:    int
    text:        str
    source_file: str
    doc_type:    str


def parse_pdf(pdf_path: str, doc_type: str = "Datasheet") -> list[PageContent]:
    """
    Extract text and tables from every page of a PDF.

    Parameters
    ----------
    pdf_path : full path to PDF file
    doc_type : label for citation e.g. 'Errata', 'Datasheet'

    Returns
    -------
    list of PageContent — one per extractable page
    """
    pages = []
    path  = Path(pdf_path)

    if not path.exists():
        print(f"  [ERROR] File not found: {pdf_path}")
        return pages

    print(f"  Parsing : {path.name}  [{doc_type}]")

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)

        for i, page in enumerate(pdf.pages):
            text = page.extract_text()

            if not text:
                continue      # skip scanned / image-only pages

            # ── Extract tables as pipe-separated text ──────────
            # Register tables in datasheets are critical.
            # Converting them to text allows the embedder to
            # find register names and bit field values.
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue
                rows = []
                for row in table:
                    clean = " | ".join(
                        str(c).strip()
                        for c in row
                        if c is not None and str(c).strip()
                    )
                    if clean:
                        rows.append(clean)
                if rows:
                    text += "\n\n[TABLE]\n" + "\n".join(rows) + "\n[/TABLE]"

            pages.append(PageContent(
                page_num    = i + 1,
                text        = text.strip(),
                source_file = path.name,
                doc_type    = doc_type,
            ))

    print(f"  Done    : {len(pages)}/{total} pages extracted")
    return pages