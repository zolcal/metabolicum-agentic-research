-- Per-marker MO-paradigm support determination (binary, overridable).
-- Written by the agentic pipeline (Hermes) — the source-of-truth record that a marker
-- was assessed for the Metabolic-Optimization paradigm. A pass-through for markers with
-- no MO dimension (no research run), but the record is still created here. Later research
-- can overwrite the row; updates are projected to the metasync DB.
CREATE TABLE IF NOT EXISTS marker_mo_determination (
    marker_slug   TEXT PRIMARY KEY,
    mo_supported  BOOLEAN NOT NULL,
    mo_rationale  TEXT,
    mo_decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
