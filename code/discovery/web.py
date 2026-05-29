"""Stage 1 public web/source discovery.

This module implements the first narrow discovery surface from
``docs/agentic-workflow/03-social-agents-spec.md``: public blogs, websites,
and Substack-like pages seeded from ``input/practitioner_registry.json``.

The implementation is intentionally conservative:

* only HTTP(S) public pages are fetched;
* authenticated/paywalled/private/manual-only surfaces are skipped;
* content saved in fixtures is text actually fetched from the page;
* every emitted fixture validates against ``source_fixture.schema.json``;
* ``synthetic`` is always false and ``verification_status`` is always
  ``verified_real_source`` for saved fixtures.

It does not use an LLM and does not invent transcripts.
"""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import re
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urldefrag, urljoin, urlparse

import requests
from jsonschema import Draft202012Validator

try:
    import trafilatura
except ImportError:  # pragma: no cover - environment guard
    trafilatura = None

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from code.discovery.tables import extract_html_tables, format_tables_for_transcript

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = PROJECT_ROOT / "input" / "practitioner_registry.json"
CATEGORIES_PATH = PROJECT_ROOT / "input" / "marker_categories.yaml"
SCHEMA_PATH = PROJECT_ROOT / "code" / "schemas" / "source_fixture.schema.json"
DEFAULT_FIXTURE_DIR = PROJECT_ROOT / "fixtures" / "sources"
DEFAULT_DISCOVERY_DIR = PROJECT_ROOT / "runs" / "stage1-web-discovery" / "discovery"

USER_AGENT = (
    "metabolicum-agentic-research/0.1 "
    "(+https://github.com/metabolicum; public-page citation research)"
)
TIMEOUT = 25
MAX_BYTES = 3_000_000
MAX_LINKS_PER_SEED = 80
MIN_TEXT_CHARS = 600

PILOT_MARKERS = ["hba1c", "lpa", "fasting-insulin", "tg-hdl-ratio"]

MARKER_TERMS: dict[str, list[str]] = {
    "hba1c": [
        "hba1c",
        "a1c",
        "hemoglobin a1c",
        "haemoglobin a1c",
        "glycated hemoglobin",
        "glycated haemoglobin",
    ],
    "lpa": [
        "lp(a)",
        "lpa",
        "lipoprotein(a)",
        "lipoprotein a",
        "apo(a)",
        "apolipoprotein(a)",
    ],
    "fasting-insulin": [
        "fasting insulin",
        "fasting-insulin",
        "insulin level",
        "insulin levels",
        "hyperinsulinemia",
        "hyperinsulinaemia",
        "insulin resistance",
        "homa-ir",
        "homa ir",
        "homa",
    ],
    "tg-hdl-ratio": [
        "tg/hdl",
        "tg hdl",
        "tg:hdl",
        "triglyceride hdl",
        "triglyceride-to-hdl",
        "triglyceride to hdl",
        "triglycerides to hdl",
        "triglyceride/hdl",
        "triglycerides/hdl",
        "hdl ratio",
    ],
    "igf-1": [
        "igf-1",
        "igf 1",
        "insulin-like growth factor 1",
        "insulin-like growth factor-1",
        "insulin like growth factor 1",
        "somatomedin c",
    ],
    "vitamin-d": [
        "vitamin d",
        "vitamin-d",
        "25-hydroxyvitamin d",
        "25 hydroxyvitamin d",
        "25(oh)d",
        "25-oh-d",
        "cholecalciferol",
    ],
    "crp-standard": [
        "c-reactive protein",
        "c reactive protein",
        "crp",
        "hs-crp",
        "hs crp",
        "high sensitivity crp",
    ],
    "hdl-cholesterol": [
        "hdl cholesterol",
        "hdl-cholesterol",
        "hdl-c",
        "hdl c",
        "high density lipoprotein cholesterol",
    ],
    "uric-acid": [
        "uric acid",
        "uric-acid",
        "hyperuricemia",
        "hyperuricaemia",
        "urate",
        "serum uric acid",
    ],
    "fructosamine": [
        "fructosamine",
        "serum fructosamine",
        "glycated serum protein",
    ],
}

