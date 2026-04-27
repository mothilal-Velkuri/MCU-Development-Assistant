# =============================================================
# test_visual_inspection.py
# Creates a visual HTML report of all extracted content.
# Opens in your browser for easy inspection.
# Run: python test_visual_inspection.py
# =============================================================

import os
import pdfplumber
from ingestion.pdf_parser import parse_pdf
from ingestion.chunker import chunk_pages

PDF_FILE  = "./docs/STM32F407_ERRATE.pdf"
DOC_TYPE  = "Errata"
OUT_FILE  = "./extraction_report.html"

print("Running extraction...")
pages  = parse_pdf(PDF_FILE, DOC_TYPE)
chunks = chunk_pages(pages)
print(f"Pages  : {len(pages)}")
print(f"Chunks : {len(chunks)}")
print("Building visual report...")

# =============================================================
# COLLECT RAW TABLE DATA FROM PDFPLUMBER
# =============================================================
raw_tables = []   # list of {page, table_index, rows}

with pdfplumber.open(PDF_FILE) as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for t_idx, table in enumerate(tables):
            if table:
                raw_tables.append({
                    "page"        : i + 1,
                    "table_index" : t_idx,
                    "rows"        : table,
                    "row_count"   : len(table),
                    "col_count"   : max(
                        len(r) for r in table if r
                    ),
                })

# =============================================================
# HTML BUILDER
# =============================================================

def esc(text):
    """Escape HTML special characters."""
    if text is None:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

html_parts = []

