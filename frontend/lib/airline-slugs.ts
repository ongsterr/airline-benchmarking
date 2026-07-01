const SLUG_PATTERN = /^[a-z0-9-]{2,20}$/;

export function parseAirlineSlugInput(input: string): string[] {
  const seen = new Set<string>();
  const slugs: string[] = [];

  for (const part of input.split(",")) {
    const slug = part.trim().toLowerCase();
    if (!slug || seen.has(slug)) continue;
    seen.add(slug);
    slugs.push(slug);
  }

  return slugs;
}

export function validateAirlineSlugs(slugs: string[]): {
  valid: string[];
  invalid: string[];
} {
  const valid: string[] = [];
  const invalid: string[] = [];

  for (const slug of slugs) {
    if (SLUG_PATTERN.test(slug)) {
      valid.push(slug);
    } else {
      invalid.push(slug);
    }
  }

  return { valid, invalid };
}
