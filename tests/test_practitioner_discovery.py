from scripts.practitioner_discovery import terms


def test_marker_terms_uses_t1_t2_phrases_and_drops_excluded():
    policy = {
        "total-testosterone": {
            "tiers": {
                "T1": ["total testosterone"],
                "T2": ["testosterone (total)", "serum testosterone"],
                "T3": ["testosterone"],
                "T4": ["testo"],
            },
            "excluded_terms": ["testo"],
        }
    }
    out = terms.marker_terms("total-testosterone", policy)
    assert out == ["total testosterone", "testosterone (total)", "serum testosterone"]
    # bare generic T3/T4 terms are never used for discovery
    assert "testosterone" not in out
    assert "testo" not in out


def test_marker_terms_unknown_marker_is_empty():
    assert terms.marker_terms("nope", {}) == []
