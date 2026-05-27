# Table Extraction Tools — Hermes Usage Guide

> **Audience:** Hermes worker runtime. Reference when Stage 1 discovery or research ingestion needs to extract tables from PDFs, web pages, or images.
> **Env:** `conda activate hermes` (packages defined in `code/environment.yml`).
> **System deps:** tesseract 5.3.4, poppler 24.02.0 (pdftotext), ghostscript 10.02.1 — all pre-installed on host.

---

## 1. Available tools

| Family | Tool | Python import | Best for |
|--------|------|---------------|----------|
| **Structured** | bioc_jats_table | `lxml` + custom | PubMed Central XML full-text |
| | html_jats_table | `beautifulsoup4` | HTML JATS article pages |
| | xlsx_sheet_table | `pandas.read_excel` | Excel supplements |
| **PDF native** | pdfplumber_native_table | `pdfplumber` | Most PDFs with clear borders |
| | pymupdf_native_table | `fitz` (PyMuPDF) | Fast fallback, layout-aware |
| | camelot_lattice_table | `camelot.read_pdf(..., flavor='lattice')` | Grid-ruled tables |
| | camelot_stream_table | `camelot.read_pdf(..., flavor='stream')` | Whitespace-aligned tables |
| | tabula_lattice_table | `tabula.read_pdf(..., lattice=True)` | Java-backed lattice mode |
| | tabula_stream_table | `tabula.read_pdf(..., lattice=False)` | Java-backed stream mode |
| | pdftotext_layout_table | `subprocess` → `pdftotext -layout` | Raw layout preservation |
| **OCR / model-OCR** | image_ocr_table | `pytesseract` + `PIL` | Scanned/image tables |
| | pdf_model_ocr_table | `pdf2image` + vision model | PDFs where native fails |

Web content (not strictly tables, but relevant):
| Tool | Import | Best for |
|------|--------|----------|
| trafilatura | `trafilatura.fetch_url`, `trafilatura.extract` | Clean article text from public URLs |

---

## 2. Pipeline priority

When Hermes encounters a document that may contain tables, attempt in this order:

```
1. Structured     (XML, HTML JATS, XLSX)     — fastest, most accurate
2. PDF native     (pdfplumber, PyMuPDF, camelot, tabula)
3. OCR fallback   (pytesseract, pdf2image + vision model)
```

**Rule:** If native methods return zero rows but tables are visually present, queue OCR recovery and record a loss-report row per `scripts/mo_v5/work_orders.py`.

---

## 3. Quick recipes

### 3.1 PDF with pdfplumber (default first try)

```python
import pdfplumber

with pdfplumber.open("article.pdf") as pdf:
    for i, page in enumerate(pdf.pages, 1):
        tables = page.extract_tables()
        for table in tables:
            # table is list of lists (rows → cells)
            df = pd.DataFrame(table[1:], columns=table[0])
            print(f"Page {i}: {len(df)} rows")
```

### 3.2 PDF with Camelot (lattice vs stream)

```python
import camelot

# Try lattice first (detects ruling lines)
tables = camelot.read_pdf("article.pdf", pages="all", flavor="lattice")
if len(tables) == 0:
    # Fallback to stream (whitespace alignment)
    tables = camelot.read_pdf("article.pdf", pages="all", flavor="stream")

for t in tables:
    df = t.df  # pandas DataFrame
    print(f"Page {t.page}: accuracy {t.accuracy}")
```

### 3.3 PDF with Tabula

```python
import tabula

dfs = tabula.read_pdf("article.pdf", pages="all", lattice=True, multiple_tables=True)
# fallback:
# dfs = tabula.read_pdf("article.pdf", pages="all", lattice=False, multiple_tables=True)
```

### 3.4 PDF with PyMuPDF (fast, layout-aware)

```python
import fitz  # PyMuPDF

doc = fitz.open("article.pdf")
for page in doc:
    tabs = page.find_tables()
    if tabs.tables:
        df = tabs[0].to_pandas()
        print(df)
```

### 3.5 Web page with trafilatura

```python
import trafilatura

downloaded = trafilatura.fetch_url("https://example.com/article")
text = trafilatura.extract(downloaded, include_tables=True, include_comments=False)
# text contains markdown-like tables if present
```

### 3.6 OCR on image-based table

```python
from PIL import Image
import pytesseract

img = Image.open("table.png")
text = pytesseract.image_to_string(img)
# Parse text manually or pass to a structured-extraction LLM prompt
```

### 3.7 PDF → images → OCR (last resort)

```python
from pdf2image import convert_from_path
import pytesseract

images = convert_from_path("scanned.pdf", dpi=300)
for i, img in enumerate(images):
    text = pytesseract.image_to_string(img)
    print(f"Page {i+1}:\n{text}\n")
```

---

## 4. Hermes invocation patterns

**When to use which:**

| Source type | Start with | Fallback |
|-------------|-----------|----------|
| PubMed Central XML | `bioc_jats_table` | `html_jats_table` |
| Publisher HTML page | `html_jats_table` | `trafilatura` extract |
| Excel supplement | `xlsx_sheet_table` (pandas) | — |
| Modern PDF with borders | `pdfplumber_native_table` | `camelot_lattice_table` |
| PDF with whitespace columns | `camelot_stream_table` | `tabula_stream_table` |
| Scanned/image PDF | `pdf_model_ocr_table` or `image_ocr_table` | — |
| Public blog/website | `trafilatura` | `requests` + `BeautifulSoup` |

**Error handling:**
- If a tool raises `ImportError` → package missing from env (should not happen; check `code/environment.yml`).
- If Camelot raises `"ghostscript"` error → system ghostscript is missing (host has 10.02.1).
- If Tabula raises `"Java"` error → Java runtime missing (install `openjdk` if needed).
- If `trafilatura` returns `None` → page blocked, requires JS, or paywalled. Do not retry with auth.

---

## 5. Validation

After extraction, assert:
1. Table has ≥1 row and ≥1 column.
2. Header row is present or inferable.
3. Numeric columns parse without 100% failure (warn if >50% NaN).
4. If multiple methods ran, prefer the one with highest cell count and lowest empty-cell ratio.

Loss reporting: if all methods fail but tables are visible, write a row to the loss report per `scripts/mo_v5/work_orders.py` §worker_rule.

---

## 6. References

- `code/environment.yml` — exact package versions
- `scripts/mo_v5/work_orders.py` — method families and worker rules
- `scripts/mo_v5/validate_worker_artifacts.py` — `TABLE_METHODS` enum
- `scripts/fetch-web-content.py` — trafilatura usage example
