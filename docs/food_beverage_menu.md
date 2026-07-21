# Extraction Pipeline for F&B Menu

The data structure for menu extraction should follow the below level of detail - (airline × cabin × route × direction × date).

Example data structure (Emirates digital-menu API transform):

```json
{
	"source": {
		"source_id": "emirates_dining_onboard",
		"airline": "emirates",
		"source_type": "airline_official",
		"default_tier": 1
	},
	"capture": {
		"capture_id": "b3f1c2a0-7d44-4e91-9a2e-1c8f0a5e9d21",
		"source_url": "https://www.emirates.com/ae/english/experience/dining/onboard-menu/?date=2026-08-01&flight=7&origin=DXB&destination=LHR&cabinclass=y&view=1",
		"captured_at": "2026-08-01T09:14:22Z",
		"snapshot_path": "evidence/emirates/dxb_lhr_7_2026-08-01_y.json",
		"media_type": "application/json",
		"raw_bytes_size": 18422
	},
	"observations": [
		{
			"observation_id": "1a9d4e77-2c05-4b8a-bf3e-6d2a71f0c9b4",
			"capture_id": "b3f1c2a0-7d44-4e91-9a2e-1c8f0a5e9d21",
			"airline": "emirates",
			"cabin_norm": "economy",
			"cabin_marketing": "Economy Class",
			"origin_iata": "DXB",
			"dest_iata": "LHR",
			"direction": "outbound",
			"menu_cycle": "2026-08",
			"service_date": "2026-08-01",
			"grain_observed": ["airline", "cabin", "route", "direction", "date"],
			"confidence_tier": 1,
			"extractor_version": "menu_api_transform_v1",
			"extracted_at": "2026-08-01T09:15:40Z",
			"items": [
				{
					"category": "Breakfast",
					"subcategory": "Main Course",
					"code": "76246",
					"title": "Vegan crêpes",
					"desc": "Filled with carrots and peppers",
					"position": 1,
					"item_hash": "m:76246",
					"item_type": "food",
					"beverage_type": null,
					"is_vegetarian": true,
					"is_vegan": true,
					"is_localized": false,
					"localization_confidence": 0.88,
					"localization_note": "Western vegan dish not specific to LHR",
					"enrichment_version": "menu_enrichment_v1",
					"enriched_at": "2026-08-01T09:16:10Z"
				},
				{
					"category": "Beverages",
					"subcategory": "Juices and Soft Drinks",
					"code": "BV000112",
					"title": "",
					"desc": "Orange, pineapple, apple, mango or tomato Cola and diet cola, lemonade, ginger ale, soda and tonic water, still and sparkling water",
					"position": 2,
					"item_hash": "m:BV000112",
					"item_type": null,
					"beverage_type": null,
					"is_vegetarian": null,
					"is_vegan": null,
					"is_localized": null,
					"localization_confidence": null,
					"localization_note": null,
					"enrichment_version": null,
					"enriched_at": null
				}
			]
		}
	]
}
```

## Data Sources

### Emirates

Website Load Type: Javascript rendered (menu content via API)

Website URL Template: https://www.emirates.com/ae/english/experience/dining/onboard-menu/?date={yyyy-mm-dd}&flight={flight-number}&origin={origin}&destination={destination}&cabinclass={cabin-code}&view=1

Website URL Example: https://www.emirates.com/ae/english/experience/dining/onboard-menu/?date=2026-08-01&flight=7&origin=DXB&destination=LHR&cabinclass=y&view=1

Digital menu API (pipeline uses this): `POST https://www.emirates.com/service/exp/digital-menu?lang=en`

Request body:
```json
{
  "flightNumber": "7",
  "departureStation": "DXB",
  "scheduledDate": "2026-Aug-01",
  "cabinClass": "Y",
  "isPaxMeal": false,
  "isDigitalMenuWithPaxMeal": ""
}
```

Notes: The onboard-menu HTML page is a Next.js shell; dish content is loaded client-side from the digital-menu API. The API is publicly accessible (no login). Cabin codes: `f` First, `j` Business, `w` Premium Economy, `y` Economy. Date format for the API is `YYYY-MMM-DD` (e.g. `2026-Aug-01`).

