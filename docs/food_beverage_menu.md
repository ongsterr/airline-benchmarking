# Extraction Pipeline for F&B Menu

The data structure for menu extraction should follow the below level of detail - (airline × cabin × route × direction × date).

Example data structure:

```json
{
	"source": {
		"source_id": "emirates_dining_business",
		"airline": "emirates",
		"source_type": "airline_official",
		"default_tier": 1
	},
	"capture": {
		"capture_id": "b3f1c2a0-7d44-4e91-9a2e-1c8f0a5e9d21",
		"source_url": "https://www.emirates.com/english/experience/dining/business-class/",
		"captured_at": "2025-07-06T09:14:22Z",
		"snapshot_path": "evidence/emirates/business_dining_20250706.html",
		"media_type": "text/html",
		"raw_bytes_size": 418223
	},
	"observations": [
		{
			"observation_id": "1a9d4e77-2c05-4b8a-bf3e-6d2a71f0c9b4",
			"capture_id": "b3f1c2a0-7d44-4e91-9a2e-1c8f0a5e9d21",
			"airline": "emirates",
			"cabin_norm": "business",
			"cabin_marketing": "Business Class",
			"origin_iata": null,
			"dest_iata": null,
			"direction": null,
			"menu_cycle": "2025-07",
			"service_date": null,
			"grain_observed": ["airline", "cabin"],
			"confidence_tier": 1,
			"extractor_version": "gpt-x+prompt_v3",
			"extracted_at": "2025-07-06T09:15:40Z",
			"items": [
				{
					"course": "main",
					"item_name": "Grilled seabass with saffron sauce",
					"item_desc": "served with roasted baby vegetables and herbed rice",
					"position": 1,
					"is_vegetarian": false,
					"is_vegan": false,
					"is_alcoholic": false,
					"source_span": "Grilled seabass with saffron sauce, served with roasted baby vegetables and herbed rice",
					"grounding_method": "exact",
					"grounding_score": 1.0,
					"item_hash": "m:grilled_seabass_saffron"
				},
				{
					"course": "beverage_alcoholic",
					"item_name": "Moet & Chandon Brut Imperial",
					"item_desc": "champagne, served throughout the flight",
					"position": 1,
					"is_vegetarian": null,
					"is_vegan": null,
					"is_alcoholic": true,
					"source_span": "a complimentary glass of champagne served as soon as you arrive on board",
					"grounding_method": "fuzzy",
					"grounding_score": 0.88,
					"item_hash": "b:moet_chandon_brut"
				}
			]
		}
	]
}
```

## Data Sources

### Emirates

Website Load Type: Static

Website URL Template: https://www.emirates.com/ae/english/experience/dining/onboard-menu/?date={yyyy-mm-dd}&flight={flight-number}&origin={origin}&destination={destination}&cabinclass={cabin-code}&view=1

Website URL Example: https://www.emirates.com/ae/english/experience/dining/onboard-menu/?date=2026-08-01&flight=7&origin=DXB&destination=LHR&cabinclass=y&view=1

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
