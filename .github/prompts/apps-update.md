# Plan: Mini-App Quality Overhaul

All 31 mini-apps audited. 9 are OK as-is; 22 need work ranging from one-line manifest fixes to full rewrites. Work is grouped into 5 tiers by effort and urgency. A cross-cutting consistency pass handles patterns that repeat across many apps.

**Steps**

## Tier 0 — Cross-cutting consistency fixes (batch) ✅ DONE

These are mechanical patterns that repeat across 8–10 apps and should be fixed in a single pass.

1. ~~**Dead-code `cfg.get("api_key")` removal.**~~ ✅ Removed the `cfg.get("api_key") or` fallback from all 10 apps. Each now reads solely from `api.get_secret("BOSS_APP_…")`. Affected: `bird_sightings_near_me`, `breaking_news`, `flights_leaving_heathrow`, `flight_status_favorite_airline`, `local_tide_times`, `moon_phase`, `space_update`, `today_in_music`, `top_trending_search`, `word_of_the_day`.

2. ~~**Missing-key-as-string → raise.**~~ ✅ Changed 8 apps that returned a string like `"(no API key set)"` to raise `RuntimeError("Missing secret: BOSS_APP_XXX_API_KEY")`. The standard `except Exception` error path in each app's `_show()` now displays the message consistently. `bird_sightings_near_me` and `breaking_news` already raised — no change needed. `space_update` had an inline check in `_show()` — converted to `raise RuntimeError`.

3. ~~**Missing manifest fields.**~~ ✅ Added `"requires_network": false` and `"required_env": []` to `admin_shutdown`, `admin_startup`, and `list_all_apps` manifests. All 31 manifests pass `validate_manifests.py`.

4. ~~**Extract `_get_local_ip()` to `_lib`.**~~ ✅ Created `src/boss/apps/_lib/net_utils.py` with shared `get_local_ip()`. Updated `admin_boss_admin` and `admin_wifi_configuration` to import from `_lib.net_utils`. Removed duplicated function and `import socket` from both. Updated corresponding tests (`test_admin_boss_admin.py`, `test_admin_wifi.py`) to import from the new location. 442 tests pass.

## Tier 1 — Broken / critical (immediate) ✅ DONE

5. ~~**`quote_of_the_day` — replace dead API.**~~ ✅ Replaced dead `api.quotable.io` with ZenQuotes.io (`https://zenquotes.io/api/random`). Updated `_fetch()` to parse `[{"q": "...", "a": "..."}]` response. Updated manifest description. No API key needed.

6. ~~**`internet_speed_check` — implement real speed test.**~~ ✅ Replaced `random.uniform()` stub with real `speedtest-cli` library. Added `speedtest-cli>=2.1,<3` to `pyproject.toml`. Shows "Testing…" while running, displays download/upload in Mbps and ping in ms. Handles `ConfigRetrievalError`. Timeout increased to 120s. Moved to `NETWORK_APPS` in smoke tests.

7. ~~**`constellation_of_the_night` — implement with local calculation.**~~ ✅ Added `ephem>=4.1,<5` to `pyproject.toml`. Uses `api.get_global_location()` for lat/lon, computes visible constellations via `ephem.Observer` with 30 bright stars. Shows constellation name, peak altitude, and compass direction. Green button refreshes. Auto-refresh every 600s. Moved to `NETWORK_APPS` in smoke tests (uses geolocation). Manifest bumped to 1.0.0.

## Tier 2 — Bug fixes (one-liners) ✅ DONE

8. ~~**`random_local_place_name` — empty-list crash.**~~ ✅ Added explicit empty-list guard in `_show()`: if `places` is empty, displays "No places loaded" and returns early instead of calling `random.choice()` on an empty list.

9. ~~**`current_weather` — move import to top-level.**~~ ✅ Moved `import datetime` from inside `_format_next_hours()` to the module-level imports block.

10. ~~**`internet_speed_check` — fix `requires_network` (interim).**~~ ✅ Superseded by step 6 (real speedtest implemented).

## Tier 3 — Upgrades (enhance existing working apps) ✅ DONE

11. ~~**`color_of_the_day` — add colour swatch + API resilience.**~~ ✅ Added date-hash fallback (`_fallback_color()`) when ColourLovers API fails. Switched from `display_text()` to `display_html()` with a 120×120px colour swatch, hex code, and colour name. ColourLovers remains primary source.

