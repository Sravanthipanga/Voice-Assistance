"""Skills that reach the internet: weather, Wikipedia, web search, websites.

All network access goes through ``fetch`` and ``open_url`` so they are easy to
stub in tests and to disable with ``SRAVS_OFFLINE=1``.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import webbrowser

from ..brain import Context, pick, skill

USER_AGENT = "Sravs-Voice-Assistant/2.0 (https://github.com/Sravanthipanga/Voice-Assistance)"

SITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "linkedin": "https://www.linkedin.com",
    "gmail": "https://mail.google.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "maps": "https://maps.google.com",
    "spotify": "https://open.spotify.com",
}


class Offline(RuntimeError):
    pass


def fetch(url: str, timeout: float = 6.0) -> str:
    if os.environ.get("SRAVS_OFFLINE"):
        raise Offline("offline mode is on")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https hosts only
        return resp.read().decode("utf-8", "replace")


def open_url(url: str) -> bool:
    return webbrowser.open(url, new=2)


def _q(text: str) -> str:
    return urllib.parse.quote_plus(text)


@skill(
    "weather",
    r"weather( like)?( in| for| at)? ?(?P<city>[a-z .'\-]+)?$",
    r"(is it|will it) (rain|snow|hot|cold)( in (?P<city>[a-z .'\-]+))?",
    keywords=("weather",),
    priority=3,
    help="check the weather",
)
def weather(ctx: Context, city: str = "") -> str:
    city = re.sub(r"^(today|now|outside)$", "", city.strip())
    try:
        line = fetch(
            f"https://wttr.in/{urllib.parse.quote(city)}?format=%l:+%C,+%t,+feels+like+%f,+humidity+%h"
        ).strip()
    except Exception:
        return "I can't reach the weather service right now. Check your internet connection."
    if not line or "Unknown location" in line or line.lower().startswith("<"):
        return f"I couldn't find the weather for {city or 'your location'}."
    return pick(f"Here's the weather. {line}.", f"Right now in {line}.")


@skill(
    "wikipedia",
    r"^(who|what) (is|was|are|were) (?P<topic>(?!the time|the date|my )[a-z0-9 .,'\-]+)$",
    r"(tell me about|wiki(pedia)?|look up) (?P<topic>[a-z0-9 .,'\-]+)$",
    priority=1,
    help="look things up on Wikipedia",
)
def wikipedia(ctx: Context, topic: str) -> str:
    topic = re.sub(r"^(a|an|the)\s+", "", topic.strip(" ."))
    try:
        data = json.loads(
            fetch("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(topic.replace(" ", "_")))
        )
    except Exception:
        return f"I couldn't look up {topic}. Want me to search the web for it instead?"
    extract = data.get("extract") or ""
    if not extract or data.get("type") == "disambiguation":
        return f"“{topic}” could mean a few things. Try being more specific."
    sentences = re.split(r"(?<=[.!?])\s+", extract)
    return " ".join(sentences[:2])


@skill("search", r"(search|google)( the web)?( for)? (?P<query>.+)", priority=2, help="search the web")
def search(ctx: Context, query: str) -> str:
    open_url(f"https://www.google.com/search?q={_q(query)}")
    return f"Searching the web for {query}."


@skill("play", r"play (?P<query>.+?)( on youtube)?$", priority=2, help="play something on YouTube")
def play(ctx: Context, query: str) -> str:
    open_url(f"https://www.youtube.com/results?search_query={_q(query)}")
    return pick(f"Playing {query} on YouTube.", f"Queueing up {query}. Enjoy!")


@skill("open", r"(open|launch|go to) (?P<site>[a-z .]+)$", priority=2, help="open websites like YouTube or GitHub")
def open_site(ctx: Context, site: str) -> str:
    site = site.lower().strip()
    url = SITES.get(site)
    if url is None and re.fullmatch(r"[a-z0-9\-]+\.[a-z.]{2,}", site.replace(" dot ", ".")):
        url = "https://" + site.replace(" dot ", ".")
    if url is None:
        return f"I don't know a website called {site}. Try “search for {site}”."
    open_url(url)
    return f"Opening {site}."