SEARCH_TERMS: dict[str, list[str]] = {
    "hba1c": ["hba1c", "a1c", "hemoglobin a1c"],
    "lpa": ["lp(a)", "lipoprotein(a)", "lipoprotein a"],
    "fasting-insulin": ["fasting insulin", "insulin resistance", "homa-ir"],
    "tg-hdl-ratio": ["tg/hdl ratio", "triglyceride hdl ratio", "triglyceride-to-hdl"],
    "igf-1": ["igf-1", "insulin-like growth factor 1", "somatomedin c"],
    "vitamin-d": ["vitamin d", "25-hydroxyvitamin d", "25(oh)d"],
    "crp-standard": ["c-reactive protein", "crp", "hs-crp"],
    "hdl-cholesterol": ["hdl cholesterol", "hdl-c", "high density lipoprotein"],
    "uric-acid": ["uric acid", "hyperuricemia", "serum uric acid"],
    "fructosamine": ["fructosamine", "glycated serum protein"],
}

# A few public search URL patterns used when a site has no discoverable sitemap
# or search page. These are still registry-seeded, public-page fetches.
SEARCH_PATH_PATTERNS = [
    "/?s={q}",
    "/search?q={q}",
    "/search/{q}",
    "/blog?query={q}",
    "/articles?query={q}",
]

SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico",
    ".css", ".js", ".json", ".xml", ".zip", ".gz", ".tar",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".m4a",
}

BLOCKED_URL_PARTS = [
    "/login", "/signin", "/sign-in", "/signup", "/cart", "/checkout",
    "/account", "/privacy", "/terms", "/wp-admin", "mailto:", "tel:",
]


@dataclass(frozen=True)
class PractitionerSeed:
    practitioner_id: str
    canonical_name: str
    source_tier: str
    marker_affinity: list[str]
    platform: str
    base_url: str
    priority: str


@dataclass
class FetchedPage:
    url: str
    status_code: int
    content_type: str
    html_text: str
    retrieved_at: str
    last_modified: str | None


@dataclass
class ExtractedPage:
    url: str
    title: str
    text: str
    links: list[str]
    published_at: str | None
    language: str


