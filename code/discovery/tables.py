"""Table extraction helpers for Stage 1 discovery.

Covers three source classes required by the workflow:

* HTML tables: extracted with pandas.read_html/lxml when available, with a
  BeautifulSoup/stdlib parser fallback.
* PDF tables: extracted with Camelot first, pdfplumber second, tabula third,
  and pdftotext -layout as a final fallback.
* Image tables: extracted with OpenCV preprocessing + pytesseract OCR, falling
  back to raw tesseract CLI if needed.

The extractor preserves table rows as source-derived text. It does not interpret
or normalize recommendations. Rows containing likely numeric ranges/lab values
are flagged so Stage 2 can focus on them without hallucinating table content.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


RANGE_RE = re.compile(
    r"(?ix)"
    r"(?:"
    r"\b\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?\b"
    r"|"
    r"(?:<|>|≤|≥|<=|>=)\s*\d+(?:\.\d+)?"
    r"|"
    r"\b\d+(?:\.\d+)?\s*(?:mg/dl|mmol/l|%|iu/ml|µiu/ml|u/l|ng/ml|mg/l|pmol/l|nmol/l)\b"
    r")"
)


@dataclass
class ExtractedTable:
    source_type: str                 # html | pdf | image
    extraction_method: str           # parser/tool used
    rows: list[list[str]]
    caption: str | None = None
    page_number: int | None = None
    table_index: int = 0
    range_rows: list[int] | None = None
    status: str = "ok"              # ok | unavailable | failed
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    value = html.unescape(str(value))
    if value.lower() == "nan":
        return ""
    value = re.sub(r"\s+", " ", value).strip()
    return value


def clean_rows(rows: list[list[Any]]) -> list[list[str]]:
    cleaned: list[list[str]] = []
    for row in rows:
        out = [clean_cell(cell) for cell in row]
        out = [cell for cell in out if cell]
        if out:
            cleaned.append(out)
    return cleaned


def row_has_range(row: list[str]) -> bool:
    return bool(RANGE_RE.search(" | ".join(row)))


def annotate_range_rows(rows: list[list[str]]) -> list[int]:
    return [idx for idx, row in enumerate(rows) if row_has_range(row)]


def _mk_table(
    source_type: str,
    method: str,
    rows: list[list[Any]],
    *,
    caption: str | None = None,
    page_number: int | None = None,
    table_index: int = 0,
) -> ExtractedTable | None:
    cleaned = clean_rows(rows)
    if not cleaned:
        return None
    return ExtractedTable(
        source_type=source_type,
        extraction_method=method,
        rows=cleaned,
        caption=clean_cell(caption) or None,
        page_number=page_number,
        table_index=table_index,
        range_rows=annotate_range_rows(cleaned),
    )


class _HTMLTableParser(HTMLParser):
    """Fallback parser when pandas/lxml/bs4 cannot parse HTML tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[ExtractedTable] = []
        self._in_table = False
        self._table_depth = 0
        self._in_row = False
        self._in_cell = False
        self._in_caption = False
        self._current_rows: list[list[str]] = []
        self._current_row: list[str] = []
        self._cell_parts: list[str] = []
        self._caption_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            if not self._in_table:
                self._in_table = True
                self._current_rows = []
                self._caption_parts = []
            self._table_depth += 1
        if not self._in_table:
            return
        if tag == "caption":
            self._in_caption = True
        elif tag == "tr":
            self._in_row = True
            self._current_row = []
        elif tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []
        elif tag == "br" and self._in_cell:
            self._cell_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if not self._in_table:
            return
        if tag in {"td", "th"} and self._in_cell:
            self._current_row.append(clean_cell(" ".join(self._cell_parts)))
            self._cell_parts = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            row = [cell for cell in self._current_row if cell]
            if row:
                self._current_rows.append(row)
            self._current_row = []
            self._in_row = False
        elif tag == "caption":
            self._in_caption = False
        elif tag == "table":
            self._table_depth -= 1
            if self._table_depth <= 0:
                table = _mk_table(
                    "html",
                    "stdlib_htmlparser",
                    self._current_rows,
                    caption=" ".join(self._caption_parts),
                    table_index=len(self.tables),
                )
                if table:
                    self.tables.append(table)
                self._in_table = False
                self._table_depth = 0
                self._current_rows = []
                self._caption_parts = []

    def handle_data(self, data: str) -> None:
        if not self._in_table:
            return
        if self._in_cell:
            self._cell_parts.append(data)
        elif self._in_caption:
            self._caption_parts.append(data)


