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