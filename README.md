# ✈️ AI-Powered Travel Planner (Multi-Agent)

A Streamlit app where three AI agents work together to plan a trip: real-time flights, hotels and restaurants, a day-by-day itinerary, destination insights, and a packing and preparation list.

**Live app:** <PASTE YOUR STREAMLIT CLOUD LINK HERE>

## Features

- **Flight Finder**: fetches live Google Flights data through SerpAPI, sorts it by price, and shows the 3 cheapest flights with booking links
- **Multi-agent design** (built with `agno.agent` and Gemini):
  - **Researcher Agent**: attractions, culture, safety, weather, visa and insurance guidance (Gemini + SerpAPI search)
  - **Hotel & Restaurant Finder Agent**: top-rated hotels (respecting your minimum star rating) and restaurants
  - **Planner Agent**: combines everything into a daily itinerary with timings, estimated costs vs your budget, a packing list, and preparation tips
- **Travel preparation sidebar**: budget and currency, flight class, hotel rating, visa and insurance toggles, packing checklist categories
- **Personalization**: travel theme (couple, family, adventure...), preferred activities, dates, and number of travelers
- Downloadable plan (`.md`)

## How it works (step by step)

1. You enter origin, destination (with IATA airport codes), dates, theme, activities and preferences.
2. The app calls **SerpAPI's Google Flights** engine, sorts the results by price and shows the 3 cheapest options with a booking link.
3. The **Researcher Agent** searches the web for attractions, culture, safety, weather, and visa/insurance info.
4. The **Hotel & Restaurant Finder Agent** searches for places that match your budget and rating.
5. The **Planner Agent** receives the flight data, research, and place picks, then writes the full itinerary, cost summary, packing list, and preparation tips.
6. Results appear in tabs: Flights, Itinerary & packing, Hotels & restaurants, Insights.

## Tech stack

| Component | Technology |
|---|---|
| UI framework | Streamlit |
| AI agents | `agno.agent` with Gemini models |
| Data source | Google Flights via SerpAPI |
| Styling | HTML/CSS inside Streamlit |
| Date formatting | Python `datetime` |
| Deployment | Streamlit Cloud |

Built with plain Python and Streamlit (no Django, Flask, or LangChain).

## API keys required

| Key | Used for | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | Agent reasoning and writing | https://aistudio.google.com/app/apikey |
| `SERPAPI_API_KEY` | Flights and web search | https://serpapi.com/manage-api-key (free plan available) |

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Paste the keys into the sidebar, or set them as environment variables.

## Deploy on Streamlit Cloud

1. Upload `app.py`, `requirements.txt`, and `README.md` to a public GitHub repo.
2. On https://share.streamlit.io click **Create app**, pick the repo, branch `main`, file `app.py`.
3. Under **Advanced settings → Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   SERPAPI_API_KEY = "your-serpapi-key"
   ```
4. Click **Deploy**.

## Example

**Input:** Delhi (DEL) to Goa (GOI), 6 nights, couple, beach + food tours, budget USD 2000, 4-star hotels.

**Output (shortened):**

```
Flights: top 3 cheapest round-trip options with prices and booking links
Day 1: Arrival, check-in, sunset at the beach, dinner at a local seafood place
Day 2: ...
Cost summary: flights, hotel, food, activities vs your budget
Packing list: clothes, medicine, documents...
```

> Replace this with a real output or screenshot from your own run.

## Disclaimer

AI-generated plans can contain mistakes. Verify visa rules, prices, opening hours, and safety advice before you travel.
