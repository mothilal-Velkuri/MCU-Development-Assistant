# =============================================================
# ingestion/chunker.py
# Splits extracted page text into overlapping chunks.
#
# Why chunking?
#   A 1000-page datasheet cannot fit in LLM context window.
#   We split it into small pieces. At query time we retrieve
#   only the most relevant pieces.
#
# Why overlap?
#   Ensures content at chunk boundaries is not lost.
#   A register description split across two chunks is still
#   fully retrievable because of the overlap.
#
# Merged Cell Fix (Phase 1 improvement):
#   pdfplumber returns None/empty for merged cells in tables.
#   forward_fill_table() propagates the cell value downward
#   so register names and function labels are not lost in
#   sub-rows. Critical for register tables in datasheets.
# =============================================================

from dataclasses import dataclass
from ingestion.pdf_parser import PageContent
from Config import CHUNK_SIZE, CHUNK_OVERLAP
import re


@dataclass
class Chunk:
    """A single searchable text unit with full source metadata."""
    text:        str
    source_file: str
    doc_type:    str
    page_num:    int
    chunk_index: int


# =============================================================
# MERGED CELL FORWARD FILL
# =============================================================

def forward_fill_table(table_text: str) -> str:
    """
    Fix merged cells in extracted table text.

    pdfplumber puts None/empty for merged cells.
    This function propagates cell values downward
    so sub-rows inherit the merged parent cell value.

    Example input (from pdfplumber):
        ETH_DMAOMR | 26 | DTCEFD
        (EMPTY)    | 25 | RSF
        (EMPTY)    | 20 | FTF

    Example output after fix:
        ETH_DMAOMR | 26 | DTCEFD
        ETH_DMAOMR | 25 | RSF
        ETH_DMAOMR | 20 | FTF
    """
    if '[TABLE]' not in table_text:
        return table_text

    result_parts = []
    # Split text into table and non-table sections
    remaining = table_text
    while '[TABLE]' in remaining:
        pre, rest = remaining.split('[TABLE]', 1)
        result_parts.append(pre)

        if '[/TABLE]' in rest:
            table_content, remaining = rest.split('[/TABLE]', 1)
        else:
            result_parts.append('[TABLE]' + rest)
            remaining = ''
            break

        # Process each row in the table
        rows = table_content.strip().split('\n')
        filled_rows = []
        last_values = {}   # col_index → last non-empty value

        for row in rows:
            if not row.strip():
                filled_rows.append(row)
                continue

            cells = row.split(' | ')
            filled_cells = []

            for col_idx, cell in enumerate(cells):
                stripped = cell.strip()

                # Cell is empty or looks like a merged cell placeholder
                is_empty = (
                    not stripped or
                    stripped == '(EMPTY/MERGED)' or
                    stripped == '(merged/empty)'
                )

                if is_empty and col_idx in last_values:
                    # Forward fill from last known value
                    filled_cells.append(last_values[col_idx])
                else:
                    filled_cells.append(cell)
                    if stripped and not is_empty:
                        last_values[col_idx] = stripped

            filled_rows.append(' | '.join(filled_cells))

        result_parts.append(
            '[TABLE]\n' + '\n'.join(filled_rows) + '\n[/TABLE]'
        )

    result_parts.append(remaining)
    return ''.join(result_parts)


# =============================================================
# SECTION-AWARE SPLITTING
# =============================================================

def detect_section_boundaries(text: str) -> list[int]:
    """
    Find positions of section headers in text.
    Returns list of character positions where sections start.

    Detects patterns like:
      2.1.1   Interrupted loads to SP
      Section 2.2 — System
      2.16.6  Successive write operations
    """
    pattern = re.compile(
        r'(?m)^'                          # start of line
        r'(\d+\.\d+(?:\.\d+)?)'          # section number e.g. 2.1.1
        r'\s+'                            # whitespace
        r'[A-Z]'                          # starts with capital letter
    )
    return [m.start() for m in pattern.finditer(text)]


# =============================================================
# MAIN CHUNKER
# =============================================================

def chunk_pages(pages: list[PageContent]) -> list[Chunk]:
    """
    Split page content into overlapping chunks.
    Applies merged-cell fix before chunking.

    Parameters
    ----------
    pages : list[PageContent] from parse_pdf()

    Returns
    -------
    list[Chunk] — all chunks across all pages in order
    """
    chunks = []

    for page in pages:
        # ── Step 1: Fix merged cells in table sections ─────────
        text = forward_fill_table(page.text)

        # ── Step 2: Try section-aware splitting first ──────────
        section_positions = detect_section_boundaries(text)

        if len(section_positions) >= 2:
            # Document has detectable sections — split at boundaries
            chunks_for_page = _split_at_sections(
                text, section_positions, page
            )
        else:
            # Fall back to fixed-size overlap chunking
            chunks_for_page = _split_fixed_size(text, page)

        chunks.extend(chunks_for_page)

    print(f"  Chunking done : {len(chunks)} chunks "
          f"from {len(pages)} pages")
    return chunks


def _split_at_sections(
    text: str,
    positions: list[int],
    page: PageContent
) -> list[Chunk]:
    """
    Split text at section boundaries.
    Each section becomes one or more chunks if it is too long.
    """
    chunks = []
    idx = 0

    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        section_text = text[start:end].strip()

        if not section_text:
            continue

        # If section fits in one chunk — keep it whole
        if len(section_text) <= CHUNK_SIZE * 2:
            chunks.append(Chunk(
                text        = section_text,
                source_file = page.source_file,
                doc_type    = page.doc_type,
                page_num    = page.page_num,
                chunk_index = idx,
            ))
            idx += 1
        else:
            # Section is large — split with overlap
            sub_chunks = _split_fixed_size(section_text, page, start_idx=idx)
            chunks.extend(sub_chunks)
            idx += len(sub_chunks)

    return chunks


def _split_fixed_size(
    text: str,
    page: PageContent,
    start_idx: int = 0
) -> list[Chunk]:
    """
    Standard fixed-size overlap chunking.
    Used as fallback and for large sections.
    """
    chunks = []
    start  = 0
    idx    = start_idx

    while start < len(text):
        end        = start + CHUNK_SIZE
        chunk_text = text[start:end]

        # Avoid tiny trailing fragments
        if len(chunk_text) < 80:
            if chunks:
                chunks[-1].text += " " + chunk_text.strip()
            break

        chunks.append(Chunk(
            text        = chunk_text.strip(),
            source_file = page.source_file,
            doc_type    = page.doc_type,
            page_num    = page.page_num,
            chunk_index = idx,
        ))

        start += CHUNK_SIZE - CHUNK_OVERLAP
        idx   += 1

    return chunks