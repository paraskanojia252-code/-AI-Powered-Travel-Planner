import os
import time
from datetime import date, timedelta
from urllib.parse import quote_plus

import requests
import streamlit as st
from agno.agent import Agent
from agno.models.google import Gemini
from dotenv import load_dotenv

load_dotenv()  # loads GEMINI_API_KEY and SERPAPI_API_KEY from a local .env file (local runs)

st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="wide")

DEFAULT_MODEL = "gemini-3.8-flash"
FLIGHT_CLASSES = {"Economy": 1, "Premium Economy": 2, "Business": 3, "First": 4}

# ---------------- Styling (HTML/CSS) ----------------
st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #0f4c81 0%, #1b9aaa 100%);
        padding: 28px 32px; border-radius: 16px; color: white; margin-bottom: 18px;
    }
    .hero h1 { margin: 0; font-size: 2rem; }
    .hero p { margin: 6px 0 0 0; opacity: 0.92; }
    .flight-card {
        border: 1px solid rgba(128,128,128,0.35); border-radius: 14px;
        padding: 16px 18px; margin-bottom: 12px;
    }
    .flight-top { display: flex; justify-content: space-between; align-items: center; }
    .flight-airline { font-weight: 700; font-size: 1.05rem; }
    .flight-price { font-weight: 800; font-size: 1.3rem; color: #1b9aaa; }
    .flight-meta { opacity: 0.8; font-size: 0.9rem; margin-top: 6px; }
    .flight-link a {
        display: inline-block; margin-top: 10px; padding: 6px 14px; border-radius: 8px;
        background: #0f4c81; color: white !important; text-decoration: none; font-size: 0.9rem;
    }
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.78rem;
        background: rgba(27,154,170,0.18); margin-right: 6px;
    }
    </style>
    <div class="hero">
        <h1>✈️ AI-Powered Travel Planner</h1>
        <p>A Researcher, a Hotel &amp; Restaurant Finder and a Planner agent work together on your trip.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------- Keys ----------------
def get_key(name: str) -> str:
    """Streamlit secrets (cloud) -> environment variable -> empty (sidebar input)."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, "")


# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("🔑 API keys")
    gemini_key = get_key("GEMINI_API_KEY") or st.text_input("Gemini API key", type="password")
    serp_key = get_key("SERPAPI_API_KEY") or st.text_input("SerpAPI key", type="password")
    model_id = st.text_input("Gemini model", value=DEFAULT_MODEL)
    low_quota = st.toggle(
        "Low-quota mode",
        value=False,
        help="Skips the web searches, so plans use fewer SerpAPI and Gemini requests (less current info).",
    )

    st.header("💰 Budget & comfort")
    currency = st.selectbox("Currency", ["USD", "INR", "EUR", "GBP", "AED"], index=0)
    budget = st.number_input(
        f"Total budget ({currency})", min_value=100, value=2000, step=100
    )
    flight_class = st.selectbox("Flight class", list(FLIGHT_CLASSES))
    hotel_rating = st.select_slider("Minimum hotel rating (stars)", options=[3, 4, 5], value=4)

    st.header("🛂 Essentials")
    need_visa = st.toggle("Include visa guidance", value=True)
    need_insurance = st.toggle("Include travel insurance advice", value=True)

    st.header("🎒 Packing checklist")
    packing = st.multiselect(
        "Categories to cover",
        ["Clothes", "Medicine & first aid", "Electronics", "Documents", "Toiletries", "Travel accessories"],
        default=["Clothes", "Medicine & first aid", "Documents"],
    )

# ---------------- Trip form ----------------
st.subheader("🧭 Tell us about your trip")
c1, c2 = st.columns(2)
with c1:
    origin_city = st.text_input("From (city)", placeholder="e.g. Delhi")
    origin_code = st.text_input("From airport code (IATA)", placeholder="e.g. DEL", max_chars=3)
with c2:
    dest_city = st.text_input("To (city)", placeholder="e.g. Goa")
    dest_code = st.text_input("To airport code (IATA)", placeholder="e.g. GOI", max_chars=3)

c3, c4, c5 = st.columns(3)
with c3:
    depart_date = st.date_input("Departure date", value=date.today() + timedelta(days=30), min_value=date.today())
with c4:
    return_date = st.date_input("Return date", value=date.today() + timedelta(days=36), min_value=date.today())
with c5:
    travelers = st.number_input("Travelers", min_value=1, max_value=10, value=2)

c6, c7 = st.columns(2)
with c6:
    theme = st.selectbox("Travel theme", ["Couple", "Family", "Solo", "Friends", "Adventure", "Luxury", "Budget backpacking"])
with c7:
    activities = st.multiselect(
        "Preferred activities",
        ["Beach", "Nightlife", "Culture & history", "Food tours", "Hiking", "Shopping", "Wildlife", "Wellness & spa"],
        default=["Culture & history", "Food tours"],
    )

generate = st.button("✨ Plan my trip", type="primary", use_container_width=True)


# ---------------- Flights (SerpAPI Google Flights) ----------------
def fetch_flights(api_key, dep, arr, out_date, ret_date, cls, adults, cur):
    """Return (top3_flights, google_flights_url, error)."""
    params = {
        "engine": "google_flights",
        "departure_id": dep.upper(),
        "arrival_id": arr.upper(),
        "outbound_date": out_date.isoformat(),
        "return_date": ret_date.isoformat(),
        "type": 1,  # round trip
        "travel_class": FLIGHT_CLASSES[cls],
        "adults": adults,
        "currency": cur,
        "hl": "en",
        "api_key": api_key,
    }
    try:
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=60)
        data = resp.json()
    except Exception as e:
        return [], "", f"Could not reach SerpAPI: {e}"

    if "error" in data:
        return [], "", data["error"]

    options = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    options = [o for o in options if o.get("price")]
    options.sort(key=lambda o: o["price"])

    link = data.get("search_metadata", {}).get("google_flights_url", "")
    if not link:  # fallback: build a Google Flights search link ourselves
        q = f"Flights from {dep.upper()} to {arr.upper()} on {out_date.isoformat()} returning {ret_date.isoformat()}"
        link = f"https://www.google.com/travel/flights?q={quote_plus(q)}"
    return options[:3], link, ""


def fmt_minutes(total: int) -> str:
    return f"{total // 60}h {total % 60}m"


def render_flight(option: dict, link: str, cur: str, rank: int):
    legs = option.get("flights", [])
    airlines = ", ".join(dict.fromkeys(l.get("airline", "") for l in legs if l.get("airline")))
    first, last = legs[0], legs[-1]
    dep_t = first.get("departure_airport", {}).get("time", "")
    arr_t = last.get("arrival_airport", {}).get("time", "")
    stops = len(legs) - 1
    stop_txt = "Non-stop" if stops == 0 else f"{stops} stop{'s' if stops > 1 else ''}"
    duration = fmt_minutes(option["total_duration"]) if option.get("total_duration") else ""
    st.markdown(
        f"""
        <div class="flight-card">
          <div class="flight-top">
            <span class="flight-airline">#{rank} &nbsp;{airlines or 'Airline'}</span>
            <span class="flight-price">{cur} {option['price']:,}</span>
          </div>
          <div class="flight-meta">
            <span class="badge">{stop_txt}</span><span class="badge">{duration}</span><br>
            Departs {dep_t} &rarr; Arrives {arr_t}
          </div>
          <div class="flight-link"><a href="{link}" target="_blank">Book / view on Google Flights</a></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------- Agents ----------------