def _extract_html_tables_pandas(html_text: str) -> list[ExtractedTable]:
    import pandas as pd

    dfs = pd.read_html(html_text, flavor=["lxml", "bs4"])
    tables: list[ExtractedTable] = []
    for idx, df in enumerate(dfs):
        rows: list[list[Any]] = []
        header = [clean_cell(col) for col in list(df.columns)]
        if any(header) and not all(str(col).startswith("Unnamed") for col in header):
            rows.append(header)
        rows.extend(df.astype(object).where(df.notna(), "").values.tolist())
        table = _mk_table("html", "pandas-read_html", rows, table_index=idx)
        if table:
            tables.append(table)
    return tables


def _extract_html_tables_bs4(html_text: str) -> list[ExtractedTable]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_text or "", "lxml")
    tables: list[ExtractedTable] = []
    for idx, table_tag in enumerate(soup.find_all("table")):
        caption_tag = table_tag.find("caption")
        rows: list[list[str]] = []
        for tr in table_tag.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            if cells:
                rows.append(cells)
        table = _mk_table(
            "html",
            "beautifulsoup-lxml",
            rows,
            caption=caption_tag.get_text(" ", strip=True) if caption_tag else None,
            table_index=len(tables),
        )
        if table:
            tables.append(table)
    return tables


def extract_html_tables(html_text: str) -> list[ExtractedTable]:
    errors: list[str] = []
    for fn in (_extract_html_tables_pandas, _extract_html_tables_bs4):
        try:
            tables = fn(html_text)
            if tables:
                return tables
        except Exception as exc:
            errors.append(f"{fn.__name__}: {exc}")
    parser = _HTMLTableParser()
    parser.feed(html_text or "")
    parser.close()
    return parser.tables


def _lines_to_tables(lines: list[str], source_type: str, method: str) -> list[ExtractedTable]:
    tables: list[ExtractedTable] = []
    block: list[str] = []

    def flush() -> None:
        nonlocal block
        if len(block) < 2:
            block = []
            return
        rows: list[list[str]] = []
        for line in block:
            line = line.strip()
            if not line:
                continue
            if "\t" in line:
                cells = [clean_cell(c) for c in line.split("\t")]
            elif "|" in line:
                cells = [clean_cell(c) for c in line.split("|")]
            else:
                cells = [clean_cell(c) for c in re.split(r"\s{2,}", line)]
            if len(cells) >= 2:
                rows.append([c for c in cells if c])
        table = _mk_table(source_type, method, rows, table_index=len(tables))
        if table and len(table.rows) >= 2:
            tables.append(table)
        block = []

    for line in lines:
        stripped = line.rstrip()
        looks_tabular = ("\t" in stripped or "|" in stripped or bool(re.search(r"\S\s{2,}\S", stripped)))
        if looks_tabular:
            block.append(stripped)
        else:
            flush()
    flush()
    return tables


def _extract_pdf_tables_pymupdf(path: Path) -> list[ExtractedTable]:
    import fitz

    out: list[ExtractedTable] = []
    doc = fitz.open(path)
    for page_index, page in enumerate(doc, start=1):
        finder = page.find_tables()
        for raw_table in getattr(finder, "tables", []) or []:
            rows = raw_table.extract()
            table = _mk_table("pdf", "pymupdf-find_tables", rows, page_number=page_index, table_index=len(out))
            if table:
                out.append(table)
    return out


def _extract_pdf_tables_camelot(path: Path) -> list[ExtractedTable]:
    import camelot

    out: list[ExtractedTable] = []
    for flavor in ("lattice", "stream"):
        try:
            parsed = camelot.read_pdf(str(path), pages="all", flavor=flavor)
        except Exception:
            continue
        for table_obj in parsed:
            rows = table_obj.df.values.tolist()
            page = None
            try:
                page = int(table_obj.page)
            except Exception:
                pass
            table = _mk_table("pdf", f"camelot-{flavor}", rows, page_number=page, table_index=len(out))
            if table:
                out.append(table)
    return out


def _extract_pdf_tables_pdfplumber(path: Path) -> list[ExtractedTable]:
    import pdfplumber

    out: list[ExtractedTable] = []
    with pdfplumber.open(path) as pdf:
        for page_index, page in enumerate(pdf.pages, start=1):
            for raw in page.extract_tables() or []:
                table = _mk_table("pdf", "pdfplumber", raw, page_number=page_index, table_index=len(out))
                if table:
                    out.append(table)
    return out


def _extract_pdf_tables_tabula(path: Path) -> list[ExtractedTable]:
    import tabula

    out: list[ExtractedTable] = []
    for lattice, method in ((True, "tabula-lattice"), (False, "tabula-stream")):
        try:
            dfs = tabula.read_pdf(str(path), pages="all", multiple_tables=True, lattice=lattice)
        except Exception:
            continue
        for df in dfs or []:
            rows: list[list[Any]] = []
            header = [clean_cell(col) for col in list(df.columns)]
            if any(header):
                rows.append(header)
            rows.extend(df.astype(object).where(df.notna(), "").values.tolist())
            table = _mk_table("pdf", method, rows, table_index=len(out))
            if table:
                out.append(table)
    return out


