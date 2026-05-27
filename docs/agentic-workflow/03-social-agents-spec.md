# Social agents specification

One agent per platform. Each uses a model or retrieval path with legitimate platform access. The goal of this section is to be brutally honest about what is actually possible: generic models cannot be treated as if they can see platform content they have no real access to.

## Practitioner and source registry

Every social agent consumes the practitioner and source registry defined in section sixteen. The registry is part of this document set and is the contract for source identity, source tier, aliases, publishing surfaces, marker affinity, and commercial interests. Runtime implementations may load the registry from YAML, JSON, or database tables, but the canonical schema and default weights are defined in section sixteen.

`source_tier` drives discovery weighting. `source_grade` is display and review context for the practitioner's or organization's body of work; it is not the same thing as a claim's evidence sub-grade. The `aliases` field prevents attribution misses across handles, show names, newsletters, clinic brands, and common short names. The `commercial_interests` field exists not to disqualify practitioners — a Tier-A practitioner who runs a longevity clinic selling ApoB testing is not wrong about ApoB simply because they sell the test — but to surface the conflict transparently. The validation council in section five uses this field to compute a `financial_conflict_flag` and `financial_conflict_severity` on each BiomarkerClaim where the source's commercial interests overlap with the marker being discussed.

## Envelope-guided discovery

Discovery agents may receive sanitized research target envelope facts from section seventeen when those facts are marked `ready`. These facts are source-free internal research goals, not evidence. Agents may use them to expand search terms, prioritize numeric claims near a target or tolerance band, and identify contradiction candidates that need deeper review.

Envelope guidance must not flatten source granularity. If a broad input envelope says "general adult" but an open-source PDF, guideline, image table, or practitioner page exposes ranges by age, sex, weight, BMI, ethnicity, altitude, cohort, specimen, method, pregnancy status, or other population strata, the agent preserves those contextual fields in the candidate metadata. The source's granularity wins over the private seed. A generic envelope can start a search; it cannot constrain extraction to generic claims.

Discovery output may include matched envelope IDs, likely context fields, and a reason such as `near_target`, `inside_tolerance`, `outside_tolerance`, `more_granular_than_envelope`, or `not_comparable`. These fields help the council decide where research is converging, but they do not approve a claim and do not change evidence grade or scoring.

## X.com / Twitter — maintenance and content discovery

The access reality is that X/Twitter discovery must use sanctioned access. The first implementation uses `twitter-mcp` plus SearXNG-discovered public links rather than a Grok-native endpoint; generic models cannot be assumed to see current X content. Grok or another X-native model remains a possible future sanctioned access path if it is added to the LLM endpoint registry. Per the ScrapeOps Twitter teardown (retrieved 2026-05-13), X's terms of service restrict automated access to the official API, so unofficial scraping is out of scope.

X is retained for maintenance and content discovery, not as a primary evidence-bearing source. It is useful for finding newly published podcasts, videos, blog posts, preprints, conference talks, and practitioner discussions that point to deeper sources. X-sourced claims can enter the council only when the post or thread contains a clear numeric metabolic claim and can be corroborated by a non-X source such as a paper, podcast, video, blog post, clinic page, or guideline. The output is an `XSourceCandidate` containing author handle, post URL, post timestamp, verbatim post text, retrieved-at timestamp, tentative source tier, candidate markers, and any linked deeper source. The risk to manage is that X has low signal-to-noise for final MO evidence, so the X agent is rate-limited and cannot dominate the ranked source list. Provider usage policies are orchestration-runtime decisions.

## YouTube — Gemini agent

Implementation uses an inventory-first workflow. The Stage 1 YouTube path first records channel/video metadata for every registry `platform: youtube` surface, then ranks videos by marker aliases and marker-category membership before fetching transcripts. This keeps high-volume channels such as Anthony Chaffee MD tractable: a 1,000+ video channel is inventoried once, but only ranked videos above the configured threshold are cached as transcripts for Stage 2.