def build_agents(gemini_api_key: str, model: str):
    def llm():
        return Gemini(id=model, api_key=gemini_api_key)

    researcher = Agent(
        name="Researcher Agent",
        role="Researches destinations",
        model=llm(),
        instructions=[
            "Use the web search results given in the prompt (and your own knowledge where they are missing) to summarize reliable information. Mention source links when available.",
            "Cover: top attractions matching the traveler's activities, local culture and etiquette, "
            "safety (common scams, areas to avoid, emergency numbers), weather for the travel dates, "
            "and local transport tips.",
            "Be concise and factual. Do not invent facts; say when something is uncertain.",
        ],
        markdown=True,
    )

    finder = Agent(
        name="Hotel & Restaurant Finder Agent",
        role="Finds hotels and restaurants",
        model=llm(),
        instructions=[
            "Use the web search results given in the prompt to pick highly rated hotels and restaurants at the destination. Mention listing links when available.",
            "Respect the minimum hotel star rating and the traveler's budget.",
            "Recommend 3 hotels (with area, approximate nightly price, why it fits) and 5 restaurants "
            "(cuisine, price level, signature dish). Include website or listing links if found.",
            "Do not invent places or prices; if unsure, say so.",
        ],
        markdown=True,
    )

    planner = Agent(
        name="Planner Agent",
        role="Builds the itinerary",
        model=llm(),
        instructions=[
            "You are an expert travel planner. Use ONLY the research, hotel/restaurant picks and flight "
            "data provided in the prompt.",
            "Create a day-by-day itinerary with morning, afternoon and evening blocks, approximate "
            "timings, estimated costs and travel time between spots. Group nearby places to save time.",
            "Include a cost summary compared against the budget, a packing list organized by the "
            "requested categories, and a practical preparation checklist.",
            "Be honest about uncertainty and tell the traveler to verify visa, insurance and prices "
            "before booking.",
        ],
        markdown=True,
    )
    return researcher, finder, planner