### Pipeline extraction flow (Emirates)

1. **Fetch** — `POST` digital-menu API; persist JSON evidence (`media_type=application/json`).
2. **Deterministic clean + flatten** — walk `categories` → `subCategories` → `items` and emit one row per item:
   - `category` ← cleaned `categories[].title`
   - `subcategory` ← cleaned `subCategories[].title`
   - `code` ← cleaned `items[].code`
   - `title` ← cleaned `items[].title`
   - `desc` ← cleaned `items[].desc`
3. **Blank-title expansion (optional LLM)** — when `title` is empty and `desc` is present, one Gemini call per cabin (`MENU_LLM_MODEL`, default `gemini-3.5-flash`, `temperature=0`) splits the description into discrete items. Generated codes use `BASE_1`, `BASE_2`, …; category/subcategory are inherited. If the key is missing or the response is invalid, the original blank-title row is kept.
4. **Load** — upsert `menu_captures` / `menu_observations` / `menu_items` by reconciling on `item_hash` (update in place; retain enrichment when category/subcategory/code/title/desc are unchanged; clear enrichment when those fields change; insert new rows unenriched; delete stale rows).
5. **Enrichment (bulk Gemini)** — after load, query that observation’s rows where `enriched_at IS NULL`, batch in groups of 50, and classify each item:
   - `item_type`: `food` | `beverage`
   - beverages → `beverage_type` (`alcoholic` | `non_alcoholic`); food-only fields null
   - foods → `is_vegetarian`, `is_vegan` (vegan ⇒ vegetarian), `is_localized`, `localization_confidence` (0–1), `localization_note`
   - localization target is the non-DXB origin/destination; `is_localized=true` only when title/desc identify cuisine specifically tied to that country/region (generic / UAE / Middle Eastern / globally common dishes are false unless specifically tied to the target)
   - valid rows get `enrichment_version=menu_enrichment_v1` + UTC `enriched_at`; invalid/missing/mismatched rows stay null and are retried on a later run
   - enrichment failures are logged and do not fail the extracted menu; audit written to `.enrichment.json`

Cleaning removes HTML tags (including literal and entity-encoded `<br>`), HTML entities, control characters, and line breaks; collapses whitespace; and preserves punctuation and Unicode accents. Cabins with no blank-title descriptions skip blank-title Gemini; enrichment still runs for unenriched rows when a key is present.

| `source` (extract) | Meaning |
|----------|---------|
| `api` | No blank-title candidates; deterministic only |
| `api+llm` | At least one blank-title candidate expanded |
| `api_llm_fallback` | Candidates existed but none expanded (no key / error / invalid) |

`extractor_version`: `menu_api_transform_v2` (+ `menu_blank_title_prompt_v1` + model when blank-title LLM runs). Enrichment is a separate stage (`menu_enrichment_prompt_v1` / `menu_enrichment_v1`).

**Sample enrichment checks (saved menus):** EK7 DXB–LHR vegan dishes (`is_vegan` / `is_vegetarian`); alcoholic Beer/Wine/Champagne vs non-alcoholic juices/soft drinks; EK582 DXB–DAC foods with Bengali-style descriptions as localized-to-DAC evidence.

### British Airways

### Virgin Atlantic

### Air India

Website Load Type: Javascript rendered

Website URL: https://www.airindia.com/in/en/experience/in-air/whats-on-my-ai/dining/check-your-menu.html

Usage: Require origin, destination and flight date in search interface -> then click on a specific flight number or use the default one -> click "Check our Menu" -> select cabin class from a dropdown selection

### United Airline

Website Load Type: Static

Website URL: https://www.united.com/en/us/fly/travel/inflight/dining-menu.html

### Lufthansa

Website Load Type: Javascript rendered

Website URL: https://www.lufthansa.com/mv/en/culinaryjourney#/menu-page

Usage: Require flight number input, cabin class and flight date for no-booking view