class ReadableHTMLParser(HTMLParser):
    """Small stdlib HTML-to-text parser with title/meta/link extraction."""

    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "dd", "div", "dl",
        "dt", "figcaption", "figure", "footer", "h1", "h2", "h3", "h4", "h5",
        "h6", "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section",
        "table", "td", "th", "tr", "ul",
    }
    HIDDEN_TAGS = {"script", "style", "noscript", "template", "svg", "canvas"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.parts: list[str] = []
        self.links: list[str] = []
        self.title_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.language = "en"
        self._hidden_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        if tag in self.HIDDEN_TAGS:
            self._hidden_depth += 1
            return
        if tag == "html" and attrs_dict.get("lang"):
            self.language = attrs_dict["lang"].split("-")[0].lower() or "en"
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            key = (attrs_dict.get("property") or attrs_dict.get("name") or "").lower()
            value = attrs_dict.get("content") or ""
            if key and value:
                self.meta[key] = html.unescape(value).strip()
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(urljoin(self.base_url, attrs_dict["href"]))
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.HIDDEN_TAGS and self._hidden_depth:
            self._hidden_depth -= 1
            return
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._hidden_depth:
            return
        text = html.unescape(data)
        if self._in_title:
            self.title_parts.append(text)
        if text.strip():
            self.parts.append(text)

    def cleaned_text(self) -> str:
        raw = " ".join(self.parts)
        raw = re.sub(r"[ \t\r\f\v]+", " ", raw)
        raw = re.sub(r"\n\s*", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        lines = [line.strip() for line in raw.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines).strip()

    def title(self) -> str:
        candidates = [
            self.meta.get("og:title"),
            self.meta.get("twitter:title"),
            " ".join(self.title_parts).strip(),
        ]
        for candidate in candidates:
            if candidate:
                return re.sub(r"\s+", " ", candidate).strip()
        return "Untitled public page"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_url(url: str) -> str:
    url, _frag = urldefrag(url.strip())
    parsed = urlparse(url)
    if not parsed.scheme and parsed.netloc == "":
        return url
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    return parsed._replace(scheme=scheme, netloc=netloc, path=path).geturl()


def same_site(url: str, base_url: str) -> bool:
    u = urlparse(url)
    b = urlparse(base_url)
    return u.scheme in {"http", "https"} and u.netloc.lower().lstrip("www.") == b.netloc.lower().lstrip("www.")


def should_skip_url(url: str) -> bool:
    lower = url.lower()
    if any(part in lower for part in BLOCKED_URL_PARTS):
        return True
    path = urlparse(lower).path
    return any(path.endswith(ext) for ext in SKIP_EXTENSIONS)


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_categories() -> dict[str, Any]:
    """Load marker categories from YAML."""
    if yaml is None or not CATEGORIES_PATH.exists():
        return {"categories": []}
    return yaml.safe_load(CATEGORIES_PATH.read_text()) or {"categories": []}


def _practitioner_seed_from_registry(practitioner: dict, surface: dict, marker_affinity: list[str]) -> PractitionerSeed | None:
    """Build a PractitionerSeed from registry data if surface is crawlable."""
    platform = surface.get("platform")
    mode = surface.get("discovery_mode")
    url = surface.get("handle_or_url", "")
    if platform not in {"website", "substack"}:
        return None
    if mode == "do_not_crawl" or surface.get("priority") == "manual_only":
        return None
    if not url.startswith(("http://", "https://")):
        return None
    return PractitionerSeed(
        practitioner_id=practitioner["id"],
        canonical_name=practitioner["canonical_name"],
        source_tier=practitioner.get("source_tier", "D"),
        marker_affinity=marker_affinity,
        platform=platform,
        base_url=normalize_url(url),
        priority=surface.get("priority", "secondary"),
    )


def website_seeds(registry: dict[str, Any], markers: list[str]) -> list[PractitionerSeed]:
    markers_set = set(markers)
    seeds: list[PractitionerSeed] = []
    seen_ids: set[str] = set()

    # Phase 1: direct practitioner affinity
    for practitioner in registry.get("practitioners", []):
        affinity = practitioner.get("marker_affinity", []) or []
        if markers_set.isdisjoint(affinity):
            continue
        for surface in practitioner.get("surfaces", []) or []:
            seed = _practitioner_seed_from_registry(practitioner, surface, affinity)
            if seed is None:
                continue
            key = f"{seed.practitioner_id}|{seed.base_url}"
            if key not in seen_ids:
                seen_ids.add(key)
                seeds.append(seed)

    # Phase 2: category fallback for markers with no direct affinity
    categories_data = load_categories()
    categories = categories_data.get("categories", {})
    if isinstance(categories, dict):
        categories = list(categories.values())
    for marker in markers:
        # Skip if already has direct seeds
        if any(marker in s.marker_affinity for s in seeds):
            continue
        # Find categories containing this marker
        for cat in categories:
            if marker not in cat.get("markers", []):
                continue
            # Add practitioners from this category
            cat_practitioner_ids = set(cat.get("practitioners", []))
            for practitioner in registry.get("practitioners", []):
                if practitioner["id"] not in cat_practitioner_ids:
                    continue
                affinity = practitioner.get("marker_affinity", []) or []
                # Extend affinity with category markers so the seed is selected
                extended_affinity = list(set(affinity + cat.get("markers", [])))
                for surface in practitioner.get("surfaces", []) or []:
                    seed = _practitioner_seed_from_registry(practitioner, surface, extended_affinity)
                    if seed is None:
                        continue
                    key = f"{seed.practitioner_id}|{seed.base_url}"
                    if key not in seen_ids:
                        seen_ids.add(key)
                        seeds.append(seed)

    tier_rank = {"A": 0, "B": 1, "C": 2, "D": 3}
    priority_rank = {"primary": 0, "secondary": 1, "manual_only": 2}
    seeds.sort(key=lambda s: (tier_rank.get(s.source_tier, 9), priority_rank.get(s.priority, 9), s.canonical_name))
    return seeds


def fetch_url(session: requests.Session, url: str) -> FetchedPage | None:
    try:
        response = session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True)
    except requests.RequestException:
        return None
    status = response.status_code
    content_type = response.headers.get("content-type", "")
    if status >= 400:
        return FetchedPage(url=response.url, status_code=status, content_type=content_type, html_text="", retrieved_at=now_utc(), last_modified=None)
    if "text/html" not in content_type and "application/xhtml" not in content_type and content_type:
        return FetchedPage(url=response.url, status_code=status, content_type=content_type, html_text="", retrieved_at=now_utc(), last_modified=None)
    chunks: list[bytes] = []
    total = 0
    try:
        for chunk in response.iter_content(chunk_size=65536):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_BYTES:
                break
            chunks.append(chunk)
    except requests.RequestException:
        return None
    response.close()
    encoding = response.encoding or "utf-8"
    body = b"".join(chunks).decode(encoding, errors="replace")
    return FetchedPage(
        url=normalize_url(response.url),
        status_code=status,
        content_type=content_type,
        html_text=body,
        retrieved_at=now_utc(),
        last_modified=response.headers.get("last-modified"),
    )


def extract_html(page: FetchedPage) -> ExtractedPage:
    parser = ReadableHTMLParser(page.url)
    parser.feed(page.html_text)
    parser.close()
    published_at = first_datetime([
        parser.meta.get("article:published_time"),
        parser.meta.get("article:modified_time"),
        parser.meta.get("date"),
        parser.meta.get("dc.date"),
        parser.meta.get("dc.date.issued"),
        page.last_modified,
    ])
    links = []
    seen = set()
    for link in parser.links:
        norm = normalize_url(link)
        if norm not in seen:
            seen.add(norm)
            links.append(norm)
    text = parser.cleaned_text()
    if trafilatura is not None:
        try:
            extracted = trafilatura.extract(
                page.html_text,
                url=page.url,
                include_tables=True,
                include_comments=False,
                output_format="txt",
            )
            if extracted and len(extracted) >= max(200, len(text) // 3):
                text = extracted.strip()
        except Exception:
            # Fall back to the deterministic parser. Stage 1 must not fail a
            # public source just because article-cleaning heuristics fail.
            pass
    table_text = format_tables_for_transcript(extract_html_tables(page.html_text))
    if table_text and table_text.strip() not in text:
        text = f"{text}\n\n{table_text}" if text else table_text.strip()
    return ExtractedPage(
        url=page.url,
        title=parser.title(),
        text=text,
        links=links,
        published_at=published_at,
        language=parser.language,
    )


def first_datetime(values: list[str | None]) -> str | None:
    for value in values:
        if not value:
            continue
        try:
            dt = email.utils.parsedate_to_datetime(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except Exception:
            pass
        try:
            cleaned = value.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        except Exception:
            continue
    return None


def marker_matches(text: str, markers: list[str]) -> list[str]:
    lower = text.lower()
    matches: list[str] = []
    for marker in markers:
        terms = MARKER_TERMS.get(marker, [marker])
        for term in terms:
            if term.lower() == "lpa":
                # Avoid false positives from URL slugs such as "help" while
                # still allowing the no-parentheses biochemical shorthand.
                pattern = r"(?<![a-z0-9])lpa(?![a-z0-9])"
            else:
                escaped = re.escape(term.lower())
                escaped = escaped.replace(r"\ ", r"[\s\-_/]*")
                escaped = escaped.replace(r"\(", r"\s*\(\s*")
                escaped = escaped.replace(r"\)", r"\s*\)\s*")
                pattern = r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])"
            if re.search(pattern, lower):
                matches.append(marker)
                break
    return matches


def keyword_score(text: str, marker: str) -> int:
    lower = text.lower()
    score = 0
    for term in MARKER_TERMS.get(marker, [marker]):
        score += len(re.findall(re.escape(term.lower()), lower))
    return score


def candidate_link_score(url: str, anchor_context: str, markers: list[str]) -> int:
    haystack = f"{url} {anchor_context}".lower()
    score = 0
    for marker in markers:
        for term in MARKER_TERMS.get(marker, [marker]) + SEARCH_TERMS.get(marker, []):
            if term.lower() in haystack:
                score += 5
    if any(part in haystack for part in ["blog", "article", "post", "learn", "health", "lipid", "diabetes", "insulin"]):
        score += 1
    return score


def site_search_urls(base_url: str, marker: str) -> list[str]:
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    urls: list[str] = []
    for term in SEARCH_TERMS.get(marker, [marker]):
        q = quote_plus(term)
        for pattern in SEARCH_PATH_PATTERNS:
            urls.append(origin + pattern.format(q=q))
    return urls


def discover_candidates_for_seed(session: requests.Session, seed: PractitionerSeed, marker: str) -> list[ExtractedPage]:
    candidates: list[ExtractedPage] = []
    queue: list[str] = [seed.base_url, *site_search_urls(seed.base_url, marker)]
    seen: set[str] = set()
    processed = 0

    while queue and processed < MAX_LINKS_PER_SEED:
        url = normalize_url(queue.pop(0))
        if url in seen or should_skip_url(url) or not same_site(url, seed.base_url):
            continue
        seen.add(url)
        processed += 1
        page = fetch_url(session, url)
        time.sleep(0.15)
        if not page or page.status_code >= 400 or not page.html_text:
            continue
        extracted = extract_html(page)
        matched = marker_matches(f"{extracted.title}\n{extracted.text}", [marker])
        if matched and len(extracted.text) >= MIN_TEXT_CHARS:
            candidates.append(extracted)
        # Follow likely marker-relevant links from seed/search pages.
        scored_links = []
        for link in extracted.links:
            if not same_site(link, seed.base_url) or should_skip_url(link):
                continue
            sc = candidate_link_score(link, extracted.title, [marker])
            if sc > 0:
                scored_links.append((sc, link))
        for _score, link in sorted(scored_links, reverse=True)[:20]:
            if link not in seen and link not in queue:
                queue.append(link)
    candidates.sort(key=lambda page: keyword_score(f"{page.title}\n{page.text}", marker), reverse=True)
    return candidates


def fixture_id_for_url(url: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, normalize_url(url)))


