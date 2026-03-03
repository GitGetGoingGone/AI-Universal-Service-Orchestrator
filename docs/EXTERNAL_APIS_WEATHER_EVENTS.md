# External APIs: Weather, Events, and External Factors

The orchestrator uses external APIs for weather, events, and web search to enrich composite experiences (date night, picnic, etc.). Configure these in **Platform Config → Integrations → External APIs**.

---

## 1. Weather API

**Purpose:** Suggest optimal dates for outdoor plans based on forecast (e.g., "Wednesday looks best for outdoor plans—clear skies").

**Recommended APIs:**

| API | Free Tier | Setup |
|-----|-----------|-------|
| **OpenWeatherMap** | 1,000 calls/day | [openweathermap.org/api](https://openweathermap.org/api) — Get API key, use `api_type: weather`, `base_url: https://api.openweathermap.org` |
| **WeatherAPI.com** | 1M calls/month | [weatherapi.com](https://www.weatherapi.com/) — Free tier, 3-day forecast |
| **Open-Meteo** | Unlimited (no key) | [open-meteo.com](https://open-meteo.com/) — No API key; use `base_url: https://api.open-meteo.com/v1` with custom params |

**Platform Config:**
- **api_type:** `weather`
- **base_url:** `https://api.openweathermap.org` (or provider URL)
- **api_key:** Your API key (encrypted at rest)
- **extra_config:** `{"units": "imperial"}` for Fahrenheit

**Expected response shape:** Orchestrator expects `temp`, `description`, `location`. OpenWeatherMap `/data/2.5/weather` is compatible by default.

---

## 2. Events API

**Purpose:** Surface concerts, shows, and local happenings when planning experiences (e.g., "Avoid Friday near downtown due to the football game crowd").

**Recommended APIs:**

| API | Free Tier | Setup |
|-----|-----------|-------|
| **Ticketmaster Discovery** | 5,000 calls/day | [developer.ticketmaster.com](https://developer.ticketmaster.com/) — Events, concerts, sports |
| **PredictHQ** | Limited free | [predicthq.com](https://www.predicthq.com/) — Events + demand forecasting |
| **Eventbrite** | Varies | [eventbrite.com/developer](https://www.eventbrite.com/developer/) — Community events |
| **SeatGeek** | 500 req/day | [platform.seatgeek.com](https://platform.seatgeek.com/) — Sports, concerts |

**Platform Config:**
- **api_type:** `events`
- **base_url:** `https://app.ticketmaster.com/discovery/v2`
- **api_key:** Your Ticketmaster API key
- **extra_config:** `{"size": 10}` for limit

**Expected response shape:** Orchestrator expects `_embedded.events` with `name`, `url`, `dates.start.localDate`. Ticketmaster Discovery is compatible by default.

---

## 3. Web Search API (External Factors)

**Purpose:** Multi-day weather outlook, local trends, "date night ideas [city]", and general research when the user gives flexible dates (e.g., "anytime next week").

**Recommended APIs:**

| API | Free Tier | Setup |
|-----|-----------|-------|
| **Serper (Google)** | 2,500 searches/month | [serper.dev](https://serper.dev/) — Fast, JSON API |
| **Tavily** | 1,000/month | [tavily.com](https://tavily.com/) — AI-oriented search |
| **Brave Search** | 2,000/month | [brave.com/search/api](https://brave.com/search/api/) |
| **Bing Web Search** | 1,000/month | [azure.microsoft.com/products/cognitive-services/bing-web-search-api](https://azure.microsoft.com/products/cognitive-services/bing-web-search-api/) |

**Platform Config:**
- **api_type:** `web_search`
- **base_url:** Provider-specific (e.g., `https://google.serper.dev` for Serper)
- **api_key:** Your API key

**Usage:** Planner calls `web_search` with queries like `"weather forecast Dallas next week"` or `"date night ideas San Francisco"`.

---

## 4. External Factors to Consider

When planning composite experiences, the orchestrator considers:

| Factor | Source | Use Case |
|--------|--------|----------|
| **Weather** | Weather API | Outdoor plans, picnics, rooftop dinners — suggest best days |
| **Local events** | Events API | Crowds, traffic, availability — e.g., "Avoid Friday near stadium" |
| **Traffic / transit** | (Future) | Rush hour, closures — timing for limo/dinner |
| **Holidays** | (Future) | Pricing, availability, surge rules |
| **Seasonality** | (Future) | Flower availability, seasonal menus |
| **Budget** | Intent entities | Filter products by `budget_max` |
| **Dietary** | Intent entities | Restaurant filters, allergies |
| **Location** | Intent entities | Weather, events, partner service areas |

---

## 5. Quick Setup (OpenWeatherMap + Ticketmaster)

1. **Weather:** Sign up at [openweathermap.org](https://openweathermap.org/api), get API key. Add External API: `weather`, base_url `https://api.openweathermap.org`, api_key.
2. **Events:** Sign up at [developer.ticketmaster.com](https://developer.ticketmaster.com/), get API key. Add External API: `events`, base_url `https://app.ticketmaster.com/discovery/v2`, api_key.
3. **Web Search (optional):** Sign up at [serper.dev](https://serper.dev/). Add External API: `web_search`, base_url `https://google.serper.dev`, api_key.

After adding, the orchestrator will call these when the user provides a location for date night, picnic, or similar experiences.
