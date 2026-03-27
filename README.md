# weather

Simple weather report with clothing recommendations.  

Gets current weather and 12-hour forecast data (in 3-hour intervals) from openweathermap.org and uses a local LLM (via ollama) to generate a spoken-style briefing.

**Usage:**
```bash
weather [city] [country]
```

Both arguments are optional and default to the values set in `.env`.

**Example:**
```bash
$ weather Berlin DE
Condition: It's a mild, partly cloudy afternoon at 7°C, but it feels much cooler at just 5°C due to the breeze.
Recommendation: Opt for a medium jacket or fleece and regular trousers; you might find it slightly chilly without a light layer underneath.
Outlook: As we move into evening, temperatures will drop to around 6°C, so consider packing an extra layer if plans extend past sunset.
```

**Setup:**

1. Clone this repository
2. Get a free API key from [OpenWeather](https://openweathermap.org/)
3. Save your API key in a `.env` file in the project root (see below)
4. Install `ollama` ([instruction](https://github.com/ollama/ollama?tab=readme-ov-file#download))
5. Pull a model (e.g., `ollama pull qwen2.5:7b`)
6. Install `uv` ([instruction](https://docs.astral.sh/uv/getting-started/installation/))
7. `uv sync`
8. `uv tool install --editable .` (so you can call `weather` from anywhere)

**`.env`**

This file contains general setup like your OpenWeather API key, your preferred LLM and default location.

I'm currently running `qwen2.5:7b` on my M4 Pro. It takes a couple of seconds to run and its output is good.

It could look like this:

```bash
DEFAULT_CITY=Berlin
DEFAULT_COUNTRY=DE
OPENWEATHER_API_KEY=12345...
LLM_MODEL=qwen2.5:7b
```