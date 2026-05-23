# Source Fixtures

`fixtures/sources/<id>.json` stores immutable cached-source fixtures for Hermes acceptance tests. Each file must validate against `code/schemas/source_fixture.schema.json`.

Required fields:

- `source_id`: UUID that also seeds the `sources.id` row during acceptance setup.
- `source_url`: public source URL or approved fixture locator.
- `source_type`: one of `post`, `video`, `podcast`, `blog`, `paper`.
- `platform`, `title`, `retrieved_at`, `source_language`, `speaker_or_author`.
- `transcript_text`: exact cached text Stage 2 receives.
- `transcript_sha256`: SHA-256 of `transcript_text` bytes.

The acceptance harness treats these files as read-only. Stage 2 receives the fixture path through `state.json` `input_files`, matching the §10 `runs/<run_id>/sources/<source_id>/transcript.txt` handoff pattern after fixture expansion.