def domain_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def slugify(value: str, max_len: int = 70) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug[:max_len].strip("-") or "source")


def build_fixture(page: ExtractedPage, seed: PractitionerSeed, expected_markers: list[str]) -> dict[str, Any]:
    text = page.text.strip()
    digest = hashlib.sha256(text.encode()).hexdigest()
    fixture = {
        "schema_version": "1",
        "source_id": fixture_id_for_url(page.url),
        "source_url": page.url,
        "source_type": "blog",
        "platform": domain_platform(page.url),
        "title": page.title[:300] or "Untitled public page",
        "retrieved_at": now_utc(),
        "published_at": page.published_at,
        "source_language": page.language or "en",
        "speaker_or_author": seed.canonical_name,
        "speaker_registry_id": seed.practitioner_id,
        "license": "all_rights_reserved_public_web_page",
        "transcript_method": "public_page_html_to_text",
        "transcript_text": text,
        "transcript_sha256": digest,
        "expected_markers": expected_markers,
        "notes": (
            "Stage 1 web discovery fixture. Text was fetched from a public HTTP(S) page "
            "seeded by input/practitioner_registry.json; no synthetic content."
        ),
        "synthetic": False,
        "verification_status": "verified_real_source",
    }
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: dict[str, Any]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(fixture), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
        raise ValueError(f"fixture schema validation failed: {detail}")
    digest = hashlib.sha256(fixture["transcript_text"].encode()).hexdigest()
    if digest != fixture["transcript_sha256"]:
        raise ValueError("fixture transcript_sha256 mismatch")
    if fixture.get("synthetic") is not False:
        raise ValueError("fixture synthetic must be false")
    if fixture.get("verification_status") != "verified_real_source":
        raise ValueError("fixture verification_status must be verified_real_source")


