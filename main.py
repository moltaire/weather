import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


API_KEY = os.getenv("OPENWEATHER_API_KEY")
assert API_KEY is not None, "OpenWeather API key not provided."

VERBOSE = os.getenv("VERBOSE", "").lower() in {"1", "true", "yes", "on"}

LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")

DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Berlin")
DEFAULT_COUNTRY = os.getenv("DEFAULT_COUNTRY", "DE")

BASE_URL = "https://api.openweathermap.org"
FORECAST_CNT = 4

SYSTEM_PROMPT = """You are a weather assistant giving a brief spoken-style daily briefing. Use natural, complete sentences — not lists or verbatim guide entries.

Temperature classification:
<5°C → cold | 5–10°C → cool | 10–18°C → mild | 18–25°C → warm | >25°C → hot

Clothing guide (use this strictly):
cold (<5°C):    heavy winter coat + thermal or fleece underlayer, warm trousers
cool (5–10°C):  winter coat + thick sweater, jeans or warm trousers
mild (10–18°C): medium jacket or fleece, regular trousers or jeans
warm (18–25°C): t-shirt or light shirt, regular trousers or jeans; light jacket only if below 22°C
hot (>25°C):    t-shirt, shorts or light trousers

Rules:
- Always round temperatures to the nearest whole number — never write decimal places under any circumstances
- Base the clothing recommendation on the feels-like temperature, not air temperature
- Recommend exactly one outfit — no alternatives
- Do not use vague terms like "layer up", "bundle up", "stay warm", or "dress appropriately"
- Do not reference data field names (like temp_c, feels_like_c) — write in plain language only
- Do not mention the city or country name
- Do not mention shoes
- Express temperatures as specific numbers, not approximations like "mid-9s"
- Use the time field to determine current time of day (morning before 12s:00, afternoon 12:00–17:00, evening after 17:00)
- No empty lines between the three output lines

Output format (exactly 3 lines, no empty lines):
Condition: <one sentence describing the weather, classification, current temp, and feels-like temp>
Recommendation: <one sentence recommending a specific outfit, written naturally>
Outlook: <one sentence on upcoming changes or today's range, with temps>

Example:
Condition: It's a cool, overcast morning at 7°C, though it feels closer to 4°C with the wind.
Recommendation: You'll want a winter coat with a thick sweater underneath, and jeans or warm trousers.
Outlook: Temperatures will drop sharply to around 4°C tonight, so dress for a cold evening if you're heading out late."""


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)


# --- helpers ---


def get(session: requests.Session, url: str, params: dict) -> dict:
    response = session.get(url, params=params)
    response.raise_for_status()
    return response.json()


def build_weather_summary(geocode_data, current_data, forecast_data):
    summary = {
        "location": {
            "city": geocode_data["name"],
            "country": geocode_data["country"],
        },
        "current": {
            "condition": current_data["weather"][0]["description"],
            "temp_c": current_data["main"]["temp"],
            "temp_min_c": current_data["main"]["temp_min"],
            "temp_max_c": current_data["main"]["temp_max"],
            "feels_like_c": current_data["main"]["feels_like"],
            "wind_mps": current_data["wind"]["speed"],
            "time": datetime.fromtimestamp(current_data["dt"]).strftime("%H:%M"),
        },
        "forecast": [],
    }

    for entry in forecast_data["list"][:FORECAST_CNT]:
        summary["forecast"].append(
            {
                "time": entry["dt_txt"],
                "condition": entry["weather"][0]["description"],
                "temp_c": entry["main"]["temp"],
                "temp_min_c": entry["main"]["temp_min"],
                "temp_max_c": entry["main"]["temp_max"],
                "feels_like_c": entry["main"]["feels_like"],
                "wind_mps": entry["wind"]["speed"],
            }
        )

    return summary


def query_ollama(session: requests.Session, summary: dict) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Weather data:\n{json.dumps(summary, indent=2)}\nWrite a report for me.",
            },
        ],
        "stream": False,
        "options": {"num_ctx": 2048, "num_predict": 300},
        "keep_alive": 0,  # unloads model immediately after response
    }

    response = session.post("http://localhost:11434/api/chat", json=payload)
    response.raise_for_status()
    return response.json()["message"]["content"]


# --- main flow ---


def main():
    parser = argparse.ArgumentParser(description="Local weather briefing via LLM.")
    parser.add_argument("city", nargs="?", default=DEFAULT_CITY)
    parser.add_argument("country", nargs="?", default=DEFAULT_COUNTRY)
    args = parser.parse_args()

    with requests.Session() as session:
        # Geocoding
        vprint("Getting geocode...")
        geocode_data = get(
            session,
            f"{BASE_URL}/geo/1.0/direct",
            {"q": f"{args.city},{args.country}", "appid": API_KEY, "limit": 1},
        )[0]
        vprint(json.dumps(geocode_data, indent=2))

        lat, lon = geocode_data["lat"], geocode_data["lon"]

        # Current weather
        vprint("Getting current weather...")
        current_data = get(
            session,
            f"{BASE_URL}/data/2.5/weather",
            {"lat": lat, "lon": lon, "units": "metric", "appid": API_KEY},
        )
        vprint(json.dumps(current_data, indent=2))

        # Forecast
        vprint("Getting forecast...")
        forecast_data = get(
            session,
            f"{BASE_URL}/data/2.5/forecast",
            {
                "lat": lat,
                "lon": lon,
                "units": "metric",
                "appid": API_KEY,
                "cnt": FORECAST_CNT,
            },
        )
        vprint(json.dumps(forecast_data, indent=2))

        # Summary → LLM
        summary = build_weather_summary(geocode_data, current_data, forecast_data)
        vprint(json.dumps(summary, indent=2))

        report = query_ollama(session, summary)
        print(report)


if __name__ == "__main__":
    main()
