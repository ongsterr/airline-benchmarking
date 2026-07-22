"""Shared application constants."""

MAX_COMPARE_CONFIGS = 8

# Slugs created by integration tests — hidden from airline summary / compare pickers.
TEST_AIRLINE_SLUG_PREFIXES = ("test-", "tst-")
TEST_AIRLINE_SLUGS = frozenset({"tuups1", "tuups2", "tuups3"})

# Pytest menu fixtures use this source_url — hidden from menu filter-options UI.
TEST_MENU_SOURCE_URLS = frozenset(
    {
        "https://example.com/menu",
        "http://example.com/menu",
    }
)


def is_display_airline_slug(slug: str) -> bool:
    """Return False for pytest fixture airlines that should not appear in the UI."""
    if slug in TEST_AIRLINE_SLUGS:
        return False
    return not slug.startswith(TEST_AIRLINE_SLUG_PREFIXES)


def is_display_menu_source_url(source_url: str | None) -> bool:
    """Return False for pytest fixture menu captures that should not appear in the UI."""
    if not source_url:
        return False
    normalized = source_url.strip().rstrip("/")
    if normalized in TEST_MENU_SOURCE_URLS:
        return False
    # Any example.com host is fixture data (with or without path / trailing junk).
    host = normalized.lower().split("://", 1)[-1].split("/", 1)[0]
    if host == "example.com" or host.endswith(".example.com"):
        return False
    return True


def is_display_menu_capture(*, airline_slug: str | None, source_url: str | None) -> bool:
    """True when a menu capture should appear in Menu Analysis filter options."""
    if airline_slug is None or not is_display_airline_slug(airline_slug):
        return False
    return is_display_menu_source_url(source_url)
