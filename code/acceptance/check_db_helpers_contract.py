#!/usr/bin/env python3
"""DB-free contract check for the Stage 3-6 db.py helpers + the ingest quarantine fix.

No database is touched. A FakeClient records the row dicts each helper would
persist; we assert every row is a strict subset of its table's columns in
supabase/migrations/0001_initial.sql (the persistence authority), uses only
valid CHECK-enum values, that claim_envelope_evaluations carries NO 'id'
(composite PK), and that the ingest failure-quarantine row uses
rejection_stage='extractor' with no 'payload' key (the old bug at ingest.py).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = PROJECT_ROOT / "supabase" / "migrations" / "0001_initial.sql"
sys.path.insert(0, str(PROJECT_ROOT))


def _table_block(table: str) -> str:
    text = MIGRATION.read_text(encoding="utf-8")
    m = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", text, re.DOTALL)
    if not m:
        raise AssertionError(f"table {table!r} not found in migration")
    return m.group(1)


def table_columns(table: str) -> set[str]:
    cols: set[str] = set()
    for line in _table_block(table).splitlines():
        line = line.strip()
        if not line or line.startswith(
            ("CHECK", "PRIMARY KEY", "FOREIGN KEY", "CONSTRAINT", "UNIQUE")
        ):
            continue
        token = line.split()[0]
        if token.isidentifier():
            cols.add(token)
    return cols


def enum_values(table: str, column: str) -> set[str]:
    block = _table_block(table)
    m = re.search(rf"{column}\s+IN\s*\((.*?)\)", block, re.DOTALL)
    if not m:
        raise AssertionError(f"no CHECK..IN enum for {table}.{column}")
    return set(re.findall(r"'([^']+)'", m.group(1)))


# ── FakeClient: records rows without touching a DB ───────────────────
class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, recorder: list, table: str):
        self._rec = recorder
        self._table = table
        self._op: str | None = None
        self._payload = None
        self._filters: dict = {}
        self._on_conflict = None

    def insert(self, data):
        self._op, self._payload = "insert", data
        return self

    def upsert(self, data, on_conflict=None):
        self._op, self._payload, self._on_conflict = "upsert", data, on_conflict
        return self

    def update(self, data):
        self._op, self._payload = "update", data
        return self

    def select(self, *a, **k):
        self._op = "select"
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def limit(self, n):
        return self

    def execute(self):
        if self._op in ("insert", "upsert", "update"):
            self._rec.append(
                {"table": self._table, "op": self._op, "row": self._payload,
                 "filters": self._filters, "on_conflict": self._on_conflict}
            )
        data = [self._payload] if isinstance(self._payload, dict) else (self._payload or [])
        return _FakeResult(data)


class FakeClient:
    def __init__(self):
        self.calls: list[dict] = []

    def table(self, name):
        return _FakeQuery(self.calls, name)


def assert_subset(table: str, row: dict, *, allow_id: bool = True) -> None:
    cols = table_columns(table)
    keys = set(row.keys())
    if not allow_id:
        assert "id" not in keys, f"{table}: row must NOT carry an 'id' (composite PK)"
    extra = keys - cols
    assert not extra, f"{table}: row has columns not in migration: {sorted(extra)}"


def main() -> None:
    from code import db
    from code.pipeline import ingest

    fake = FakeClient()
    c = db.DBClient(fake, label="fake")

    # 1) insert_provenance
    c.insert_provenance({
        "biomarker_claim_id": "bc-1", "edge_type": "paper_to_pmid",
        "source_locator": "surface:x", "target_locator": "pmid:123",
        "research_study_id": "rs-1", "confidence": 0.9,
        "resolution_status": "resolved", "resolver_agent": "provenance",
    })
    prov = fake.calls[-1]["row"]
    assert_subset("provenance", prov)
    assert prov["resolution_status"] in enum_values("provenance", "resolution_status")
    assert prov["edge_type"] in enum_values("provenance", "edge_type")

    # 2) insert_legal_review
    c.insert_legal_review({
        "biomarker_claim_id": "bc-1", "decision": "approve",
        "rationale": "short attributed quote", "applicable_rules": ["quote_length"],
        "quote_length_check": True, "license_check": True, "tos_check": True,
        "feist_compilation_risk": "low", "eu_database_flag": False,
        "reviewer_model": "dashscope-qwen-max",
    })
    legal = fake.calls[-1]["row"]
    assert_subset("legal_reviews", legal)
    assert legal["decision"] in enum_values("legal_reviews", "decision")
    assert legal["feist_compilation_risk"] in enum_values("legal_reviews", "feist_compilation_risk")

    # 3) insert_claim_envelope_evaluation — composite PK, NO id
    c.insert_claim_envelope_evaluation({
        "biomarker_claim_id": "bc-1", "envelope_id": "env-1",
        "alignment_status": "aligned", "evaluator_model": "council",
    })
    cee = fake.calls[-1]["row"]
    assert_subset("claim_envelope_evaluations", cee, allow_id=False)
    assert cee["alignment_status"] in enum_values("claim_envelope_evaluations", "alignment_status")

    # 4) update_biomarker_claim_status — update by id
    c.update_biomarker_claim_status(
        "bc-1", provenance_status="resolved", legal_status="approved", approval_status="approved"
    )
    upd = fake.calls[-1]
    assert upd["table"] == "biomarker_claims" and upd["op"] == "update", "must UPDATE biomarker_claims"
    assert upd["filters"].get("id") == "bc-1", "must filter by id"
    assert_subset("biomarker_claims", upd["row"])

    # 5) get_source_by_id — read path; must resolve without raising
    c.get_source_by_id("src-1")

    # 6) ingest failure-quarantine row — the bug fix (no 'payload', rejection_stage='extractor')
    q = ingest.build_ingest_failure_quarantine_row(
        source_id="src-1", source_url="https://example.test/x", error="boom"
    )
    assert "payload" not in q, "quarantine row must not carry a 'payload' column (old bug)"
    assert q.get("rejection_stage") == "extractor", \
        f"expected rejection_stage='extractor', got {q.get('rejection_stage')!r}"
    assert q["rejection_stage"] in enum_values("quarantine", "rejection_stage")
    assert_subset("quarantine", q)

    print("check_db_helpers_contract: all assertions passed")
    print(f"  recorded {len(fake.calls)} DB write calls; ingest quarantine row conforms")


if __name__ == "__main__":
    main()