def _extract_pdf_tables_pdftotext(path: Path) -> list[ExtractedTable]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "pdf-layout.txt"
        proc = subprocess.run([pdftotext, "-layout", str(path), str(out)], capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            return []
        text = out.read_text(errors="replace") if out.exists() else ""
    return _lines_to_tables(text.splitlines(), "pdf", "pdftotext-layout")


def _table_quality(table: ExtractedTable) -> tuple[int, int, int]:
    cells = [cell for row in table.rows for cell in row if clean_cell(cell)]
    range_count = len(table.range_rows or [])
    return (range_count, len(cells), len(table.rows))


def _extract_pdf_tables_ocr(path: Path, *, max_pages: int = 5) -> list[ExtractedTable]:
    from pdf2image import convert_from_path
    import pytesseract

    out: list[ExtractedTable] = []
    images = convert_from_path(str(path), dpi=300, first_page=1, last_page=max_pages)
    for page_index, image in enumerate(images, start=1):
        text = pytesseract.image_to_string(image, config="--psm 6")
        for table in _lines_to_tables(text.splitlines(), "pdf", "pdf2image-pytesseract"):
            table.page_number = page_index
            table.table_index = len(out)
            out.append(table)
    return out


def extract_pdf_tables(path: str | Path) -> list[ExtractedTable]:
    path = Path(path)
    errors: list[str] = []
    candidate_sets: list[list[ExtractedTable]] = []
    for name, fn in (
        ("pdfplumber", _extract_pdf_tables_pdfplumber),
        ("pymupdf", _extract_pdf_tables_pymupdf),
        ("camelot", _extract_pdf_tables_camelot),
        ("tabula", _extract_pdf_tables_tabula),
        ("pdftotext", _extract_pdf_tables_pdftotext),
    ):
        try:
            tables = fn(path)
            if tables:
                for idx, table in enumerate(tables):
                    table.table_index = idx
                candidate_sets.append(tables)
        except Exception as exc:
            errors.append(f"{name}: {exc}")
    if candidate_sets:
        best = max(
            candidate_sets,
            key=lambda tables: (
                sum(_table_quality(t)[0] for t in tables),
                sum(_table_quality(t)[1] for t in tables),
                sum(_table_quality(t)[2] for t in tables),
            ),
        )
        return best
    try:
        ocr_tables = _extract_pdf_tables_ocr(path)
        if ocr_tables:
            return ocr_tables
    except Exception as exc:
        errors.append(f"pdf2image-ocr: {exc}")
    return [ExtractedTable("pdf", "configured-pdf-extractors", [], status="failed", error="; ".join(errors) or "no tables found")]


def _ocr_image_text_pytesseract(path: Path) -> str:
    import cv2
    import pytesseract

    image = cv2.imread(str(path))
    if image is None:
        raise ValueError(f"could not read image: {path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    return pytesseract.image_to_string(gray, config="--psm 6")


def _ocr_image_text_cli(path: Path) -> str:
    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise RuntimeError("tesseract command not found")
    proc = subprocess.run([tesseract, str(path), "stdout", "--psm", "6"], capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout


def extract_image_tables(path: str | Path) -> list[ExtractedTable]:
    path = Path(path)
    errors: list[str] = []
    for method, fn in (("opencv-pytesseract", _ocr_image_text_pytesseract), ("tesseract-cli", _ocr_image_text_cli)):
        try:
            text = fn(path)
            tables = _lines_to_tables(text.splitlines(), "image", method)
            if tables:
                return tables
            if text.strip():
                rows = [[line.strip()] for line in text.splitlines() if line.strip()]
                table = _mk_table("image", method, rows, table_index=0)
                if table:
                    return [table]
        except Exception as exc:
            errors.append(f"{method}: {exc}")
    return [ExtractedTable("image", "configured-image-extractors", [], status="failed", error="; ".join(errors) or "no OCR text")]


def format_tables_for_transcript(tables: list[ExtractedTable]) -> str:
    blocks: list[str] = []
    for table in tables:
        if table.status != "ok" or not table.rows:
            continue
        label = f"[{table.source_type.upper()} TABLE {table.table_index + 1}]"
        if table.page_number is not None:
            label += f" page {table.page_number}"
        if table.caption:
            label += f" {table.caption}"
        label += f" ({table.extraction_method})"
        lines = [label]
        for idx, row in enumerate(table.rows):
            prefix = "* " if table.range_rows and idx in table.range_rows else "  "
            lines.append(prefix + " | ".join(row))
        blocks.append("\n".join(lines))
    if not blocks:
        return ""
    return "\n\nExtracted source tables:\n" + "\n\n".join(blocks)
