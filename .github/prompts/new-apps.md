# Plan: New Mini-Apps for BOSSv3

Candidate apps for implementation, organized by category. All leverage the 3-colour-button + screen interaction model (LED-gated: Yellow, Green, Blue). Priority picks marked with ⭐.

## Platform Constraints Recap

- **Inputs:** 3 colour buttons (yellow/green/blue) — only active when matching LED is ON
- **Outputs:** `display_text()`, `display_html()`, `display_image()`, `display_markdown()`, `clear()` + 4 LEDs
- **Threading:** Single daemon thread per app, cooperative stop via `stop_event`
- **Helpers:** `fetch_json()`, `fetch_text()`, `TextPaginator`, `wrap_paragraphs()`, `get_local_ip()`
- **Location:** `api.get_global_location()` → `{"lat", "lon"}` (default: London)

---

## Free API-Powered Info Apps (no key needed)

### ⭐ 1. ISS Tracker ✅ IMPLEMENTED (`iss_tracker`, switch `155`)
- **API:** [Open Notify](http://open-notify.org/Open-Notify-API/) — `http://api.open-notify.org/iss-now.json` + `/astros.json`
- **Display:** Current lat/lon, altitude, crew count. Show distance from user's location.
- **Buttons:** Green = refresh position
- **Tags:** `content`, `network`, `science`
- **Notes:** Dead-simple API, unique "wow factor," no key needed

### ⭐ 2. Currency Exchange ✅ IMPLEMENTED (`currency_exchange`, switch `156`)
- **API:** [Frankfurter](https://www.frankfurter.app/) — `https://api.frankfurter.app/latest?from=GBP`
- **Display:** GBP→USD/EUR/JPY (or configurable pairs). Show rate + daily change direction.
- **Buttons:** Yellow/Blue = cycle currency pairs, Green = refresh
- **Config:** `base_currency: "GBP"`, `target_currencies: ["USD", "EUR", "JPY", "AUD", "CHF"]`
- **Tags:** `content`, `network`
- **Notes:** Practical daily utility, free, reliable (ECB data)

### 3. Wikipedia Random Article ✅ IMPLEMENTED (`wikipedia_random_article`, switch `157`)
- **API:** [Wikipedia REST](https://en.wikipedia.org/api/rest_v1/) — `/page/random/summary`
- **Display:** Article title + extract with TextPaginator
- **Buttons:** Yellow/Blue = paginate, Green = new article
- **Tags:** `content`, `network`

### ⭐ 4. Sunrise / Sunset ✅ IMPLEMENTED (`sunrise_sunset`, switch `158`)
- **API:** [Sunrise-Sunset](https://sunrise-sunset.org/api) — uses existing lat/lon from `get_global_location()`
- **Display:** Sunrise, sunset, golden hour, day length, solar noon. Could show progress bar of daylight remaining.
- **Buttons:** Green = refresh
- **Tags:** `content`, `network`
- **Notes:** Complements existing weather + moon phase + constellation apps nicely

### 5. Country Fact ✅ IMPLEMENTED (`country_fact`, switch `159`)
- **API:** [REST Countries](https://restcountries.com/v3.1/all) — random country
- **Display:** Flag emoji, name, capital, population, languages, region
- **Buttons:** Green = new country
- **Tags:** `novelty`, `network`

### 6. Earthquake Monitor ✅ IMPLEMENTED (`earthquake_monitor`, switch `160`)
- **API:** [USGS](https://earthquake.usgs.gov/fdsnws/event/1/) — `query?format=geojson&minmagnitude=4&limit=10&orderby=time`
- **Display:** Recent significant earthquakes — magnitude, location, depth, time ago
- **Buttons:** Yellow/Blue = paginate, Green = refresh
- **Tags:** `content`, `network`, `science`

### 7. Dog of the Day
- **API:** [Dog CEO](https://dog.ceo/dog-api/) — `https://dog.ceo/api/breeds/image/random`
- **Display:** Random dog image via `display_image()` + breed name
- **Buttons:** Green = new dog
- **Tags:** `novelty`, `network`
- **Notes:** Tests `display_image()` with URL — verify this works first

### ⭐ 8. Crypto Ticker ✅ IMPLEMENTED (`crypto_ticker`, switch `161`)
- **API:** [CoinGecko](https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=gbp,usd&include_24hr_change=true)
- **Display:** BTC/ETH/SOL prices in GBP with 24h % change, colour-coded up/down
- **Buttons:** Yellow/Blue = cycle coins, Green = refresh
- **Config:** `coins: ["bitcoin", "ethereum", "solana"]`, `vs_currency: "gbp"`
- **Tags:** `content`, `network`

### 9. Air Quality Index ✅ IMPLEMENTED (`air_quality_index`, switch `162`)
- **API:** [Open-Meteo AQI](https://air-quality-api.open-meteo.com/v1/air-quality) — uses existing lat/lon
- **Display:** AQI, PM2.5, PM10, NO₂ with health recommendation text
- **Buttons:** Green = refresh
- **Tags:** `content`, `network`, `science`
- **Notes:** Pairs naturally with existing `current_weather` (same API family)

### 10. UV Index ✅ IMPLEMENTED (`uv_index`, switch `163`)
- **API:** [Open-Meteo](https://api.open-meteo.com/v1/forecast?hourly=uv_index) — uses existing lat/lon
- **Display:** Current UV index with colour-coded severity bar (`display_html()`) + sun protection advice
- **Buttons:** Green = refresh
- **Tags:** `content`, `network`

### 11. Cocktail of the Day ✅ IMPLEMENTED (`cocktail_of_the_day`, switch `164`)
- **API:** [TheCocktailDB](https://www.thecocktaildb.com/api/json/v1/1/random.php)
- **Display:** Drink name, glass type, ingredient list with measures. Paginate if long.
- **Buttons:** Yellow/Blue = paginate ingredients, Green = new cocktail
- **Tags:** `novelty`, `network`

### 12. Meal Idea ✅ IMPLEMENTED (`meal_idea`, switch `165`)
- **API:** [TheMealDB](https://www.themealdb.com/api/json/v1/1/random.php)
- **Display:** Meal name, category, origin, ingredients list
- **Buttons:** Yellow/Blue = paginate, Green = new meal
- **Tags:** `novelty`, `network`

---

## Simple Games (3-button interaction)

### ⭐ 13. Trivia Quiz ✅ IMPLEMENTED (`trivia_quiz`, switch `166`)
- **API:** [Open Trivia DB](https://opentdb.com/api.php?amount=1&type=multiple)
- **Mechanic:** Show question + 3 answer choices (one correct, two wrong — drop one distractor from the 4 returned). Map to Yellow/Green/Blue. Randomize correct answer position each round.
- **Display:** Question text, three labelled options, running score `(correct/total)`
- **Buttons:** Yellow = option A, Green = option B, Blue = option C
- **Config:** `category` (any/science/history/etc.), `difficulty` (easy/medium/hard)
- **Tags:** `game`, `network`
- **Notes:** Highest engagement potential. Decode HTML entities from API response.

### ⭐ 14. Reaction Timer
- **Mechanic:** Random LED lights up after random delay (1–5s). Player presses matching button ASAP. Show reaction time in ms. Wrong button = penalty. Track best time across session.
- **Display:** "Wait…" → LED flash → reaction time in ms → best/avg stats
- **Buttons:** Yellow/Green/Blue = respond to matching LED
- **Tags:** `game`
- **Notes:** No network needed. Leverages LED hardware uniquely. Pure fun.

### ⭐ 15. Simon Says
- **Mechanic:** System plays a sequence of LED flashes (growing each round). Player repeats the sequence using buttons. One wrong = game over. Track high score.
- **Display:** "Watch…" during playback, "Your turn (3/5)" during input, score on game over
- **Buttons:** Yellow/Green/Blue = repeat sequence
- **Tags:** `game`
- **Notes:** No network. Best use of the LED hardware. Classic game everyone knows.

### 16. Number Guess ✅ IMPLEMENTED (`number_guess`, switch `167`)
- **Mechanic:** System picks 1–100. Player uses binary search. Yellow = "my guess is lower," Blue = "my guess is higher," Green = "I think it's [current midpoint]." Track attempts vs optimal (7).
- **Display:** Range `[lo–hi]`, current guess, attempt count
- **Buttons:** Yellow = lower, Green = guess, Blue = higher
- **Tags:** `game`

### 17. Rock Paper Scissors ✅ IMPLEMENTED (`rock_paper_scissors`, switch `168`)
- **Mechanic:** Yellow = Rock, Green = Paper, Blue = Scissors. Best-of-5 vs random. Show choice + result + running score.
- **Display:** Player choice vs computer choice, W/L/D, series score
- **Buttons:** Yellow = Rock, Green = Paper, Blue = Scissors
- **Tags:** `game`

### 18. Math Challenge ✅ IMPLEMENTED (`math_challenge`, switch `169`)
- **Mechanic:** Random arithmetic (addition/multiplication/subtraction). Three answer options mapped to Y/G/B. Difficulty increases with streak. Timer adds pressure.
- **Display:** Problem, three choices, score, streak count
- **Buttons:** Yellow/Green/Blue = pick answer
- **Config:** `operations: ["+", "-", "*"]`, `max_number: 100`
- **Tags:** `game`

### 19. Coin Flip Streak ✅ IMPLEMENTED (`coin_flip_streak`, switch `170`)
- **Mechanic:** Guess heads (Yellow) or tails (Blue) before flip. Green = flip. Track longest correct streak. Simple but addictive.
- **Display:** Coin result (heads/tails emoji), current streak, best streak
- **Buttons:** Yellow = heads, Blue = tails, Green = flip
- **Tags:** `game`

---

## Offline / Utility

### 20. Pomodoro Timer ✅ IMPLEMENTED (`pomodoro_timer`, switch `171`)
- **Mechanic:** 25-min work → 5-min break → repeat. Show countdown on screen.
- **Buttons:** Green = start/pause, Yellow = short break (5m), Blue = long break (15m)
- **Display:** Large countdown timer, session count, current phase
- **Tags:** `utility`
- **Notes:** No network. Practical productivity tool.

### 21. Countdown to Event ✅ IMPLEMENTED (`countdown_to_event`, switch `172`)
- **Mechanic:** Configurable target date. Shows days/hours/minutes remaining.
- **Config:** `event_name: "Christmas"`, `target_date: "2026-12-25"`
- **Display:** Large countdown numbers + event name
- **Buttons:** Green = refresh display
- **Tags:** `utility`

---

## Implementation Priority

| Priority | App | Reason |
|----------|-----|--------|
| P0 | Trivia Quiz (#13) | Highest engagement, tests game pattern, free API |
| P0 | Reaction Timer (#14) | No network, unique LED use, instant fun |
| P0 | Simon Says (#15) | No network, best hardware showcase |
| P1 | ISS Tracker (#1) | Unique content, dead-simple API |
| P1 | Currency Exchange (#2) | Daily utility, reliable free API |
| P1 | Sunrise/Sunset (#4) | Complements weather/moon/constellation cluster |
| P2 | Crypto Ticker (#8) | Popular interest, good API |
| P2 | Rock Paper Scissors (#17) | Simple game, quick to build |
| P2 | Math Challenge (#18) | Educational, no network |
| P3 | Everything else | Nice-to-have, build on demand |

## Switch Mappings (proposed / assigned)

Available switch values (still unused, after assigning 155–172): 2–4, 10–15, 33–73, 76–154, 173–230, 232–243, 245–251, 253.

| Switch | App |
|--------|-----|
| 166 | `trivia_quiz` ✅ assigned |
| 34 | `reaction_timer` |
| 35 | `simon_says` |
| 155 | `iss_tracker` ✅ assigned |
| 156 | `currency_exchange` ✅ assigned |
| 157 | `wikipedia_random_article` ✅ assigned |
| 158 | `sunrise_sunset` ✅ assigned |
| 159 | `country_fact` ✅ assigned |
| 160 | `earthquake_monitor` ✅ assigned |
| 161 | `crypto_ticker` ✅ assigned |
| 162 | `air_quality_index` ✅ assigned |
| 163 | `uv_index` ✅ assigned |
| 164 | `cocktail_of_the_day` ✅ assigned |
| 165 | `meal_idea` ✅ assigned |
| 167 | `number_guess` ✅ assigned |
| 168 | `rock_paper_scissors` ✅ assigned |
| 169 | `math_challenge` ✅ assigned |
| 170 | `coin_flip_streak` ✅ assigned |
| 171 | `pomodoro_timer` ✅ assigned |
| 172 | `countdown_to_event` ✅ assigned |

## Progress

- ✅ Implemented first three apps from this plan:
	- `iss_tracker` (switch `155`)
	- `currency_exchange` (switch `156`)
	- `wikipedia_random_article` (switch `157`)
- ✅ Implemented next three apps from this plan:
	- `sunrise_sunset` (switch `158`)
	- `country_fact` (switch `159`)
	- `earthquake_monitor` (switch `160`)
- ✅ Implemented apps 8–12 from this plan:
	- `crypto_ticker` (switch `161`)
	- `air_quality_index` (switch `162`)
	- `uv_index` (switch `163`)
	- `cocktail_of_the_day` (switch `164`)
	- `meal_idea` (switch `165`)
- ✅ Implemented apps 13, 16, 17, 18, 19 from this plan:
	- `trivia_quiz` (switch `166`)
	- `number_guess` (switch `167`)
	- `rock_paper_scissors` (switch `168`)
	- `math_challenge` (switch `169`)
	- `coin_flip_streak` (switch `170`)
- ✅ Implemented utility apps from this plan:
	- `pomodoro_timer` (switch `171`)
	- `countdown_to_event` (switch `172`)
- ✅ Added all eighteen implemented apps to `src/boss/config/app_mappings.json`
- ✅ Added all eighteen implemented apps to smoke-test classification in `tests/unit/apps/test_app_smoke.py`

## Notes

- All free APIs listed have been verified as active (no key required)
- Games should use a common `_lib/game_utils.py` if patterns emerge (score tracking, countdown display)
- `display_image()` with URLs needs verification before Dog of the Day (#7) — may need to download to temp file first
- Open Trivia DB returns HTML entities (`&quot;`, `&#039;`) — must decode with `html.unescape()`
- CoinGecko free tier has rate limits (~10-30 req/min) — use reasonable refresh intervals