The model candidate is Gemini, using the native YouTube URL ingestion feature. Gemini accepts a public YouTube URL directly and processes audio plus sampled visual frames (Google AI documentation, retrieved 2026-05-13). The alternative for transcript-only work is `youtube-transcript-api`, a Python library that pulls user-provided or auto-generated captions without full video ingestion.

The agent's job is to discover videos where practitioners discuss metabolic markers and return URL, channel, upload date, view count, and the list of markers the video appears to cover. The terms-of-service reality is worth being explicit about. YouTube's terms prohibit scraping outside the official API; per the ScrapeOps YouTube teardown (retrieved 2026-05-13), "the Terms of Service explicitly ban all forms of scraping unless you're a public search engine, use YouTube's official APIs, or have obtained written permission beforehand." Gemini's native URL ingestion is Google-sanctioned and therefore safe. The `youtube-transcript-api` route operates in a gray zone — for fair-use factual quotation with attribution, the risk is low; for republication or training, the risk is high. We only quote, never republish. The legal agent records `transcript_method: third_party_caption_api` on these claims.

## Podcasts — direct RSS primary, Podscan augmentation

The podcast agent operates in two tiers.

Tier 1 is verified RSS feeds. The practitioner/source registry's `SourceSurface` entries with `platform: "podcast"` and an `rss_feed_url` provide direct feed URLs for known practitioner shows. A scheduled RSS reader polls these feeds and records new episodes as source candidates. If the episode provides a transcript, the pipeline stores the transcript source. If not, the runtime may use local or external transcription, with the method recorded.

Tier 2 is Podscan augmentation. Podscan discovers shows or episodes not already represented in verified RSS feeds and provides pre-transcribed content where available. Listen Notes and transcription providers remain fallback options for discovery and transcription gaps. Provider selection, quota checks, and usage limits are orchestration-runtime decisions.

The transcription method is recorded per source, with values such as `source_transcript`, `local_transcription`, `podscan_pretranscribed`, `assemblyai_universal2`, or `unknown`.

## Blogs, websites, and Substack — public page discovery

Blogs, websites, newsletters, and Substack surfaces are first-class discovery inputs when they are public and attributable. The practitioner/source registry represents them with `platform: "website"` or `platform: "substack"` and a canonical `handle_or_url`. The discovery goal is narrow: find marker-relevant public posts, preserve URL and retrieval timestamp, and extract only short attributed quotations needed for factual claims. Authenticated newsletter archives, paywalled pages, private posts, and scraped bulk archives are out of scope unless the legal agent explicitly approves the access path.

Substack is treated as a website-like source, not as a social platform. It can produce evidence-bearing claims only when the author is a named practitioner, researcher, organization, or media source in the section-sixteen registry, or when the post links to a deeper source that can be independently verified.

## Reddit — discovery-only community signal

Reddit is included as a discovery-only community-signal source, subject to terms-of-service review before implementation. The target surfaces are public communities relevant to metabolic health, low-carb nutrition, diabetes, longevity, fasting, lipid discussions, and insulin resistance. The registry may name specific subreddits through `SourceSurface` entries with `platform: "reddit"`, `subreddit`, and `post_type`. Reddit is useful for finding questions, recurring pain points, emerging terms, practitioner mentions, and links to deeper sources.

Reddit-sourced content is not treated as practitioner evidence unless the quoted content is from a named practitioner, researcher, organization, or linked deeper source that can be verified independently. Anonymous user reports can inform discovery and marker-context review, but they do not become MO practitioner claims. The output is a `RedditSourceCandidate` containing subreddit, post or comment URL, author handle, timestamp, text excerpt, candidate markers, matched practitioner aliases, and any linked deeper source. Bulk archive ingestion is out of scope; the Reddit channel must stay narrow, attributable, and citation-oriented.

## Semantic discovery pass

Keyword discovery is not sufficient for practitioner speech. After platform-specific discovery produces candidates, a semantic ranking pass re-scores candidate titles, descriptions, transcript excerpts, and post excerpts against the marker discovery brief. The model choice is runtime-configurable and deferred; the contract requirement is that semantic scores are recorded and can promote contextual matches that do not contain exact marker aliases. Prior semantic-search research should be preserved as calibration evidence: the `intfloat/multilingual-e5-large` family and an approximate 0.76 cosine threshold are known candidate baselines, not hard-coded requirements.

