"""Shared application constants."""

MAX_COMPARE_CONFIGS = 8

# Slugs created by integration tests — hidden from airline summary / compare pickers.
TEST_AIRLINE_SLUG_PREFIXES = ("test-", "tst-")
TEST_AIRLINE_SLUGS = frozenset({"tuups1", "tuups2", "tuups3"})


def is_display_airline_slug(slug: str) -> bool:
    """Return False for pytest fixture airlines that should not appear in the UI."""
    if slug in TEST_AIRLINE_SLUGS:
        return False
    return not slug.startswith(TEST_AIRLINE_SLUG_PREFIXES)
