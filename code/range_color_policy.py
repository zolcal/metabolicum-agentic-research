"""Status normalization + canonical color, per docs/policies/RANGE-STATUS-COLOR-POLICY.md.

Stage 6 assembly derives a range_fact `status` then resolves `color` via
canonical_color(status). The 7-hex palette matches the biomarker_claims.color
CHECK constraint in the migration. canonical_color raises UnmappedStatusError on
an unknown status so the assembly step can quarantine the claim (rejection_stage
'assembly') rather than crash.
"""

from __future__ import annotations


class UnmappedStatusError(ValueError):
    """Raised when a status string is not in the canonical alias table."""


BUCKET_TO_HEX: dict[str, str] = {
    "optimal": "#22c55e",
    "near_optimal": "#84cc16",
    "borderline": "#eab308",
    "elevated": "#f97316",
    "critical": "#ef4444",
    "severe": "#dc2626",
    "indeterminate": "#9ca3af",
}

# Alias table (canonical mapping). Keys are lowercased; hyphen/underscore
# variants are tolerated by normalize_status. Mirrors the policy doc exactly,
# including the quirks: `low` -> elevated, `critical` -> severe bucket,
# very_high/very_low/deficient -> critical bucket.
_ALIASES: dict[str, list[str]] = {
    "optimal": [
        "optimal", "normal", "good", "healthy", "sufficient", "negative", "ideal",
        "target", "optimal_high", "optimal_low", "lmhr",
    ],
    "near_optimal": [
        "near_optimal", "acceptable", "adequate", "low_normal", "high_normal", "below_optimal",
    ],
    "borderline": [
        "borderline", "borderline_high", "borderline_low", "borderline_elevated", "moderate",
        "attention", "monitor", "caution", "verify", "investigate", "mildly_elevated", "trace",
        "supplement_possible", "concerning", "suboptimal", "sarcopenia_concern", "near_lmhr",
    ],
    "elevated": [
        "elevated", "elevated_risk", "high", "above_optimal", "above_optimal_high", "low",
        "low_risk", "acute", "trough", "poor",
    ],
    "critical": [
        "very_high", "very_low", "deficient", "abnormal", "excessive", "insufficient", "high_risk",
    ],
    "severe": [
        "critical", "critical_high", "critical_low", "severe",
    ],
    "indeterminate": [
        "indeterminate", "not_applicable", "n/a", "insufficient_evidence", "subtherapeutic",
        "unknown", "high_protein", "low_muscle", "not_lmhr",
    ],
}

STATUS_TO_BUCKET: dict[str, str] = {
    alias: bucket for bucket, aliases in _ALIASES.items() for alias in aliases
}


def _key(raw: str) -> str:
    return (raw or "").strip().lower().replace("-", "_")


def normalize_status(raw: str) -> str:
    """Map a raw status string to its canonical bucket. Raises on unmapped."""
    k = _key(raw)
    if k in STATUS_TO_BUCKET:
        return STATUS_TO_BUCKET[k]
    # tolerate 'n/a' written without normalization of the slash
    if k.replace("_", "/") in STATUS_TO_BUCKET:
        return STATUS_TO_BUCKET[k.replace("_", "/")]
    raise UnmappedStatusError(f"unmapped status: {raw!r}")


def canonical_color(status: str) -> str:
    """Return the canonical hex for a status (accepts aliases or buckets)."""
    return BUCKET_TO_HEX[normalize_status(status)]
