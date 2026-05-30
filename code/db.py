"""Supabase client layer for metabolicum-agentic-research.

Handles the local `supabase/` config directory that shadows the supabase-py
package when running from project root. Provides typed helpers for core tables.

Usage:
    from code.db import get_client, get_local_client

    # Remote (cloud) Supabase — durable persistence
    client = get_client()
    client.upsert_sources([{"url": "...", ...}])

    # Local Supabase — dev + acceptance tests
    local = get_local_client()
    local.query_sources(marker="apob")
"""

from __future__ import annotations

import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


# ── Import fix: local supabase/ dir shadows supabase-py ──────────────
# The project has a `supabase/` directory (CLI config) that Python treats
# as a namespace package, blocking the real `supabase` pip package.
# We temporarily remove CWD-like paths from sys.path before importing.

def _import_supabase():
    """Import the real supabase package, bypassing local dir shadowing."""
    # Save and clean sys.path
    original = sys.path[:]
    project_root = str(Path(__file__).resolve().parent.parent)
    sys.path = [p for p in sys.path if not (
        p == '' or
        p == '.' or
        os.path.abspath(p) == project_root or
        os.path.abspath(p) == os.path.join(project_root, 'supabase')
    )]
    try:
        # Remove any cached shadow module
        for key in list(sys.modules.keys()):
            if key == 'supabase' or key.startswith('supabase.'):
                if hasattr(sys.modules[key], '__path__'):
                    mod_path = getattr(sys.modules[key], '__path__', None)
                    if mod_path and any('metabolicum' in str(p) for p in mod_path):
                        del sys.modules[key]
        mod = importlib.import_module('supabase')
        return mod
    finally:
        sys.path = original


_supabase_mod = _import_supabase()
create_client = _supabase_mod.create_client


# ── Environment loading ──────────────────────────────────────────────

def _load_env() -> dict[str, str]:
    """Load secrets/.env into a dict (does NOT pollute os.environ)."""
    env_file = Path(__file__).resolve().parent.parent / "secrets" / ".env"
    result: dict[str, str] = {}
    if not env_file.is_file():
        return result
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            if v:  # skip empty values
                result[k.strip()] = v.strip()
    return result


_env = _load_env()


def _get_env(key: str, fallback: str | None = None) -> str:
    """Get from loaded env, then os.environ, then fallback."""
    return _env.get(key) or os.environ.get(key) or fallback or ""


# ── Client singletons ────────────────────────────────────────────────

_remote_client = None
_local_client = None


def get_client():
    """Get or create the remote Supabase client (cloud project)."""
    global _remote_client
    if _remote_client is None:
        url = _get_env("SUPABASE_URL")
        key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set "
                "in secrets/.env or environment"
            )
        _remote_client = create_client(url, key)
    return _remote_client


def get_local_client():
    """Get or create the local Supabase client (dev DB on port 54421).

    Note: Local Supabase REST API requires project-specific JWT keys.
    If the REST connection fails, falls back to psycopg2 direct DB access.
    """
    global _local_client
    if _local_client is None:
        url = "http://127.0.0.1:54421"
        # Try the remote anon key first (works if local uses same JWT secret)
        key = _get_env("SUPABASE_ANON_KEY")
        if key:
            try:
                client = create_client(url, key)
                # Test connectivity
                client.table("sources").select("id").limit(0).execute()
                _local_client = client
                return _local_client
            except Exception:
                pass
        # Fallback: well-known Supabase demo anon key
        demo_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilFCblKiNlV8"
        _local_client = create_client(url, demo_key)
    return _local_client


# ── DBClient wrapper with typed helpers ──────────────────────────────