The ranked-source output includes:

- `keyword_score`
- `semantic_score`
- `final_discovery_score`
- `match_reason`
- `semantic_model`
- `semantic_threshold`
- `scoring_config_version`

The default final score blends source quality, surface priority, engagement, recency, and semantic relevance. Exact weights remain runtime configuration until calibration data is available.

## Telegram — public preview agent

The access surface is Telegram's public channel previews at `https://t.me/s/<channel>`, which serve post text, timestamps, view counts, and reactions without any account or `api_id` (Apify Telegram scraper documentation, retrieved 2026-05-13). The terms-of-service reality must be read carefully. Telegram's Bot Developer Terms explicitly prohibit, in their words, "any form of data collection aimed at creating large datasets, machine learning models and AI products, such as scraping public group or channel contents" (telegram.org/tos/bot-developers, retrieved 2026-05-13). This clause appears in the Bot Developer terms, constraining applications that use the Bot Platform — API ID, bot tokens, MTProto, and libraries like Telethon. The public `t.me/s/` web preview, which Telegram itself serves to indexing crawlers, sits in a different posture.

`[JUDGMENT]` The conservative reading of this distinction is that we do not use the Bot API, `api_id`/`api_hash`, MTProto, or Telethon for dataset construction. We use only the public web preview surface. We treat its output as discovery signal, not training corpus. We store only the minimum needed for citation. If a marker has insufficient Telegram signal under this constraint, we accept the gap.

## Out-of-scope and restricted platforms

| Platform | Access reality | Posture |
| --- | --- | --- |
| LinkedIn | Third-party API access for content discovery does not exist. The hiQ Labs v. LinkedIn line of cases (Ninth Circuit affirmed scraping public profiles is not a CFAA violation; N.D. Cal. then ruled hiQ breached LinkedIn's user agreement; settlement and injunction followed — California Lawyers Association, Privacy World, Staffing Industry, retrieved 2026-05-13) establishes contract liability as the live risk. | `[JUDGMENT]` Manual-seed channel only. The user curates practitioner LinkedIn URLs opened directly for verification. No scraping. |
| Facebook / Instagram | Meta's Graph API is for managing your own pages. The Meta Content Library (transparency.meta.com, retrieved 2026-05-13) requires non-profit academic affiliation, CASD review, and access inside Meta's SRE or SOMAR's VDE. | `[JUDGMENT]` Deferred entirely for the first implementation. Third-party "unofficial Facebook APIs" expose contract liability without strategic advantage; substantive metabolic practitioners are on X, YouTube, and podcasts. |

## The WSJ findings and why they reinforce this design

The May 2026 Wall Street Journal article by Andrea Petersen, "Wellness Influencers Come Under Scrutiny," reports several findings that bear directly on this section. The Pew Research Center study underlying the article found that the influencer category labeled "healthcare professional" is broad and unreliable as a credentials signal in itself — it includes doctors and dietitians but also chiropractors and massage therapists, with sixteen percent of influencers reporting no credentials at all. Brooke Nickel at the University of Sydney School of Public Health noted in the same article that "some people called themselves doctors but 'that might just be their handle for whatever reason.'" This is precisely why our practitioner/source registry requires human-curated tier values rather than algorithmically derived ones: bio claims in social media are unreliable by default, and our tiering depends on the user's editorial judgment, not on what handles or profile fields say. Nickel's 2025 study found that about seventy percent of influencer posts about medical tests carried undisclosed financial conflicts of interest, which directly motivates the `commercial_interests` field on the registry entry. The 2024 Australian study in the International Journal of Behavioral Nutrition and Physical Activity found that posts from registered dietitians were significantly more accurate than posts from generic influencers, which provides empirical support for credential-weighted tiering as a design choice. None of this changes the architecture; all of it independently validates the architecture's existing posture.