def write_fixture(fixture: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = (fixture.get("expected_markers") or ["marker"])[0]
    base = slugify(fixture.get("platform") or domain_platform(fixture.get("source_url", "")), 24)
    prefix = f"{marker}-{base}"
    existing = sorted(output_dir.glob(f"{prefix}-*.json"))
    source_id = fixture.get("source_id")
    for path in existing:
        try:
            current = json.loads(path.read_text())
        except Exception:
            continue
        if current.get("source_id") == source_id or current.get("source_url") == fixture.get("source_url"):
            path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
            return path
    path = output_dir / f"{prefix}-{len(existing) + 1:02d}.json"
    path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
    return path


def discover_real_fixtures(markers: list[str], *, per_marker: int = 1) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    registry = load_registry()
    seeds = website_seeds(registry, markers)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})

    selected: list[dict[str, Any]] = []
    log: list[dict[str, Any]] = []
    used_urls: set[str] = set()

    for marker in markers:
        marker_selected = 0
        marker_seeds = [s for s in seeds if marker in s.marker_affinity]
        log.append({"marker": marker, "event": "marker_start", "seed_count": len(marker_seeds)})
        for seed in marker_seeds:
            if marker_selected >= per_marker:
                break
            candidates = discover_candidates_for_seed(session, seed, marker)
            log.append({
                "marker": marker,
                "event": "seed_checked",
                "practitioner_id": seed.practitioner_id,
                "base_url": seed.base_url,
                "candidates": len(candidates),
            })
            for page in candidates:
                if page.url in used_urls:
                    continue
                matches = marker_matches(f"{page.title}\n{page.text}", markers)
                if marker not in matches:
                    continue
                # Search-result pages are useful discovery intermediates but
                # weak evidence-bearing fixtures. If a search/archive page is
                # the first apparent match, fetch its marker-relevant article
                # links once more and prefer concrete articles.
                if "/?s=" in page.url or "/search" in page.url or "archive" in page.url.lower():
                    linked_pages: list[ExtractedPage] = []
                    for link in page.links[:80]:
                        if not same_site(link, seed.base_url) or should_skip_url(link):
                            continue
                        if candidate_link_score(link, page.title, [marker]) <= 0:
                            continue
                        linked = fetch_url(session, link)
                        if linked and linked.status_code < 400 and linked.html_text:
                            extracted_link = extract_html(linked)
                            if marker in marker_matches(f"{extracted_link.title}\n{extracted_link.text}", markers):
                                linked_pages.append(extracted_link)
                    if linked_pages:
                        linked_pages.sort(key=lambda p: keyword_score(f"{p.title}\n{p.text}", marker), reverse=True)
                        page = linked_pages[0]
                        matches = marker_matches(f"{page.title}\n{page.text}", markers)
                try:
                    fixture = build_fixture(page, seed, matches)
                except Exception as exc:
                    log.append({"marker": marker, "event": "fixture_rejected", "url": page.url, "error": str(exc)})
                    continue
                selected.append(fixture)
                used_urls.add(page.url)
                marker_selected += 1
                log.append({
                    "marker": marker,
                    "event": "fixture_selected",
                    "url": page.url,
                    "title": page.title,
                    "expected_markers": matches,
                    "sha256": fixture["transcript_sha256"],
                })
                break
        if marker_selected < per_marker:
            log.append({"marker": marker, "event": "marker_incomplete", "selected": marker_selected, "needed": per_marker})
    return selected, log



