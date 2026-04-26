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