# ── Header ────────────────────────────────────────────────────
html_parts.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Extraction Visual Report — STM32F407_ERRATE.pdf</title>
<style>
  body {{
    font-family: Arial, sans-serif;
    background: #1e1e1e;
    color: #d4d4d4;
    margin: 0;
    padding: 20px;
  }}
  h1 {{
    color: #4ec9b0;
    border-bottom: 2px solid #4ec9b0;
    padding-bottom: 8px;
  }}
  h2 {{
    color: #dcdcaa;
    margin-top: 40px;
    border-left: 4px solid #dcdcaa;
    padding-left: 10px;
  }}
  h3 {{
    color: #9cdcfe;
    margin-top: 24px;
  }}
  .summary-box {{
    background: #252526;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    padding: 16px 24px;
    margin: 16px 0;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }}
  .stat {{
    text-align: center;
  }}
  .stat .num {{
    font-size: 2em;
    font-weight: bold;
    color: #4ec9b0;
  }}
  .stat .lbl {{
    font-size: 0.85em;
    color: #858585;
    margin-top: 4px;
  }}
  .page-block {{
    background: #252526;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    margin: 12px 0;
    overflow: hidden;
  }}
  .page-header {{
    background: #2d2d30;
    padding: 8px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #3e3e42;
  }}
  .page-num {{
    font-weight: bold;
    color: #4ec9b0;
    font-size: 1em;
  }}
  .badges {{
    display: flex;
    gap: 6px;
  }}
  .badge {{
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: bold;
  }}
  .badge-text   {{ background:#1a4a3a; color:#4ec9b0; }}
  .badge-table  {{ background:#4a3a1a; color:#dcdcaa; }}
  .badge-notext {{ background:#3a1a1a; color:#f48771; }}
  .page-content {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
  }}
  .text-panel {{
    padding: 12px 16px;
    border-right: 1px solid #3e3e42;
  }}
  .table-panel {{
    padding: 12px 16px;
  }}
  .panel-label {{
    font-size: 11px;
    color: #858585;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 8px;
  }}
  .raw-text {{
    font-family: "Courier New", monospace;
    font-size: 11px;
    background: #1a1a1a;
    padding: 10px;
    border-radius: 4px;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
    color: #ce9178;
    border: 1px solid #3e3e42;
  }}
  table.extracted {{
    border-collapse: collapse;
    width: 100%;
    font-size: 11px;
    margin-bottom: 12px;
  }}
  table.extracted th {{
    background: #3a3a3a;
    color: #dcdcaa;
    padding: 5px 8px;
    border: 1px solid #555;
    text-align: left;
  }}
  table.extracted td {{
    padding: 4px 8px;
    border: 1px solid #3e3e42;
    color: #d4d4d4;
    vertical-align: top;
    max-width: 200px;
    word-break: break-word;
  }}
  table.extracted tr:nth-child(even) td {{
    background: #2a2a2a;
  }}
  .merged-cell {{
    background: #2d2d50 !important;
    color: #9cdcfe;
    font-style: italic;
  }}
  .empty-cell {{
    color: #555;
    font-style: italic;
  }}
  .no-table {{
    color: #555;
    font-style: italic;
    font-size: 12px;
  }}
  .chunk-block {{
    background: #252526;
    border: 1px solid #3e3e42;
    border-radius: 6px;
    margin: 8px 0;
    overflow: hidden;
  }}
  .chunk-header {{
    background: #2d2d30;
    padding: 6px 14px;
    display: flex;
    justify-content: space-between;
    border-bottom: 1px solid #3e3e42;
    font-size: 12px;
  }}
  .chunk-text {{
    font-family: "Courier New", monospace;
    font-size: 11px;
    padding: 10px 14px;
    white-space: pre-wrap;
    word-break: break-word;
    color: #ce9178;
    max-height: 150px;
    overflow-y: auto;
  }}
  .chunk-has-table {{ border-left: 3px solid #dcdcaa; }}
  .chunk-has-errata {{ border-left: 3px solid #f48771; }}
  .chunk-normal {{ border-left: 3px solid #4ec9b0; }}
  .nav {{
    position: sticky;
    top: 0;
    background: #1e1e1e;
    padding: 8px 0;
    border-bottom: 1px solid #3e3e42;
    margin-bottom: 20px;
    z-index: 100;
  }}
  .nav a {{
    color: #4ec9b0;
    text-decoration: none;
    margin-right: 20px;
    font-size: 13px;
  }}
  .nav a:hover {{ text-decoration: underline; }}
  .warning {{
    background: #3a2a1a;
    border: 1px solid #dcdcaa;
    border-radius: 4px;
    padding: 10px 16px;
    margin: 8px 0;
    font-size: 12px;
    color: #dcdcaa;
  }}
  .ok {{
    background: #1a3a2a;
    border: 1px solid #4ec9b0;
    border-radius: 4px;
    padding: 10px 16px;
    margin: 8px 0;
    font-size: 12px;
    color: #4ec9b0;
  }}
  .section-stats {{
    font-size: 12px;
    color: #858585;
    margin-bottom: 12px;
  }}
</style>
</head>
<body>
""")

# ── Navigation ─────────────────────────────────────────────────
html_parts.append("""
<div class="nav">
  <a href="#summary">Summary</a>
  <a href="#pages">Page Extraction</a>
  <a href="#tables">Raw Tables</a>
  <a href="#chunks">Chunks</a>
  <a href="#errata">Errata Chunks</a>
</div>
""")

# ── Title ──────────────────────────────────────────────────────
html_parts.append(f"""
<h1>📄 Extraction Visual Report</h1>
<p style="color:#858585;">
  File: <strong style="color:#9cdcfe;">STM32F407_ERRATE.pdf</strong>
  &nbsp;|&nbsp; Type: <strong style="color:#9cdcfe;">Errata</strong>
  &nbsp;|&nbsp; Generated by test_visual_inspection.py
</p>
""")

# =============================================================
# SECTION 1 — SUMMARY
# =============================================================
pages_with_tables = len([p for p in pages if '[TABLE]' in p.text])
chunks_with_tables = len([c for c in chunks if '[TABLE]' in c.text])
errata_keywords = ['ERRAT','WORKAROUND','LIMITATION','BUG','INCORRECT']
chunks_with_errata = len([
    c for c in chunks
    if any(k in c.text.upper() for k in errata_keywords)
])

html_parts.append(f"""
<h2 id="summary">📊 Summary</h2>
<div class="summary-box">
  <div class="stat">
    <div class="num">{len(pages)}</div>
    <div class="lbl">Pages Extracted</div>
  </div>
  <div class="stat">
    <div class="num">{len(raw_tables)}</div>
    <div class="lbl">Raw Tables Found</div>
  </div>
  <div class="stat">
    <div class="num">{len(chunks)}</div>
    <div class="lbl">Total Chunks</div>
  </div>
  <div class="stat">
    <div class="num">{chunks_with_errata}</div>
    <div class="lbl">Errata Chunks</div>
  </div>
</div>
""")

# =============================================================
# SECTION 2 — PAGE BY PAGE
# =============================================================
html_parts.append(f"""
<h2 id="pages">📃 Page-by-Page Extraction</h2>
<div class="section-stats">
  Showing all {len(pages)} pages — 
  left panel: extracted text | right panel: extracted tables
</div>
""")

for page in pages:
    has_table = '[TABLE]' in page.text

    # Split text and table parts
    text_only = page.text
    table_parts = []
    if has_table:
        parts = page.text.split('[TABLE]')
        text_only = parts[0]
        for part in parts[1:]:
            if '[/TABLE]' in part:
                tbl_content, rest = part.split('[/TABLE]', 1)
                table_parts.append(tbl_content.strip())
                text_only += rest

    badge_html = '<span class="badge badge-text">TEXT</span>'
    if has_table:
        badge_html += '<span class="badge badge-table">TABLE</span>'

    html_parts.append(f"""
<div class="page-block">
  <div class="page-header">
    <span class="page-num">Page {page.page_num}</span>
    <div class="badges">{badge_html}</div>
    <span style="font-size:11px;color:#858585;">
      {len(page.text)} chars total
    </span>
  </div>
  <div class="page-content">
    <div class="text-panel">
      <div class="panel-label">Extracted Text</div>
      <div class="raw-text">{esc(text_only[:600])}</div>
    </div>
    <div class="table-panel">
      <div class="panel-label">
        Extracted Tables ({len(table_parts)} found)
      </div>
""")

    if table_parts:
        for t_idx, tbl in enumerate(table_parts):
            rows = [r.strip() for r in tbl.strip().split('\n') if r.strip()]
            html_parts.append(f"""
      <table class="extracted">
        <caption style="color:#858585;font-size:11px;
                        text-align:left;margin-bottom:4px;">
          Table {t_idx + 1}
        </caption>
""")
            for r_idx, row in enumerate(rows):
                cells = row.split(' | ')
                tag = 'th' if r_idx == 0 else 'td'
                row_html = ''
                for cell in cells:
                    cell = cell.strip()
                    css = ''
                    if cell == '':
                        css = ' class="empty-cell"'
                        cell = '(empty)'
                    elif len(cell) < 3 and r_idx > 0:
                        css = ' class="merged-cell"'
                    row_html += (
                        f'<{tag}{css}>{esc(cell)}</{tag}>'
                    )
                html_parts.append(
                    f'<tr>{row_html}</tr>\n'
                )
            html_parts.append('</table>')
    else:
        html_parts.append(
            '<p class="no-table">No tables on this page</p>'
        )

    html_parts.append('</div></div></div>')

# =============================================================
# SECTION 3 — RAW TABLES FROM PDFPLUMBER
# =============================================================
html_parts.append(f"""
<h2 id="tables">🗂 Raw Tables (Direct from pdfplumber)</h2>
<div class="section-stats">
  {len(raw_tables)} tables extracted directly — 
  this is what pdfplumber sees before any processing.
  Highlighted cells: blue = possibly merged/empty cells.
</div>
""")

for t in raw_tables[:20]:  # show first 20
    html_parts.append(f"""
<div class="page-block">
  <div class="page-header">
    <span class="page-num">
      Page {t['page']} — Table {t['table_index']+1}
    </span>
    <span style="font-size:11px;color:#858585;">
      {t['row_count']} rows × {t['col_count']} cols
    </span>
  </div>
  <div style="padding:12px 16px;overflow-x:auto;">
    <table class="extracted">
""")
    for r_idx, row in enumerate(t['rows']):
        tag = 'th' if r_idx == 0 else 'td'
        row_html = ''
        if row:
            for cell in row:
                cell_str = str(cell).strip() if cell else ''
                if cell is None or cell_str == '':
                    row_html += (
                        f'<{tag} class="merged-cell">'
                        f'(merged/empty)</{tag}>'
                    )
                else:
                    row_html += (
                        f'<{tag}>{esc(cell_str)}</{tag}>'
                    )
        html_parts.append(f'<tr>{row_html}</tr>\n')

    html_parts.append('</table></div></div>')

if len(raw_tables) > 20:
    html_parts.append(
        f'<p style="color:#858585;">'
        f'... and {len(raw_tables)-20} more tables. '
        f'Showing first 20 only.</p>'
    )

# =============================================================
# SECTION 4 — ALL CHUNKS
# =============================================================
html_parts.append(f"""
<h2 id="chunks">🔪 All Chunks (first 30)</h2>
<div class="section-stats">
  Total: {len(chunks)} chunks |
  🟡 Yellow border = contains table |
  🔴 Red border = contains errata keyword |
  🟢 Green border = normal text chunk
</div>
""")

for c in chunks[:30]:
    has_tbl = '[TABLE]' in c.text
    has_err = any(
        k in c.text.upper() for k in errata_keywords
    )
    if has_tbl:
        css = 'chunk-has-table'
        tag = '🟡 TABLE'
    elif has_err:
        css = 'chunk-has-errata'
        tag = '🔴 ERRATA'
    else:
        css = 'chunk-normal'
        tag = '🟢 TEXT'

    html_parts.append(f"""
<div class="chunk-block {css}">
  <div class="chunk-header">
    <span>
      Chunk {c.chunk_index} &nbsp;|&nbsp;
      Page {c.page_num} &nbsp;|&nbsp;
      {len(c.text)} chars
    </span>
    <span>{tag}</span>
  </div>
  <div class="chunk-text">{esc(c.text[:400])}</div>
</div>
""")

# =============================================================
# SECTION 5 — ERRATA SPECIFIC CHUNKS
# =============================================================
errata_chunks = [
    c for c in chunks
    if any(k in c.text.upper() for k in errata_keywords)
]

html_parts.append(f"""
<h2 id="errata">🔴 Errata-Specific Chunks ({len(errata_chunks)} found)</h2>
<div class="section-stats">
  These chunks contain errata keywords and will be retrieved
  when the LLM needs to check for silicon bugs and workarounds.
</div>
""")

for c in errata_chunks[:15]:
    html_parts.append(f"""
<div class="chunk-block chunk-has-errata">
  <div class="chunk-header">
    <span>
      Chunk {c.chunk_index} &nbsp;|&nbsp;
      Page {c.page_num} &nbsp;|&nbsp;
      {c.source_file}
    </span>
    <span>🔴 ERRATA</span>
  </div>
  <div class="chunk-text">{esc(c.text[:500])}</div>
</div>
""")

# =============================================================
# CLOSE HTML
# =============================================================
html_parts.append("""
</body>
</html>
""")

# =============================================================
# WRITE AND OPEN
# =============================================================
with open(OUT_FILE, 'w', encoding='utf-8') as f:
    f.write(''.join(html_parts))

print(f"\nReport saved to: {OUT_FILE}")
print("Opening in browser...")

import webbrowser, pathlib
webbrowser.open(
    pathlib.Path(OUT_FILE).resolve().as_uri()
)

print("\n" + "=" * 55)
print("VISUAL INSPECTION REPORT READY")
print("=" * 55)
print(f"File     : extraction_report.html")
print(f"Location : C:\\mcu_assistant\\extraction_report.html")
print(f"Pages    : {len(pages)}")
print(f"Tables   : {len(raw_tables)}")
print(f"Chunks   : {len(chunks)}")
print("=" * 55)
print("Check the browser for visual inspection.")
print("Look specifically at:")
print("  Section 2 — Page by page text vs table side by side")
print("  Section 3 — Raw tables to check merged/split cells")
print("  Section 5 — Errata chunks for keyword detection")
print("=" * 55)