def _project_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)

def write_discovery_artifacts(fixtures: list[dict[str, Any]], log: list[dict[str, Any]], discovery_dir: Path) -> None:
    discovery_dir.mkdir(parents=True, exist_ok=True)
    ranked = []
    for fixture in fixtures:
        ranked.append({
            "source_id": fixture["source_id"],
            "source_url": fixture["source_url"],
            "source_type": fixture["source_type"],
            "platform": fixture["platform"],
            "title": fixture["title"],
            "speaker_or_author": fixture.get("speaker_or_author"),
            "speaker_registry_id": fixture.get("speaker_registry_id"),
            "expected_markers": fixture.get("expected_markers", []),
            "keyword_score": sum(keyword_score(fixture["transcript_text"], m) for m in fixture.get("expected_markers", [])),
            "semantic_score": None,
            "final_discovery_score": None,
            "match_reason": "public_web_marker_keyword_match",
            "semantic_model": None,
            "semantic_threshold": None,
            "scoring_config_version": "stage1-web-keyword-v1",
            "retrieved_at": fixture["retrieved_at"],
            "raw_sha256": fixture["transcript_sha256"],
        })
    (discovery_dir / "web.json").write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n")
    (discovery_dir / "ranked_sources.json").write_text(json.dumps(ranked, indent=2, ensure_ascii=False) + "\n")
    completed_at = now_utc()
    state = {
        "schema_version": "1",
        "run_id": discovery_dir.parent.name,
        "stage": "stage_1_discovery",
        "status": "completed" if fixtures else "quarantined",
        "input_files": [_project_relative(REGISTRY_PATH)],
        "output_files": [
            _project_relative(discovery_dir / "web.json"),
            _project_relative(discovery_dir / "ranked_sources.json"),
        ],
        "started_at": completed_at,
        "completed_at": completed_at,
        "model_endpoints": [],
        "tool_manifest": "stage_1_web_discovery",
        "metrics": {"sources_processed": len(fixtures), "claims_emitted": 0, "provider_calls": 0},
        "error": None if fixtures else {
            "code": "no_verified_sources",
            "message": "no verified real public web fixtures discovered",
            "rejection_codes": ["no_verified_real_public_web_fixtures"],
        },
    }
    (discovery_dir / "state.json").write_text(json.dumps(state, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover real public web fixtures from practitioner registry seeds.")
    parser.add_argument("--markers", nargs="+", default=PILOT_MARKERS, help="Marker IDs to discover")
    parser.add_argument("--per-marker", type=int, default=1, help="Fixtures to save per marker")
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR, help="Directory for source fixture JSON files")
    parser.add_argument("--discovery-dir", type=Path, default=DEFAULT_DISCOVERY_DIR, help="Directory for Stage 1 discovery artifacts")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate but do not write fixture files")
    args = parser.parse_args(argv)

    started = now_utc()
    fixtures, log = discover_real_fixtures(args.markers, per_marker=args.per_marker)
    log.insert(0, {"event": "run_start", "started_at": started, "markers": args.markers, "per_marker": args.per_marker})
    log.append({"event": "run_complete", "completed_at": now_utc(), "fixtures": len(fixtures)})

    if not args.dry_run:
        paths = [write_fixture(fixture, args.fixture_dir) for fixture in fixtures]
        write_discovery_artifacts(fixtures, log, args.discovery_dir)
    else:
        paths = []
        write_discovery_artifacts(fixtures, log, args.discovery_dir)

    for fixture in fixtures:
        print(f"verified_real_source {fixture['expected_markers']} {fixture['source_url']} sha256={fixture['transcript_sha256']}")
    for path in paths:
        print(f"wrote {path}")

    missing = []
    for marker in args.markers:
        count = sum(1 for f in fixtures if marker in f.get("expected_markers", []))
        if count < args.per_marker:
            missing.append(marker)
    if missing:
        print(f"incomplete markers: {', '.join(missing)}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
