# HANDOVER-SESSION-9

## Date
2026-05-29

## Summary
Aligned the Hermes run-state and brief-generation code with the 2026-05-29 brief-driven realignment note.

## Completed
- Audited `input/hermes-briefs/`: 982 YAML briefs checked, 0 `_meta` blocks found.
- Fixed `code/state.py` so `state.json` includes `schema_version: "1"`.
- Moved `research_target_envelopes.sanitized.json` from `discovery/` to the run root via `PipelineRun.write_sanitized_envelopes()`.
- Added `PipelineRun.write_claim_envelope_evaluations()` for `council/claim_envelope_evaluations.jsonl`.
- Fixed `code/discovery/web.py` so its direct state writer also includes `schema_version: "1"`.
- Updated `code/schemas/state.schema.json` so `schema_version` is required.
- Removed `_meta` emission from legacy `scripts/prepare_hermes_briefs.py`.
- Updated `code/acceptance/check_hermes_briefs.py` so `_meta` is explicitly rejected.

## Verification
- `env TMPDIR=/home/zoltan/Projects/metabolicum-agentic-research/.pytest-tmp python3 -m pytest -p no:cacheprovider tests/test_state_layout_alignment.py tests/test_hermes_asset_pipeline.py -q` passed: 6 tests.
- `python3 code/acceptance/check_hermes_briefs.py --qualification` passed: 10/10.
- `python3 code/acceptance/check_hermes_briefs.py --wave wave-0` passed: 5/5.
- `python3 code/acceptance/check_hermes_briefs.py --wave wave-1` passed: 105/105.
- `python3 code/acceptance/check_hermes_briefs.py --wave wave-2` passed: 108/108.
- `python3 code/acceptance/check_hermes_briefs.py --wave wave-2b` passed: 90/90.
- `python3 code/acceptance/check_hermes_briefs.py --wave wave-3` passed: 674/674.

## Next Steps
- When implementing the trigger/orchestrator, enforce the SM firewall structurally: pointer-only inputs for discovery/extraction, SM rows only for the Stage-3 council.
- Do not depend on `_meta` in brief files; diagnostics belong in sidecars.

## Files Changed
- `code/state.py`
- `code/discovery/web.py`
- `code/schemas/state.schema.json`
- `code/acceptance/check_hermes_briefs.py`
- `scripts/prepare_hermes_briefs.py`
- `tests/test_state_layout_alignment.py`
- `tests/test_hermes_asset_pipeline.py`
- `HANDOVER-SESSION-9.md`
