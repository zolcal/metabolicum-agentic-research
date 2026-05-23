# Range Status Color Policy

> **Vendored copy.** Upstream source of truth: `metasync/docs/specs/RANGE-STATUS-COLOR-POLICY.md`.
> Vendored into `metabolicum-agentic-research/docs/policies/` so the Hermes agent runtime
> (constrained to this project boundary) can read the canonical alias table and palette.
> When the upstream version changes, re-vendor and bump the date/version line below.
> Last sync: 2026-05-23 (v1.0).

**Status:** v1.0 (Draft for review)
**Date:** 2026-05-23
**Scope:** Color of paradigm range tiers (`paradigm_ranges.color`, `range_facts.color`).
**Out of scope:** Marker-level accent color (`markers.color_primary`), brand colors, page-hero accents, evidence-grade colors.

## Why this exists

Three paradigms (SM, RC, MO) × hundreds of markers × multiple import pipelines (sm-clean-frozen, rc-pipeline wave-1, rc-legacy, mo-research) have produced a `paradigm_ranges` table with **the same status mapped to multiple colors**:

- SM `low` is stored as `#3b82f6`, `#f59e0b`, AND `#f97316` (878 rows split across three colors)
- RC `optimal` is stored as both `#22c55e` and `#10b981`
- RC `borderline` is stored as both `#facc15` and `#eab308`
- 37+ distinct status values appear in the DB; many have no canonical color mapping

The web renderer (`ParadigmBar`, `VerticalParadigmBars`) and the mobile renderer (`apps/mobile/src/components/paradigm/utils.ts`) **read the color stored on the row, not a fresh lookup**. So drift in the DB shows up directly in the UI. This policy ends that.

## Canonical palette

One palette, paradigm-agnostic, marker-agnostic. Six semantic buckets:

| Bucket | Hex | Tailwind | Semantic meaning |
|---|---|---|---|
| `optimal` | `#22c55e` | green-500 | Target / preferred / healthy |
| `near_optimal` | `#84cc16` | lime-500 | Close to optimal, no concern |
| `borderline` | `#eab308` | yellow-500 | Marginal; warrants attention |
| `elevated` | `#f97316` | orange-500 | Abnormal, action recommended |
| `critical` | `#ef4444` | red-500 | Significantly abnormal, urgent attention |
| `severe` | `#dc2626` | red-600 | Critical-extreme (rare; reserve for genuine emergency thresholds) |
| `indeterminate` | `#9ca3af` | gray-400 | Insufficient evidence, not applicable, or unmappable status (fallback only) |

These are the only colors that should appear in `paradigm_ranges.color` or `range_facts.color`. Any other hex is policy violation.

## Status alias table (the canonical mapping)

Every DB status string maps to exactly one bucket. This is the **authoritative table** — both the import helper and the renderer derive from it.

### → `optimal` (`#22c55e`)
`optimal`, `normal`, `good`, `healthy`, `sufficient`, `negative`, `ideal`, `adequate`, `target`, `optimal_high`, `optimal_low`

### → `near_optimal` (`#84cc16`)
`near-optimal`, `near_optimal`, `acceptable`, `low_normal`, `high_normal`, `above_optimal`, `below_optimal`

### → `borderline` (`#eab308`)
`borderline`, `borderline_high`, `borderline_low`, `borderline_elevated`, `moderate`, `attention`, `monitor`, `caution`, `verify`, `investigate`, `mildly_elevated`, `trace`, `supplement_possible`, `concerning`, `suboptimal`

### → `elevated` (`#f97316`)
`elevated`, `elevated_risk`, `high`, `high_risk`, `high-risk`, `above-optimal`, `low`, `low_risk`, `acute`, `trough`, `poor`

### → `critical` (`#ef4444`)
`very_high`, `very_low`, `deficient`, `abnormal`, `excessive`, `insufficient`

### → `severe` (`#dc2626`)
`critical`, `critical_high`, `critical_low`, `severe`

### → `indeterminate` (`#9ca3af`)
`indeterminate`, `not_applicable`, `not-applicable`, `N/A`, `insufficient_evidence`, `subtherapeutic`, `unknown`

### Bespoke / specialty statuses (must be mapped or rejected)

Mostly from MO pipelines. Pre-decided here so import doesn't break:

| Status | Maps to |
|---|---|
| `high_protein` | `indeterminate` (descriptive, not a tier) |
| `low_muscle` | `indeterminate` |
| `sarcopenia_concern` | `borderline` |
| `lmhr` | `optimal` (confirmed phenotype) |
| `near-lmhr` | `borderline` |
| `not-lmhr` | `indeterminate` |

New bespoke statuses must be added here before they're allowed into the DB. The import helper rejects unmapped statuses.

## Directionality clarification — the `low` ambiguity

For most markers, `low` is bad (low ferritin = anemia risk). For some calculators, `low` is good (low HOMA-IR = good metabolic health). The status string alone doesn't carry that meaning.

**Policy:** `low` always maps to `elevated` orange. Markers where the "low side" of normal is the target should use one of:

- `optimal_low` → `optimal` (green) — "low is good"
- `low_normal` → `near_optimal` (lime) — "borderline but acceptable"
- `near_optimal` → `near_optimal` (lime)

Pipelines that produce `low` for a "low is good" marker are emitting the wrong status. Fix the status, not the color.

## Normalization contract (import-time)

Every pipeline that writes to `paradigm_ranges` or `range_facts` MUST resolve `color` via the canonical helper:

