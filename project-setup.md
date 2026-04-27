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
**Step 3:**
    verify the config.py file with below code.
        python -c "
        import Config
        
        print('LLM Backend    :', Config.LLM_BACKEND)
        print('Ollama Model   :', Config.OLLAMA_MODEL)
        print('Embedding Model:', Config.EMBEDDING_MODEL)
        print('Chunk Size     :', Config.CHUNK_SIZE)
        print('Top K Results  :', Config.TOP_K_RESULTS)
        print('config.py OK')
    output should be something like below.
        (mcu_assistant) C:\mcu_assistant>python test_config.py
        LLM Backend    : ollama
        Ollama Model   : mistral
        Embedding Model: all-MiniLM-L6-v2
        Chunk Size     : 500
        Top K Results  : 6
        config.py OK

**Step 4:**    **Create pdf_parser.py**
    create pdf_parser.py in ingestion folder.
        # =============================================================
        # ingestion/pdf_parser.py
        # Extracts text and tables from PDF files page by page.
        # Uses pdfplumber which handles embedded tables better than
        # basic PDF parsers — critical for register tables in datasheets.
        # =============================================================
        
        import pdfplumber
        from pathlib import Path
        from dataclasses import dataclass
        
        
        @dataclass
        class PageContent:
            """
            Holds extracted content from a single PDF page.
            source_file : filename only (e.g. 'stm32f4_rm.pdf')
            doc_type    : label assigned by user ('Datasheet', 'Errata' etc.)
            page_num    : 1-based page number
            text        : full extracted text including table contents
            """
            page_num:    int
            text:        str
            source_file: str
            doc_type:    str
        
        
        def parse_pdf(pdf_path: str, doc_type: str = "Datasheet") -> list[PageContent]:
            """
            Extract text from every page of a PDF.
        
            Parameters
            ----------
            pdf_path : str
                Full path to the PDF file.
            doc_type : str
                Document type label — used later when citing sources.
        
            Returns
            -------
            list[PageContent]
                One PageContent object per page that has extractable text.
                Image-only (scanned) pages are skipped gracefully.
            """
            pages  = []
            path   = Path(pdf_path)
        
            if not path.exists():
                print(f"  [ERROR] File not found: {pdf_path}")
                return pages
        
            print(f"  Parsing: {path.name} ({doc_type})")
        
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
        
                for i, page in enumerate(pdf.pages):
        
                    # ── Extract plain text ─────────────────────────────
                    text = page.extract_text()
        
                    if not text:
                        # Scanned / image-only page — skip silently
                        continue
        
                    # ── Extract tables and append as text ─────────────
                    # Register tables in datasheets carry critical info.
                    # We convert them to pipe-separated text so the
                    # embedder can find register names and bit fields.
                    tables = page.extract_tables()
                    for table in tables:
                        if not table:
                            continue
                        table_rows = []
                        for row in table:
                            # Filter None cells, join with pipe separator
                            clean_row = " | ".join(
                                str(cell).strip()
                                for cell in row
                                if cell is not None and str(cell).strip()
                            )
                            if clean_row:
                                table_rows.append(clean_row)
        
                        if table_rows:
                            table_text = "\n".join(table_rows)
                            text += f"\n\n[TABLE]\n{table_text}\n[/TABLE]"
        
                    # ── Store the page ─────────────────────────────────
                    pages.append(PageContent(
                        page_num    = i + 1,
                        text        = text.strip(),
                        source_file = path.name,
                        doc_type    = doc_type,
                    ))
        
            print(f"  Done: {len(pages)} / {total_pages} pages extracted")
            return pages
        **Step 5:**  **Test pdf_parser.py**
        paste below script and run (add any pdf file in the docs folder)
        from ingestion.pdf_parser import parse_pdf, PageContent
        import os
        
        # Check if any PDF exists in docs/
        pdfs = [f for f in os.listdir('./docs') if f.endswith('.pdf')]
        
        if not pdfs:
            print('No PDF in docs/ yet — testing import only')
            print('pdf_parser.py import OK')
        else:
            pages = parse_pdf(f'./docs/{pdfs[0]}', 'Datasheet')
            print(f'Pages extracted : {len(pages)}')
            print(f'First page num  : {pages[0].page_num}')
            print(f'Source file     : {pages[0].source_file}')
            print(f'Doc type        : {pages[0].doc_type}')
            print(f'Text preview    : {pages[0].text[:80]}...')
            print('pdf_parser.py OK')
        output should be similar to below.
         Parsing: open_platform_license_agreement.pdf (Datasheet)
          Done: 3 / 3 pages extracted
        Pages extracted : 3
        First page num  : 1
        Source file     : open_platform_license_agreement.pdf
        Doc type        : Datasheet
        Text preview    : OPEN PLATFORM LICENSE AGREEMENT
        This Open Platform License Agreement (“Agreement...
        pdf_parser.py OK
        
        **step 6:**    **chunker.py**
        copy below code and save as chunker.py.
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