12. ~~**`tiny_poem` — add pagination for long poems.**~~ ✅ Replaced `textwrap.wrap` with `TextPaginator` + `wrap_paragraphs` from `_lib/paginator.py`. Yellow/blue buttons navigate pages. Green fetches a new poem. LEDs cleaned up on exit.

13. ~~**`space_update` — add toggle between APOD and Mars.**~~ ✅ Replaced `random.choice` with explicit mode toggle. Yellow = APOD mode, Blue = Mars mode, Green = refresh current. Mode-matching LEDs light up. Removed `import random`.

14. ~~**`public_domain_book_snippet` — show contiguous passages.**~~ ✅ Changed `random.sample` (non-contiguous) to `_pick_contiguous()` which selects N consecutive lines from a random start position. Added `TextPaginator` with yellow/blue navigation. Added two new `.txt` assets (Pride and Prejudice opening, Alice in Wonderland opening). Default `lines` bumped to 20.

15. ~~**`name_that_animal` — add fallback for unreliable API.**~~ ✅ Created `assets/animals_fallback.json` with 50 animals. On API failure, falls back to random selection from local JSON. Logs info message when falling back. Shows "(offline)" in title when using fallback.

16. ~~**`today_in_music` — rename to "Top Tracks".**~~ ✅ Changed `display_name` to "Top Tracks" and `description` to "Top tracks for a genre tag (Last.fm)." in manifest. Updated docstring and title variable in code. Directory name unchanged to preserve switch mapping.

17. ~~**`flights_leaving_heathrow` — make airport configurable.**~~ ✅ Added `"airport": "LHR"` to manifest config. Code reads `cfg.get("airport", "LHR")` and uses it in API call and title. `flight_status_favorite_airline` already had configurable `iata` — no change needed.

## Tier 4 — Polish (nice-to-have) ✅ DONE

18. ~~**`joke_of_the_moment` — refactor closure.**~~ ✅ Replaced `pending_punchline: list[str | None] = [None]` mutable-container pattern with `pending_punchline: str | None = None` and `nonlocal pending_punchline` in both `_show_new()` and `on_button()`.

19. ~~**`app_jokes` — guard against None payload.**~~ ✅ Added `if event.payload is None: return` guard at the top of `on_button()`.

20. ~~**`admin_wifi_configuration` — add logging on scan failure.**~~ ✅ Added module-level `_log = logging.getLogger(__name__)`. Changed silent `except: pass` in `_get_current_wifi()` and `_scan_networks()` to log debug messages via `_log.debug(...)`.

21. ~~**`bird_sightings_near_me` — friendlier "no sightings" message.**~~ ✅ Replaced `raise ValueError("No sightings")` with `return [("No recent sightings in this area.", "")]` — displays as a normal text line instead of an error.

## Apps confirmed OK as-is (no changes needed)

- `admin_boss_admin`, `app_jokes` (minor polish only), `breaking_news`, `dad_joke_generator`, `hello_world`, `on_this_day`, `random_emoji_combo`, `random_useless_fact`

## Verification

- Run `python scripts/validate_manifests.py` after every manifest change
- Run `pytest tests/ -x --tb=short` — must maintain 442+ passing tests
- For new dependencies (`speedtest-cli`, `ephem`): add to `pyproject.toml [project.dependencies]`, verify `pip install -e ".[dev]"` succeeds
- For `quote_of_the_day`: manually verify `https://zenquotes.io/api/random` returns valid JSON in browser
- For `constellation_of_the_night`: verify `ephem` computes sensible results for the configured lat/lon
- For `internet_speed_check`: run once manually and confirm download/upload/ping are realistic values
- Smoke tests should still pass for every modified app (`test_app_smoke.py`)
- Update `improvements.prompt.md` items #21 and #22 (stub apps) when their implementations are complete

## Decisions

- `quote_of_the_day`: ZenQuotes.io (free, no key) over API Ninjas or local file
- `constellation_of_the_night`: local `ephem` calculation over astronomy API (no key needed, works offline)
- `internet_speed_check`: real `speedtest-cli` measurement over keeping as demo
- `today_in_music`: rename to "Top Tracks" rather than rewrite to show actual music history
- Missing-key handling: raise `RuntimeError` consistently (matches `bird_sightings_near_me` and `breaking_news` patterns which already work correctly)
