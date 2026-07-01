export const MAX_COMPARE_CONFIGS = 8;
export const MIN_COMPARE_CONFIGS = 2;
export const FLEET_PAGE_SIZE = 50;
export const FLEET_LOOKUP_LIMIT = 500;

const TEST_AIRLINE_SLUG_PREFIXES = ["test-", "tst-"] as const;
const TEST_AIRLINE_SLUGS = new Set(["tuups1", "tuups2", "tuups3"]);

/** Slugs from pytest fixtures — excluded from airline lists and compare pickers. */
export function isDisplayAirlineSlug(slug: string): boolean {
  if (TEST_AIRLINE_SLUGS.has(slug)) return false;
  return !TEST_AIRLINE_SLUG_PREFIXES.some((prefix) => slug.startsWith(prefix));
}