def serp_search(api_key: str, query: str, n: int = 5) -> str:
    """Run one Google search through SerpAPI and return short text snippets."""
    try:
        resp = requests.get(
            "https://serpapi.com/search.json",
            params={"engine": "google", "q": query, "num": n, "hl": "en", "api_key": api_key},
            timeout=45,
        )
        data = resp.json()
    except Exception as e:
        return f"(search failed: {e})"
    if "error" in data:
        return f"(search error: {data['error']})"
    lines = [
        f"- {r.get('title', '')} | {r.get('snippet', '')} | {r.get('link', '')}"
        for r in (data.get("organic_results") or [])[:n]
    ]
    return "\n".join(lines) or "(no results)"


def run_searches(api_key: str, queries: list) -> str:
    return "\n\n".join(f"### {q}\n{serp_search(api_key, q)}" for q in queries)


def web_block(results: str) -> str:
    if not results:
        return "\n\n=== WEB SEARCH RESULTS ===\nNone (low-quota mode). Use your own knowledge and say it is unverified."
    return f"\n\n=== WEB SEARCH RESULTS ===\n{results}"


def looks_like_api_error(text: str) -> bool:
    """Gemini errors sometimes come back as JSON text instead of raising."""
    t = text.strip()
    if t.startswith("{") and '"error"' in t[:60] and '"code"' in t:
        return True
    return len(t) < 600 and '"arguments"' in t and '"name"' in t  # raw tool-call text


def is_quota_error(text: str) -> bool:
    t = text.lower()
    return "429" in t or "resource_exhausted" in t or "exceeded your current quota" in t


def run_agent(agent: Agent, prompt: str, retries: int = 4) -> str:
    """Run an agent, retrying when Gemini is busy (503) or returns an error payload."""
    waits = [5, 12, 25]
    last_error = ""
    for attempt in range(retries):
        try:
            content = agent.run(prompt).content
            text = content if isinstance(content, str) else str(content or "")
            if text.strip() and not looks_like_api_error(text):
                return text
            last_error = text or "Empty response from the model."
        except Exception as e:
            last_error = str(e)
        if is_quota_error(last_error):
            break  # retrying a quota error only wastes more quota
        if attempt < retries - 1:
            st.write(f"⏳ Gemini is busy, retrying in {waits[attempt]}s...")
            time.sleep(waits[attempt])
    raise RuntimeError(
        ("Gemini quota exceeded (429). Wait a few minutes (or until tomorrow for the daily limit), "
         "use a key from a new project, or turn on low-quota mode in the sidebar. "
         if is_quota_error(last_error) else
         "Gemini is overloaded or returned an error after several tries. "
         "Wait a minute and try again, or switch the model in the sidebar (e.g. gemini-3.7-flash). ")
        + f"Details: {last_error[:300]}"
    )


FALLBACK_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-flash-latest"]


def run_role(role: str, prompt: str, models: list, cache: dict, gem_key: str) -> str:
    """Run one agent role; if a model is overloaded, fall back to the next model."""
    last_error = ""
    for model in list(models):
        try:
            if model not in cache:
                cache[model] = dict(zip(("researcher", "finder", "planner"),
                                        build_agents(gem_key, model)))
            text = run_agent(cache[model][role], prompt, retries=2)
            if models[0] != model:  # remember the model that worked and use it first
                models.remove(model)
                models.insert(0, model)
            return text
        except RuntimeError as e:
            last_error = str(e)
            st.write(f"⚠️ {model} is unavailable right now, trying another model...")
    raise RuntimeError(
        "All Gemini models are overloaded, out of quota, or unavailable right now. "
        "Wait a few minutes and try again, use a key from a new Google project, or turn on "
        f"low-quota mode in the sidebar. Details: {last_error[:300]}"
    )


