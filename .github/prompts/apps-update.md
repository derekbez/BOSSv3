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

## Tier 2 — Bug fixes (one-liners)

8. **`random_local_place_name` — empty-list crash.** `random.choice(places)` crashes with `IndexError` if `places` is empty after loading. Change `_show()` to guard: `if not places: api.screen.display_text("No places loaded"); return`.

9. **`current_weather` — move import to top-level.** The `import datetime` inside `_format_next_hours()` should move to the module top alongside other imports. Also consider adding timezone handling for consistency with the API's UTC timestamps.

10. ~~**`internet_speed_check` — fix `requires_network` (interim).**~~ ✅ Superseded by step 6 (real speedtest implemented).

## Tier 3 — Upgrades (enhance existing working apps)

11. **`color_of_the_day` — add colour swatch + API resilience.** ColourLovers API is unreliable. Add a fallback: if the API fails, generate a deterministic "colour of the day" from a hash of the date. Use `api.screen.display_html()` to show an actual colour swatch rectangle alongside the hex code. Keep ColourLovers as primary source when reachable.

12. **`tiny_poem` — add pagination for long poems.** Currently uses `textwrap.wrap` directly. Replace with `TextPaginator` from `_lib/paginator.py` for poems that exceed one screen. Add yellow/blue button navigation like `on_this_day` does. Use `wrap_paragraphs()` from the paginator module for consistency.

13. **`space_update` — add toggle between APOD and Mars.** Currently picks one randomly. Add button interaction: green = refresh current, yellow = switch to APOD, blue = switch to Mars Curiosity. Light the corresponding LEDs when each mode is active. Consider using `DEMO_KEY` as a fallback for NASA API (rate-limited but functional).

14. **`public_domain_book_snippet` — show contiguous passages.** Currently shows random non-contiguous lines which read incoherently. Change to pick a random start position and show N contiguous lines. Add more `.txt` assets (e.g. public domain excerpts from Project Gutenberg). Add pagination with yellow/blue buttons for long passages.

15. **`name_that_animal` — add fallback for unreliable API.** Zoo Animal API is on Heroku free tier and may cold-start or go offline. Add a local `animals_fallback.json` asset with ~50 animals. If the API call fails, serve from the fallback list. Log a warning when falling back.

16. **`today_in_music` — rename or fix mismatch.** "Today in Music" implies historical music events but actually shows top tracks for a genre tag via Last.fm. Either:
    - (a) **Rename** to "Top Tracks" and update `display_name` + `description`, or
    - (b) **Rewrite** to actually show music history events (e.g. use a "this day in music history" API or dataset)
    - Recommend option (a) as it's honest and requires minimal code change.

17. **`flights_leaving_heathrow` — make airport configurable.** Airport is hardcoded to `LHR`. Add `"airport": "LHR"` to manifest `config` block and read it via `cfg.get("airport", "LHR")`. Update the title dynamically. Same change for `flight_status_favorite_airline` — make airline configurable via `config`.

## Tier 4 — Polish (nice-to-have)

18. **`joke_of_the_moment` — refactor closure.** Replace mutable `[None]` list pattern with `nonlocal` keyword for `pending_punchline`. Minor code clarity improvement.

19. **`app_jokes` — guard against None payload.** Add `if event.payload is None: return` guard in `on_button`. Defensive, edge-case only.

20. **`admin_wifi_configuration` — add logging on scan failure.** The silent `pass` in `_scan_networks` and `_get_current_wifi` exception handlers should log a debug message.

21. **`bird_sightings_near_me` — friendlier "no sightings" message.** Currently raises `ValueError("No sightings")` which displays as an error. Return a user-friendly string instead.

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