class DBClient:
    """Typed helper wrapper around a Supabase client.

    Provides table-specific methods with input validation and
    consistent error handling. Works with both local and remote clients.
    """

    def __init__(self, client, *, label: str = "remote"):
        self._client = client
        self.label = label

    @property
    def raw(self):
        """Access the underlying supabase client directly."""
        return self._client

    # ── Sources ──────────────────────────────────────────────────

    def upsert_source(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a source row. Keyed by URL (UNIQUE constraint)."""
        if "id" not in data:
            data["id"] = str(uuid4())
        if "fetched_at" not in data:
            data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        result = self._client.table("sources").upsert(data, on_conflict="url").execute()
        return result.data[0] if result.data else {}

    def source_exists(self, url: str) -> bool:
        """Check if a source with this URL already exists."""
        result = self._client.table("sources").select("id").eq("url", url).limit(1).execute()
        return len(result.data) > 0

    def get_source_by_url(self, url: str) -> dict[str, Any] | None:
        """Fetch a source row by URL."""
        result = self._client.table("sources").select("*").eq("url", url).limit(1).execute()
        return result.data[0] if result.data else None

    def query_sources(self, *, platform: str | None = None, limit: int = 100) -> list[dict]:
        """Query sources with optional platform filter."""
        q = self._client.table("sources").select("*")
        if platform:
            q = q.eq("platform", platform)
        return q.limit(limit).execute().data

    # ── Claims ───────────────────────────────────────────────────

    def insert_claim(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a pre-council extracted claim."""
        if "id" not in data:
            data["id"] = str(uuid4())
        if "extracted_at" not in data:
            data["extracted_at"] = datetime.now(timezone.utc).isoformat()
        result = self._client.table("claims").insert(data).execute()
        return result.data[0] if result.data else {}

    def query_claims(self, *, source_id: str | None = None, limit: int = 100) -> list[dict]:
        """Query pre-council claims."""
        q = self._client.table("claims").select("*")
        if source_id:
            q = q.eq("source_id", source_id)
        return q.limit(limit).execute().data

    # ── Source-Claim-Marker links ────────────────────────────────

    def upsert_claim_markers(self, claim_id: str, markers: list[dict]) -> list[dict]:
        """Insert marker links for a claim. Each dict: {marker, confidence}."""
        rows = []
        for m in markers:
            rows.append({
                "claim_id": claim_id,
                "marker": m["marker"],
                "confidence": m.get("confidence"),
            })
        if not rows:
            return []
        result = self._client.table("source_claim_marker").upsert(
            rows, on_conflict="claim_id,marker"
        ).execute()
        return result.data

    def query_claims_by_marker(self, marker: str, limit: int = 200) -> list[dict]:
        """Query all claims tagged with a specific marker (via link table)."""
        # Two-step: get claim_ids from link table, then fetch claims
        link_result = (
            self._client.table("source_claim_marker")
            .select("claim_id")
            .eq("marker", marker)
            .limit(limit)
            .execute()
        )
        claim_ids = [r["claim_id"] for r in link_result.data]
        if not claim_ids:
            return []
        # Fetch claims in batches (PostgREST 'in' filter)
        result = (
            self._client.table("claims")
            .select("*")
            .in_("id", claim_ids)
            .execute()
        )
        return result.data

    # ── BiomarkerClaims (post-council) ──────────────────────────

    def insert_biomarker_claim(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert an approved biomarker claim (post-council)."""
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        result = self._client.table("biomarker_claims").insert(data).execute()
        return result.data[0] if result.data else {}

    def query_biomarker_claims(
        self,
        *,
        marker: str | None = None,
        paradigm: str | None = None,
        approval_status: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """Query post-council biomarker claims with filters."""
        q = self._client.table("biomarker_claims").select("*")
        if marker:
            q = q.eq("marker", marker)
        if paradigm:
            q = q.eq("paradigm", paradigm)
        if approval_status:
            q = q.eq("approval_status", approval_status)
        return q.limit(limit).execute().data

    # ── SM Anchors ───────────────────────────────────────────────

    def upsert_sm_anchor(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update an SM anchor row."""
        if "id" not in data:
            data["id"] = str(uuid4())
        if "curated_at" not in data:
            data["curated_at"] = datetime.now(timezone.utc).isoformat()
        result = self._client.table("sm_anchors").insert(data).execute()
        return result.data[0] if result.data else {}

    def query_sm_anchors(self, marker: str | None = None, limit: int = 100) -> list[dict]:
        """Query SM anchors, optionally filtered by marker."""
        q = self._client.table("sm_anchors").select("*")
        if marker:
            q = q.eq("marker", marker)
        return q.limit(limit).execute().data

    # ── Marker Glossary ──────────────────────────────────────────

    def upsert_glossary_entries(self, entries: list[dict]) -> list[dict]:
        """Bulk upsert marker glossary entries. Keyed by (marker, language, term)."""
        if not entries:
            return []
        result = self._client.table("marker_glossary").upsert(
            entries, on_conflict="marker,language,term"
        ).execute()
        return result.data

    def query_glossary(self, marker: str | None = None, language: str = "en") -> list[dict]:
        """Query glossary entries for a marker."""
        q = self._client.table("marker_glossary").select("*").eq("language", language)
        if marker:
            q = q.eq("marker", marker)
        return q.limit(500).execute().data

    def lookup_marker(self, term: str, language: str = "en") -> str | None:
        """Look up a marker slug by term (exact match). Returns marker or None."""
        result = (
            self._client.table("marker_glossary")
            .select("marker")
            .eq("language", language)
            .eq("term", term)
            .limit(1)
            .execute()
        )
        return result.data[0]["marker"] if result.data else None

    # ── Practitioners ────────────────────────────────────────────

    def upsert_practitioner(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a practitioner."""
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        result = self._client.table("practitioners").upsert(
            data, on_conflict="id"
        ).execute()
        return result.data[0] if result.data else {}

    def upsert_practitioner_surface(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a practitioner surface."""
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        result = self._client.table("practitioner_surfaces").upsert(
            data, on_conflict="practitioner_id,platform,handle_or_url"
        ).execute()
        return result.data[0] if result.data else {}

    def upsert_commercial_interest(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a practitioner commercial interest."""
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        result = self._client.table("practitioner_commercial_interests").insert(
            data
        ).execute()
        return result.data[0] if result.data else {}

    def check_financial_conflict(
        self, practitioner_id: str | None, marker: str
    ) -> tuple[bool, str]:
        """Check if a practitioner has a financial conflict with a marker.

        Returns (has_conflict, highest_severity).
        Severity order: generic < marker_specific < direct_competitor < undisclosed.
        """
        if not practitioner_id:
            return False, "generic"

        result = (
            self._client.table("practitioner_commercial_interests")
            .select("severity, related_markers")
            .eq("practitioner_id", practitioner_id)
            .execute()
        )

        severity_rank = {
            "generic": 0,
            "marker_specific": 1,
            "direct_competitor": 2,
            "undisclosed": 3,
        }
        has_conflict = False
        highest = "generic"

        for row in result.data:
            related = row.get("related_markers") or []
            if marker in related:
                has_conflict = True
                sev = row.get("severity", "generic")
                if severity_rank.get(sev, 0) > severity_rank.get(highest, 0):
                    highest = sev

        return has_conflict, highest

    # ── Research Target Envelopes ────────────────────────────────

    def insert_envelope(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a research target envelope fact."""
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        result = self._client.table("research_target_envelopes").insert(data).execute()
        return result.data[0] if result.data else {}

    def query_envelopes(
        self, marker: str, paradigm: str | None = None, readiness: str = "ready"
    ) -> list[dict]:
        """Query envelope facts for a marker."""
        q = (
            self._client.table("research_target_envelopes")
            .select("*")
            .eq("marker", marker)
            .eq("readiness_state", readiness)
        )
        if paradigm:
            q = q.eq("paradigm", paradigm)
        return q.limit(100).execute().data

    # ── Quarantine ───────────────────────────────────────────────

    def insert_quarantine(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a quarantine record."""
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("quarantined_at", now)
        data.setdefault("updated_at", now)
        result = self._client.table("quarantine").insert(data).execute()
        return result.data[0] if result.data else {}

    # ── Research Studies ─────────────────────────────────────────

    def upsert_research_study(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert or update a research study. Deduped by PMID or DOI."""
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        # Try PMID dedup first, then DOI
        conflict_key = None
        if data.get("pmid"):
            conflict_key = "pmid"
        elif data.get("doi"):
            conflict_key = "doi"
        if conflict_key:
            result = self._client.table("research_studies").upsert(
                data, on_conflict=conflict_key
            ).execute()
        else:
            result = self._client.table("research_studies").insert(data).execute()
        return result.data[0] if result.data else {}

    # ── MO determination ─────────────────────────────────────────

    def upsert_mo_determination(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist a marker's binary MO-support determination (overridable on re-research).

        The Hermes pipeline creates this record on every run — researched markers and
        not_supported pass-throughs alike. Keyed by marker_slug.
        """
        result = self._client.table("marker_mo_determination").upsert(
            data, on_conflict="marker_slug"
        ).execute()
        return result.data[0] if result.data else {}

    # ── Stage 3-6 additions (provenance / legal / council eval) ──

    def insert_provenance(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a Stage 4 provenance edge (surface→paper→PMID/DOI resolution)."""
        if "id" not in data:
            data["id"] = str(uuid4())
        result = self._client.table("provenance").insert(data).execute()
        return result.data[0] if result.data else {}

    def insert_legal_review(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a Stage 5 legal/IP review record."""
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("reviewed_at", now)
        data.setdefault("updated_at", now)
        result = self._client.table("legal_reviews").insert(data).execute()
        return result.data[0] if result.data else {}

    def insert_claim_envelope_evaluation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a Stage 3 council claim↔envelope alignment evaluation.

        The table uses a composite PK (biomarker_claim_id, envelope_id) and has
        no synthetic id column — never inject a uuid here.
        """
        data.setdefault("evaluated_at", datetime.now(timezone.utc).isoformat())
        result = self._client.table("claim_envelope_evaluations").upsert(
            data, on_conflict="biomarker_claim_id,envelope_id"
        ).execute()
        return result.data[0] if result.data else {}

    def update_biomarker_claim_status(
        self, biomarker_claim_id: str, **fields: Any
    ) -> dict[str, Any]:
        """Update lifecycle/status fields on a biomarker_claims row by id.

        Used by Stage 4/5/6 to set provenance_status, legal_status,
        approval_status, exported_at. Always stamps updated_at.
        """
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = (
            self._client.table("biomarker_claims")
            .update(fields)
            .eq("id", biomarker_claim_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_source_by_id(self, source_id: str) -> dict[str, Any] | None:
        """Fetch a source row by id (assembly/provenance need source metadata)."""
        result = (
            self._client.table("sources").select("*").eq("id", source_id).limit(1).execute()
        )
        return result.data[0] if result.data else None

    # ── Generic helpers ──────────────────────────────────────────

    def table_count(self, table: str) -> int:
        """Return row count for a table."""
        # Some tables have no 'id' column (marker_glossary uses composite PK).
        # Use '*' and count='exact' which works regardless of columns.
        result = self._client.table(table).select("*", count="exact").limit(0).execute()
        return result.count or 0

    def health_check(self) -> dict[str, int]:
        """Check connectivity and return table counts for core tables."""
        counts = {}
        for table in [
            "sources", "claims", "biomarker_claims", "sm_anchors",
            "practitioners", "marker_glossary", "research_target_envelopes",
            "quarantine", "research_studies",
        ]:
            try:
                counts[table] = self.table_count(table)
            except Exception as e:
                counts[table] = -1  # error sentinel
        return counts


# ── Convenience constructors ─────────────────────────────────────────

def remote() -> DBClient:
    """Get a DBClient wrapping the remote Supabase project."""
    return DBClient(get_client(), label="remote")


def local() -> DBClient:
    """Get a DBClient wrapping the local Supabase dev DB."""
    return DBClient(get_local_client(), label="local")


# ── CLI smoke test ───────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Remote Supabase ===")
    try:
        r = remote()
        counts = r.health_check()
        for table, count in counts.items():
            status = f"{count} rows" if count >= 0 else "ERROR"
            print(f"  {table}: {status}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()
    print("=== Local Supabase ===")
    try:
        l = local()
        counts = l.health_check()
        for table, count in counts.items():
            status = f"{count} rows" if count >= 0 else "ERROR"
            print(f"  {table}: {status}")
    except Exception as e:
        print(f"  ERROR: {e}")


# ── psycopg2 local client (fallback when REST API JWT mismatch) ──────

class LocalDBClient:
    """psycopg2-based client for the local Supabase dev DB.

    Used when the local Supabase REST API has JWT key mismatch
    (common when supabase CLI is not installed to retrieve project keys).
    Provides the same interface as DBClient for core operations.
    """

    def __init__(self, db_url: str | None = None):
        import psycopg2
        import psycopg2.extras
        if db_url is None:
            db_url = _get_env("SUPABASE_DB_URL")
        if not db_url:
            raise RuntimeError("SUPABASE_DB_URL must be set in secrets/.env")
        self._conn = psycopg2.connect(db_url)
        self._conn.autocommit = True
        self.label = "local-psycopg"

    def _execute(self, sql: str, params: tuple = ()) -> list[dict]:
        import psycopg2.extras
        with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description:
                return [dict(row) for row in cur.fetchall()]
            return []

    def close(self):
        self._conn.close()

    # ── Sources ──────────────────────────────────────────────────

    def upsert_source(self, data: dict[str, Any]) -> dict[str, Any]:
        if "id" not in data:
            data["id"] = str(uuid4())
        if "fetched_at" not in data:
            data["fetched_at"] = datetime.now(timezone.utc).isoformat()
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in data if k != "id")
        sql = f"""
            INSERT INTO sources ({cols}) VALUES ({vals})
            ON CONFLICT (url) DO UPDATE SET {updates}
            RETURNING *
        """
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    def source_exists(self, url: str) -> bool:
        rows = self._execute(
            "SELECT id FROM sources WHERE url = %s LIMIT 1", (url,)
        )
        return len(rows) > 0

    # ── MO determination ─────────────────────────────────────────

    def upsert_mo_determination(self, data: dict[str, Any]) -> dict[str, Any]:
        """Persist a marker's binary MO-support determination (overridable on re-research)."""
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in data if k != "marker_slug")
        sql = f"""
            INSERT INTO marker_mo_determination ({cols}) VALUES ({vals})
            ON CONFLICT (marker_slug) DO UPDATE SET {updates}
            RETURNING *
        """
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    # ── Claims ───────────────────────────────────────────────────

    def insert_claim(self, data: dict[str, Any]) -> dict[str, Any]:
        import json as _json
        if "id" not in data:
            data["id"] = str(uuid4())
        if "extracted_at" not in data:
            data["extracted_at"] = datetime.now(timezone.utc).isoformat()
        # Serialize JSON fields
        for key in ("population", "cited_paper"):
            if key in data and isinstance(data[key], (dict, list)):
                data[key] = _json.dumps(data[key])
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO claims ({cols}) VALUES ({vals}) RETURNING *"
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    # ── Source-Claim-Marker links ────────────────────────────────

    def upsert_claim_markers(self, claim_id: str, markers: list[dict]) -> list[dict]:
        results = []
        for m in markers:
            rows = self._execute(
                """INSERT INTO source_claim_marker (claim_id, marker, confidence)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (claim_id, marker) DO UPDATE SET confidence = EXCLUDED.confidence
                   RETURNING *""",
                (claim_id, m["marker"], m.get("confidence")),
            )
            if rows:
                results.append(rows[0])
        return results

    # ── SM Anchors ───────────────────────────────────────────────

    def upsert_sm_anchor(self, data: dict[str, Any]) -> dict[str, Any]:
        import json as _json
        if "id" not in data:
            data["id"] = str(uuid4())
        if "curated_at" not in data:
            data["curated_at"] = datetime.now(timezone.utc).isoformat()
        if "population" in data and isinstance(data["population"], dict):
            data["population"] = _json.dumps(data["population"])
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO sm_anchors ({cols}) VALUES ({vals}) RETURNING *"
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    # ── Marker Glossary ──────────────────────────────────────────

    def upsert_glossary_entries(self, entries: list[dict]) -> list[dict]:
        results = []
        for e in entries:
            rows = self._execute(
                """INSERT INTO marker_glossary (marker, language, term, term_type)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (marker, language, term) DO UPDATE SET term_type = EXCLUDED.term_type
                   RETURNING *""",
                (e["marker"], e["language"], e["term"], e.get("term_type", "alias")),
            )
            if rows:
                results.append(rows[0])
        return results

    # ── Practitioners ────────────────────────────────────────────

    def upsert_practitioner(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        updates = ", ".join(f"{k} = EXCLUDED.{k}" for k in data if k != "id")
        sql = f"""
            INSERT INTO practitioners ({cols}) VALUES ({vals})
            ON CONFLICT (id) DO UPDATE SET {updates}
            RETURNING *
        """
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    def upsert_practitioner_surface(self, data: dict[str, Any]) -> dict[str, Any]:
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        sql = f"""
            INSERT INTO practitioner_surfaces ({cols}) VALUES ({vals})
            ON CONFLICT (practitioner_id, platform, handle_or_url)
            DO UPDATE SET {", ".join(f"{k} = EXCLUDED.{k}" for k in data if k not in ("id", "practitioner_id", "platform", "handle_or_url"))}
            RETURNING *
        """
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    def upsert_commercial_interest(self, data: dict[str, Any]) -> dict[str, Any]:
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO practitioner_commercial_interests ({cols}) VALUES ({vals}) RETURNING *"
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    # ── Research Target Envelopes ────────────────────────────────

    def insert_envelope(self, data: dict[str, Any]) -> dict[str, Any]:
        import json as _json
        if "id" not in data:
            data["id"] = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data.setdefault("created_at", now)
        data.setdefault("updated_at", now)
        if "population" in data and isinstance(data["population"], dict):
            data["population"] = _json.dumps(data["population"])
        cols = ", ".join(data.keys())
        vals = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO research_target_envelopes ({cols}) VALUES ({vals}) RETURNING *"
        rows = self._execute(sql, tuple(data.values()))
        return rows[0] if rows else {}

    # ── Generic helpers ──────────────────────────────────────────

    def table_count(self, table: str) -> int:
        rows = self._execute(f"SELECT COUNT(*) AS cnt FROM {table}")
        return rows[0]["cnt"] if rows else 0

    def health_check(self) -> dict[str, int]:
        counts = {}
        for table in [
            "sources", "claims", "biomarker_claims", "sm_anchors",
            "practitioners", "marker_glossary", "research_target_envelopes",
            "quarantine", "research_studies",
        ]:
            try:
                counts[table] = self.table_count(table)
            except Exception:
                counts[table] = -1
        return counts


def local_psycopg() -> LocalDBClient:
    """Get a psycopg2-based local DB client."""
    return LocalDBClient()

