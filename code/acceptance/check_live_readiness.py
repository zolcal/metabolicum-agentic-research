#!/usr/bin/env python3
"""Live-run readiness preflight (read-only, $0).

Reports what must be up before a live single-marker/wave run: local LLM server,
cloud keys (presence only — never values), PubMed/Crossref reachability, Supabase
creds, and the vendor/run-hermes path. Prints a verdict; exit 0 always (diagnostic).
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

# secrets/.env is gitignored (absent in worktrees) — search known locations.
_SECRET_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "secrets" / ".env",
    Path("/media/zoltan/4TSSD/metabolicum-agentic-research/secrets/.env"),
    Path("/home/zoltan/Projects/metabolicum-agentic-research/secrets/.env"),
]


def _env_keys() -> tuple[set[str], str]:
    for p in _SECRET_CANDIDATES:
        if p.is_file():
            present = set()
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if v.strip():
                        present.add(k.strip())
            return present, str(p)
    return set(), "(none found)"


def _http_ok(url: str, timeout: float = 4.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def main() -> None:
    keys, src = _env_keys()
    checks = []

    def add(name, ok, detail=""):
        checks.append((name, ok, detail))

    # Local Stage-2 LLM
    add("llama-server :8080 (Stage-2 extractor)", _http_ok("http://127.0.0.1:8080/v1/models", 3.0),
        "local GPU; cloud fallback = deepseek-direct-chat if down")
    # Cloud keys for the council + legal
    add("OPENROUTER_API_KEY (council reviewer+decider)", "OPENROUTER_API_KEY" in keys)
    add("DASHSCOPE_API_KEY (Stage-2 fallback / legal)", "DASHSCOPE_API_KEY" in keys)
    add("GOOGLE/GEMINI key (embeddings)", bool({"GOOGLE_API_KEY", "GOOGLE_AI_API_KEY"} & keys),
        "GOOGLE_AI_API_KEY vs GOOGLE_API_KEY name mismatch flagged in earlier review")
    # Provenance (keyless works, rate-limited)
    add("NCBI E-utilities reachable", _http_ok(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?retmode=json", 5.0),
        f"NCBI_API_KEY {'present' if 'NCBI_API_KEY' in keys else 'absent (keyless rate-limited)'}")
    add("Crossref reachable", _http_ok("https://api.crossref.org/works/10.1001/jama.2020.0", 5.0))
    # Persistence
    add("SUPABASE creds present", {"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"} <= keys)
    # Vendor / runner path
    root = Path("/media/zoltan/4TSSD/metabolicum-agentic-research")
    vendors = sorted(p.name for p in (root / "vendor").glob("hermes-agent-*")) if (root / "vendor").is_dir() else []
    add("Hermes vendor present", bool(vendors), f"vendors={vendors}; run-hermes references v2026.5.16")

    print(f"=== Live readiness (keys from {src}) ===")
    for name, ok, detail in checks:
        mark = "✅" if ok else "❌"
        print(f"  {mark} {name}" + (f"  — {detail}" if detail else ""))

    blockers = [n for n, ok, _ in checks if not ok and ("OPENROUTER" in n or ":8080" in n or "SUPABASE" in n)]
    print("\nVERDICT:", "READY for a live run (or local-down -> cloud fallback)" if not blockers
          else f"NOT ready — resolve: {blockers}")
    print(json.dumps({"checks": {n: ok for n, ok, _ in checks}, "blockers": blockers}, indent=2))


if __name__ == "__main__":
    main()
