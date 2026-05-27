# YouTube Transcript Discovery

YouTube is a primary discovery surface for practitioner-heavy MO claims. The pipeline handles it in two phases.

## Phase 1: Channel inventory

The inventory step reads `platform: youtube` surfaces from `input/practitioner_registry.json`, resolves each channel, and records video metadata into `runs/<run_id>/discovery/youtube_inventory.jsonl`. Metadata includes video id, URL, title, description, upload timestamp, duration, view count, channel id, channel title, practitioner id, and practitioner name.

Inventory is allowed to run across every registry YouTube channel because it stores metadata only and uses sanctioned YouTube API access.

## Phase 2: Ranked transcript cache fill

The ranking step scores video title and description against marker aliases plus marker-category expansions from `input/marker_categories.yaml`. The transcript step fetches only ranked videos above the configured threshold and writes normal source fixtures under `fixtures/sources/` or `runs/<run_id>/sources/<source_id>/`.

Default transcript limits:

| Setting | Default |
| --- | ---: |
| max videos per channel inventory | 50 |
| min transcript keyword score | 5 |
| max transcripts per run | 25 |
| max transcripts per practitioner per run | 10 |

## Allowed transcript methods

| Method | `transcript_method` value | Use |
| --- | --- | --- |
| YouTube MCP transcript | `youtube_mcp_transcript` | Preferred transcript cache fill when available. |
| Gemini native URL ingestion | `gemini_native_youtube_url` | Allowed for direct source analysis when transcript export is unavailable. |
| Operator supplied JSON transcript | `operator_supplied_json_transcript` | Allowed for fixtures and manually reviewed cache fills. |
| Public caption API | `third_party_caption_api` | Allowed for targeted public caption cache fill when MCP transcript access is unavailable; do not use for bulk republication or training. |

The pipeline does not download video or audio files for this task. It does not use authenticated pages, private videos, member-only videos, or access-control bypasses.

## Stage 2 boundary

Stage 2 never calls YouTube directly. It receives cached transcript fixtures with `source_type: video`, `platform: youtube`, `source_url`, `transcript_method`, `transcript_text`, and `transcript_sha256`.

## Bootstrap target

`person:anthony-chaffee` is the first high-volume channel used to validate this workflow. The initial production run inventories his channel, ranks videos for `apob`, `fasting-insulin`, `hba1c`, and `tg-hdl-ratio`, and caches transcripts for the top ranked videos that have available captions.
