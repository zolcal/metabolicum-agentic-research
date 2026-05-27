#!/usr/bin/env python3
"""Manual fixture creator from a URL."""

import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
import trafilatura

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from code.discovery.web import load_registry, normalize_url

SCHEMA_PATH = PROJECT_ROOT / "code" / "schemas" / "source_fixture.schema.json"
FIXTURES_DIR = PROJECT_ROOT / "fixtures" / "sources"


def create_fixture(
    url: str,
    marker: str,
    source_type: str = "blog",
    speaker_or_author: str | None = None,
    speaker_registry_id: str | None = None,
    notes: str | None = None,
) -> dict:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "metabolicum-agentic-research/0.1 (+https://github.com/metabolicum; public-page citation research)",
        "Accept": "text/html,application/xhtml+xml",
    })
    
    print(f"Fetching {url}...")
    resp = session.get(url, timeout=25, allow_redirects=True)
    resp.raise_for_status()
    
    html = resp.text
    text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
    text = text.strip()
    
    if len(text) < 600:
        raise ValueError(f"Extracted text too short: {len(text)} chars")
    
    # Try to get title from HTML
    title = ""
    import re
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if m:
        title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
    if not title:
        title = text.split('\n')[0][:120]
    
    domain = urlparse(resp.url).netloc
    platform = domain.replace("www.", "")
    
    fixture = {
        "schema_version": "1",
        "source_id": str(uuid.uuid5(uuid.NAMESPACE_URL, normalize_url(resp.url))),
        "source_url": normalize_url(resp.url),
        "source_type": source_type,
        "platform": platform,
        "title": title,
        "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "published_at": None,
        "source_language": "en",
        "speaker_or_author": speaker_or_author,
        "speaker_registry_id": speaker_registry_id,
        "license": "all_rights_reserved_public_web_page",
        "transcript_method": "public_page_html_to_text",
        "transcript_text": text,
        "transcript_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "expected_markers": [marker],
        "notes": notes,
        "synthetic": False,
        "verification_status": "verified_real_source",
    }
    
    # Validate against schema
    schema = json.loads(SCHEMA_PATH.read_text())
    from jsonschema import Draft202012Validator
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(fixture), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
        raise ValueError(f"fixture schema validation failed: {detail}")
    
    return fixture


def save_fixture(fixture: dict) -> Path:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    marker = fixture["expected_markers"][0]
    platform = fixture["platform"].replace(".", "-")[:24]
    prefix = f"{marker}-{platform}"
    existing = sorted(FIXTURES_DIR.glob(f"{prefix}-*.json"))
    path = FIXTURES_DIR / f"{prefix}-{len(existing) + 1:02d}.json"
    path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--marker", required=True)
    parser.add_argument("--author")
    parser.add_argument("--registry-id")
    parser.add_argument("--notes")
    parser.add_argument("--source-type", default="blog")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    fixture = create_fixture(
        args.url,
        args.marker,
        source_type=args.source_type,
        speaker_or_author=args.author,
        speaker_registry_id=args.registry_id,
        notes=args.notes,
    )
    print(f"Created fixture: {fixture['title'][:60]}...")
    print(f"  Text length: {len(fixture['transcript_text'])} chars")
    print(f"  Markers: {fixture['expected_markers']}")
    
    if not args.dry_run:
        path = save_fixture(fixture)
        print(f"  Saved to: {path}")
