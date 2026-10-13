# Sravs — Voice Assistant 🎙️

**Sravs** is a friendly voice assistant written in Python. Talk to it, or type to it, and it can tell the time, do maths, check the weather, look things up on Wikipedia, open websites, play music on YouTube, set timers and reminders, take notes, and remember facts about you between sessions.

It's a full rewrite of my original ChatterBot script. ChatterBot is no longer maintained and doesn't install on modern Python, so Sravs now uses its own small, fast intent engine and has no required dependencies.

```text
Sravs: Good evening, Sravanthi! I'm Sravs. What shall we do?
You:   what's the weather like in Chicago
Sravs: Right now in Chicago: Partly cloudy, +18°C, feels like +17°C, humidity 52%.
You:   remind me in 10 minutes to stretch
Sravs: Okay, I'll remind you to stretch in 10 minutes.
You:   what is 15 percent of 80
Sravs: 15 percent of 80 is 12.
```

## Features

| | Try saying |
|---|---|
| 🕒 Time & date | “what time is it”, “what's the date today” |
| 🧮 Safe calculator | “what is 12 times 7”, “2 to the power of 10”, “15 percent of 80” |
| 🌦️ Weather (no API key) | “what's the weather in Hyderabad”, “will it rain” |
| 📚 Wikipedia | “who is Ada Lovelace”, “tell me about black holes” |
| 🔎 Web & music | “search for pasta recipes”, “open GitHub”, “play lofi beats on YouTube” |
| ⏲️ Timers & reminders | “set a timer for 5 minutes”, “remind me in half an hour to drink water” |
| 🧠 Long-term memory | “my name is Sravanthi”, “remember that my locker code is 4512”, “what is my locker code”, “what do you remember”, “forget my locker code” |
| 📝 Notes | “take a note buy milk”, “read my notes”, “clear my notes” |
| 🎲 Fun | jokes, fun facts, “flip a coin”, “roll a 20 sided dice”, “spell necessary”, “motivate me” |
| 💬 Small talk | “how are you”, “who are you”, “thank you”, “say that again”, “help” |

Other things it handles:
- **Optional wake word:** run with `--wake` and Sravs only answers after “hey Sravs …”.
- **Forgiving matching:** slightly misheard words still work, so “wether” finds the weather.
- **Varied replies:** Sravs picks from several phrasings so it doesn't sound like a recording, and greets you by name with the right time of day.
- **Graceful fallbacks:** with no microphone it switches to typing, and with no speech engine it prints its replies. It works offline too (`SRAVS_OFFLINE=1`), with only the web skills politely declining.
- **Robust:** if a skill fails, Sravs apologises and keeps running instead of crashing.

## Quick start

```bash
git clone https://github.com/Sravanthipanga/Voice-Assistance.git
cd Voice-Assistance
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[voice]"     # speech packages (or: pip install -r requirements.txt)
sravs                         # talk to it
sravs --text                  # type instead of speaking
```

You can also run it without installing it as a package: `python -m sravs --text`.

**Microphone setup:**
- **Windows:** `pip install pyaudio` usually just works.
- **macOS:** `brew install portaudio && pip install pyaudio`.
- **Linux:** `sudo apt install portaudio19-dev espeak-ng && pip install pyaudio`.

Speech recognition uses Google's free web recogniser, so it needs an internet connection. Speaking (pyttsx3) runs fully offline.

### Options

| Flag | What it does |
|---|---|
| `--text` | Type instead of speaking into the microphone |
| `--mute` | Print replies instead of speaking them |
| `--wake` | Only respond after “hey Sravs” |
| `--name Jarvis` | Rename the assistant (the wake word changes too) |
| `--rate 160` | Speaking speed in words per minute |
| `--voice zira` | Choose a system voice by part of its name |
| `--lang en-IN` | Recognition language/accent |
| `--memory path.json` | Where to keep memories (default `~/.sravs/memory.json`) |

## Project layout

```
sravs/
  brain.py        intent engine: @skill registry, regex + fuzzy matching, Context
  storage.py      JSON memory (atomic writes, thread-safe)
  voice.py        Speaker (pyttsx3) / Listener (SpeechRecognition) with fallbacks
  __main__.py     CLI loop, wake word, timer alerts
  skills/
    core.py       greetings, time, date, safe calculator, jokes, facts, dice…
    memory.py     remember/recall/forget, notes, timers, reminders
    web.py        weather (wttr.in), Wikipedia, search, websites, YouTube
tests/            48 tests covering routing, every skill and the CLI
```

### Adding a skill

```python
from sravs.brain import Context, skill


@skill("flip table", r"flip (the )?table", keywords=("table",), priority=1)
def flip_table(ctx: Context) -> str:
    return "(╯°□°)╯︵ ┻━┻"
```

Put it in any module inside `sravs/skills/` and import that module from `sravs/skills/__init__.py`. Named regex groups such as `(?P<city>…)` are passed to the function as keyword arguments.

## Development

```bash
pip install -e ".[dev]"
pytest -q          # 48 tests, no microphone or internet needed
ruff check .
```

GitHub Actions runs the linter and tests on Python 3.9, 3.12 and 3.13 for every push.
