"""Data loaders for seeding the metabolicum-agentic-research database.

Each loader reads from input/ files and populates the corresponding
Supabase tables. Loaders are idempotent (upsert-based) and can be
re-run safely.

Usage:
    python -m code.loaders.marker_glossary [--local|--remote]
    python -m code.loaders.practitioner_registry [--local|--remote]
    python -m code.loaders.sm_anchors [--local|--remote]
    python -m code.loaders.envelope_facts [--local|--remote]

    # Or load everything at once:
    python -m code.loaders --all [--local|--remote]
"""

from __future__ import annotations

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_target(use_local: bool = True):
    """Get the appropriate DB client based on --local/--remote flag."""
    from code.db import local_psycopg, remote
    if use_local:
        return local_psycopg()
    return remote()


def parse_target_args() -> argparse.Namespace:
    """Parse common --local/--remote arguments."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--local", action="store_true", default=True,
                       help="Write to local Supabase (default)")
    group.add_argument("--remote", action="store_true",
                       help="Write to remote Supabase cloud project")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be loaded without writing")
    return parser.parse_args()