# ---------------- Main flow ----------------
if generate:
    errors = []
    if not gemini_key or not serp_key:
        errors.append("Please provide both the Gemini and SerpAPI keys in the sidebar.")
    if not origin_city or not dest_city:
        errors.append("Please enter both the origin and destination cities.")
    if len(origin_code) != 3 or len(dest_code) != 3:
        errors.append("Please enter 3-letter IATA airport codes (e.g. DEL, GOI).")
    if return_date <= depart_date:
        errors.append("The return date must be after the departure date.")
    for e in errors:
        st.error(e)
    if errors:
        st.stop()

    days = (return_date - depart_date).days
    trip_summary = (
        f"Trip: {origin_city} ({origin_code.upper()}) to {dest_city} ({dest_code.upper()})\n"
        f"Dates: {depart_date.strftime('%d %b %Y')} to {return_date.strftime('%d %b %Y')} ({days} days)\n"
        f"Travelers: {travelers} | Theme: {theme}\n"
        f"Activities: {', '.join(activities) or 'open to suggestions'}\n"
        f"Total budget: {currency} {budget:,} | Flight class: {flight_class} | Min hotel rating: {hotel_rating} stars\n"
        f"Visa guidance needed: {'yes' if need_visa else 'no'} | Insurance advice needed: {'yes' if need_insurance else 'no'}\n"
        f"Packing categories: {', '.join(packing) or 'general'}"
    )

    try:
        with st.status("Your agents are working...", expanded=True) as status:
            st.write("✈️ Searching Google Flights...")
            flights, flights_link, flight_err = fetch_flights(
                serp_key, origin_code, dest_code, depart_date, return_date,
                flight_class, int(travelers), currency,
            )

            research_web = places_web = ""
            if not low_quota:
                st.write("🔎 Searching the web (SerpAPI) for attractions, safety, hotels and restaurants...")
                month = depart_date.strftime("%B")
                research_queries = [
                    f"top attractions in {dest_city} {' '.join(activities)}",
                    f"{dest_city} travel safety tips scams culture etiquette",
                    f"{dest_city} weather in {month} what to expect",
                ]
                if need_visa:
                    research_queries.append(f"visa requirements for {dest_city} travelers from {origin_city}")
                if need_insurance:
                    research_queries.append(f"travel insurance advice for {dest_city}")
                research_web = run_searches(serp_key, research_queries)
                places_web = run_searches(serp_key, [
                    f"best {hotel_rating} star hotels in {dest_city}",
                    f"best restaurants in {dest_city} {' '.join(activities)}",
                ])

            models = list(dict.fromkeys([model_id.strip()] + FALLBACK_MODELS))
            agent_cache = {}

            st.write("🧠 Researcher Agent is gathering culture, safety and attraction details...")
            research = run_role(
                "researcher",
                f"{trip_summary}\n\nResearch {dest_city}: attractions for these activities, culture and "
                f"etiquette, safety, weather during the dates, local transport."
                + (" Also explain visa requirements for travelers from the origin country." if need_visa else "")
                + (" Also give travel insurance advice for this trip." if need_insurance else "")
                + web_block(research_web),
                models, agent_cache, gemini_key,
            )

            st.write("🏨 Hotel & Restaurant Finder Agent is picking places to stay and eat...")
            places = run_role(
                "finder",
                f"{trip_summary}\n\nFind the best hotels (at least {hotel_rating} stars) and restaurants in {dest_city}."
                + web_block(places_web),
                models, agent_cache, gemini_key,
            )

            st.write("🗺️ Planner Agent is building your itinerary...")
            flight_text = "\n".join(
                f"- {o['price']} {currency}, {len(o.get('flights', [])) - 1} stop(s), "
                f"{', '.join(dict.fromkeys(l.get('airline', '') for l in o.get('flights', [])))}"
                for o in flights
            ) or "No flight data available."
            itinerary = run_role(
                "planner",
                f"{trip_summary}\n\n=== FLIGHT OPTIONS ===\n{flight_text}\n\n=== RESEARCH ===\n{research}"
                f"\n\n=== HOTELS & RESTAURANTS ===\n{places}\n\n"
                f"Write the complete plan: daily itinerary for {days} days, cost summary vs budget, "
                f"packing list, and preparation tips.",
                models, agent_cache, gemini_key,
            )
            status.update(label="Your trip plan is ready!", state="complete", expanded=False)
    except Exception as e:
        st.error(f"Something went wrong: {e}")
        st.stop()

    st.session_state["result"] = {
        "flights": flights, "flights_link": flights_link, "flight_err": flight_err,
        "research": research, "places": places, "itinerary": itinerary,
        "title": f"{origin_city} → {dest_city}", "currency": currency,
    }

res = st.session_state.get("result")
if res:
    st.header(f"🌍 {res['title']}")
    tab_flights, tab_itin, tab_places, tab_research = st.tabs(
        ["✈️ Flights", "🗺️ Itinerary & packing", "🏨 Hotels & restaurants", "📚 Insights"]
    )

    with tab_flights:
        st.subheader("Top 3 cheapest flights")
        if res["flight_err"]:
            st.warning(f"Flight search problem: {res['flight_err']}")
        elif not res["flights"]:
            st.info("No flights found for these dates and airports.")
        else:
            for i, option in enumerate(res["flights"], 1):
                render_flight(option, res["flights_link"], res["currency"], i)
            st.caption("Prices come from Google Flights via SerpAPI and can change. Verify before booking.")

    with tab_itin:
        st.markdown(res["itinerary"])
        st.download_button(
            "Download plan (.md)", res["itinerary"], file_name="travel_plan.md", mime="text/markdown"
        )

    with tab_places:
        st.markdown(res["places"])

    with tab_research:
        st.markdown(res["research"])

    st.caption("AI-generated plan. Always verify visa rules, prices, opening hours and safety advice before you travel.")
else:
    st.info("Fill in your trip details and click **Plan my trip**.")
