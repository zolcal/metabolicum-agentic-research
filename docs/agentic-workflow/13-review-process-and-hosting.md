# Repository and handoff policy

The specification and implementation should live in Git-backed markdown and code repositories. Git provides diff tracking, pull requests, blame, branch protection, and a durable audit trail for changes that affect research output.

`[JUDGMENT]` The implementation repository is `metabolicum-agentic-research`. It contains the runtime code, database migrations, run-state conventions, and reviewed export artifacts. The documentation set defines the contracts that repository must satisfy, but the runtime repository owns implementation choices.

The documentation remains private while it contains operational details, provider choices, source rosters, or legal risk analysis. It can be published later only after credentials, private notes, and sensitive implementation details are removed.

The production handoff repository or branch is separate from the agent runtime. Reviewed artifacts from `metabolicum-agentic-research` are submitted for controlled import into `metasync`, with one pull request per marker-paradigm per run containing the artifact and a `RUN_REPORT.md`. Merging or importing requires manual approval and must not grant the agentic project direct production credentials.

Every production handoff must include enough context for review: source count, approved claim count, quarantine count by reason, evidence-grade distribution, provenance completion rate, legal review status, provider/resource anomalies if any, and a statement of whether the import changes user-facing content, internal review content, or both.