```python
# scripts/lib/range_color_policy.py
STATUS_TO_BUCKET: dict[str, str] = { ... }    # the alias table above
BUCKET_TO_HEX: dict[str, str] = {
    "optimal":       "#22c55e",
    "near_optimal":  "#84cc16",
    "borderline":    "#eab308",
    "elevated":      "#f97316",
    "critical":      "#ef4444",
    "severe":        "#dc2626",
    "indeterminate": "#9ca3af",
}

def normalize_status(raw: str) -> str:
    """Lowercase, replace separators, return canonical key. No fuzzy matching."""
    return raw.strip().lower().replace(" ", "_").replace("-", "_")

def canonical_color(status: str) -> str:
    """Resolve a status to its canonical hex. Raises if unmapped."""
    key = normalize_status(status)
    if key not in STATUS_TO_BUCKET:
        raise UnmappedStatusError(f"Status {status!r} has no canonical color mapping. "
                                  f"Add to STATUS_TO_BUCKET or fix the status string.")
    return BUCKET_TO_HEX[STATUS_TO_BUCKET[key]]
```

A TypeScript twin lives in `apps/web/src/lib/ranges/color-policy.ts` (and re-exported from a shared package if/when one exists).

**Enforcement at import:** every ingester (`scripts/sm_import/*`, `scripts/rc_import/*`, future `scripts/mo_import/*`) calls `canonical_color(status)` and writes its return value. If the helper raises, the ingester fails loud — never falls back to a default in production. Acceptable to soft-fail with a warning in `--dry-run` mode.

**Enforcement at the DB (defense in depth):** add a `CHECK` constraint that `color IN (canonical 7 hex values)`. This catches any path that bypasses the helper.

```sql
ALTER TABLE paradigm_ranges
  ADD CONSTRAINT paradigm_ranges_canonical_color
  CHECK (color IN ('#22c55e','#84cc16','#eab308','#f97316','#ef4444','#dc2626','#9ca3af'));
ALTER TABLE range_facts
  ADD CONSTRAINT range_facts_canonical_color
  CHECK (color IS NULL OR color IN ('#22c55e','#84cc16','#eab308','#f97316','#ef4444','#dc2626','#9ca3af'));
```

Add the constraint AFTER the one-time cleanup pass below; otherwise existing drift blocks the constraint.

## Renderer contract

- `ParadigmBar`, `VerticalParadigmBars`, mobile `getStatusColor()` — read the stored color directly. **Do not** call `canonical_color()` again at render time. The DB row is the source of truth post-import.
- The `getStatusColor()` function in `apps/mobile/src/components/paradigm/utils.ts` is retained for legacy callers and the (rare) case of rendering a status with no stored color, but it MUST yield the same values as the canonical table above. Today it almost does; one cleanup item is to align it 1:1 with this policy.

## Marker-level color (separate concern)

`markers.color_primary` and `markers.color_secondary` are independent of range-tier color. They drive marker badges, hero accents, listing tiles. They use the brand palette + extended accents (see `docs/PAGE-TEMPLATES.md` Evaluator color table). This policy says nothing about them; they are governed by `docs/BRANDING.md`.

If/when we codify marker-level color assignment (e.g., per-category default + per-marker override), it lives in a separate spec.

## One-time cleanup of existing drift

Before adding the CHECK constraint:

```sql
-- Map current colors → canonical. Mirror the alias table.
UPDATE paradigm_ranges SET color = CASE
  WHEN color IN ('#10b981','#22c55e') THEN '#22c55e'           -- optimal greens
  WHEN color IN ('#facc15','#eab308') THEN '#eab308'           -- borderline yellows
  WHEN color IN ('#3b82f6','#f59e0b','#f97316') AND status IN ('low')
       THEN '#f97316'                                          -- SM low → elevated orange
  WHEN color = '#991b1b' THEN '#dc2626'                        -- darker red → severe red-600
  WHEN color = '#6b7280' THEN '#9ca3af'                        -- gray fallback alignment
  ELSE color
END
WHERE color IS NOT NULL;
```

Apply equivalent to `range_facts`. Spot-checked subjects: sodium, magnesium, homa-ir (wave-1) keep their visual intent; SM drift collapses to the canonical palette.

The full migration is generated automatically by the canonical helper running against the current DB state — see `scripts/lib/range_color_policy.py --emit-cleanup-sql`. (Helper TBD; trivial implementation.)

## Open questions

1. **`severe` vs `critical`** — keep both, or collapse `severe` into `critical`? Right now I've split: `critical` for thresholds like *very_high* / *deficient* (red-500), `severe` for actual emergency cutoffs like *critical_low* in serum sodium (red-600). Visually close; might not be worth two tiers. Recommend keeping for now and reviewing after MO research lands.
2. **`indeterminate` for `insufficient_evidence`** — current RC data has 704 rows with `status='insufficient_evidence'` and a gray color. This policy keeps that mapping. Confirm that's the right UX (a gray bar segment instead of no segment).
3. **MO bespoke statuses** — pipelines emitting `high_protein`, `low_muscle`, `sarcopenia_concern`, etc. are encoding clinical context, not severity tiers. Long-term these should move out of `status` into a separate column or a tag. For now mapped as listed.

## References

- `apps/mobile/src/components/paradigm/utils.ts` — current `getStatusColor()` (closest to a canonical implementation; updates from this policy land here first)
- `apps/web/src/lib/db/range-fallback.ts` — fallback `STATUS_COLORS` (subset of canonical)
- `apps/web/src/lib/paradigm-ranges-validated.ts` — historical hardcoded `COLORS` map (pre-DB era; useful reference)
- `docs/HANDOVER-SESSION-47-learn-page-template.md` — only doc that informally stated the rule
- `docs/BRANDING.md` — brand palette + marker accent colors (separate concern)
- `docs/PAGE-TEMPLATES.md` — evaluator accent colors (separate concern)
