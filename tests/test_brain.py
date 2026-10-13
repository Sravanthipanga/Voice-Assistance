import time

import pytest

from sravs.brain import normalise
from sravs.skills import web
from sravs.skills.core import evaluate
from sravs.skills.memory import parse_seconds
from sravs.storage import Memory


def skill_for(brain, text):
    found = brain.match(normalise(text))
    return found[0].name if found else None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("hello", "greet"),
        ("hey sravs what time is it", "time"),
        ("what's the date today", "date"),
        ("what is 12 times 7", "calculate"),
        ("what is your name", "identity"),
        ("what is my name", "get name"),
        ("my name is sravanthi", "set name"),
        ("i'm tired", "motivate"),
        ("tell me a joke please", "joke"),
        ("what's the weather like in chicago", "weather"),
        ("what is the weather", "weather"),
        ("who is ada lovelace", "wikipedia"),
        ("search for python tutorials", "search"),
        ("play lofi beats on youtube", "play"),
        ("open github", "open"),
        ("set a timer for 5 minutes", "timer"),
        ("remind me in 10 minutes to stretch", "remind"),
        ("remember that my locker code is 4512", "remember"),
        ("what is my locker code", "recall"),
        ("take a note buy milk", "note"),
        ("read my notes", "read notes"),
        ("flip a coin", "coin"),
        ("roll a 20 sided dice", "dice"),
        ("what can you do", "help"),
        ("wether", "weather"),  # fuzzy: misheard
        ("jok", "joke"),
    ],
)
def test_routing(brain, text, expected):
    assert skill_for(brain, text) == expected


def test_unknown_is_friendly(brain):
    assert "help" in brain.respond("blorp zing").lower()


@pytest.mark.parametrize(
    "expr, value",
    [
        ("12 times 7", 84),
        ("2 plus 3 * 4", 14),
        ("10 divided by 4", 2.5),
        ("2 ^ 10", 1024),
        ("5 squared", 25),
        ("20 percent of 50", 10),
        ("-3 + 1", -2),
        ("1,000 + 1", 1001),
    ],
)
def test_calculator(expr, value):
    assert evaluate(expr) == value


@pytest.mark.parametrize("bad", ["__import__('os')", "2 ** 1000", "open('x')"])
def test_calculator_is_safe(bad):
    with pytest.raises((ValueError, SyntaxError)):
        evaluate(bad)


def test_divide_by_zero(brain):
    assert "zero" in brain.respond("what is 5 divided by 0")


def test_name_memory(brain, ctx, tmp_path):
    brain.respond("my name is sravanthi")
    assert brain.respond("what's my name") == "You're Sravanthi, of course!"
    assert Memory(tmp_path / "memory.json").get_profile("name") == "Sravanthi"


def test_facts_and_notes(brain):
    brain.respond("remember that my wifi password is sunflower42")
    assert "sunflower42" in brain.respond("what is my wifi password")
    assert "sunflower42" in brain.respond("what do you remember")
    brain.respond("forget my wifi password")
    assert "don't have anything" in brain.respond("what is my wifi password")
    brain.respond("take a note buy milk")
    brain.respond("add a note call mom")
    assert brain.respond("read my notes") == "Your notes: 1. buy milk. 2. call mom."
    assert brain.respond("clear my notes") == "Cleared 2 notes."


def test_parse_seconds():
    assert parse_seconds("5", "minutes") == 300
    assert parse_seconds("two", "hours") == 7200
    assert parse_seconds("half an", "hour") == 1800
    assert parse_seconds("30", "sec") == 30


def test_reminder_fires(brain, ctx):
    assert "remind you to stretch" in brain.respond("remind me in 1 second to stretch")
    time.sleep(1.3)
    assert ctx.notify.messages == ["Reminder: stretch."]


def test_web_actions(brain, opened):
    assert brain.respond("search for best pizza") == "Searching the web for best pizza."
    brain.respond("open youtube")
    brain.respond("play lofi beats on youtube")
    assert opened == [
        "https://www.google.com/search?q=best+pizza",
        "https://www.youtube.com",
        "https://www.youtube.com/results?search_query=lofi+beats",
    ]
    assert "don't know a website" in brain.respond("open narnia")


def test_wikipedia_and_weather(brain, monkeypatch):
    def fake_fetch(url, timeout=6.0):
        if "wikipedia" in url:
            return (
                '{"type":"standard","extract":"Ada Lovelace was a mathematician. She wrote the first program. Third."}'
            )
        return "Chicago: Sunny, +21°C, feels like +20°C, humidity 40%"

    monkeypatch.setattr(web, "fetch", fake_fetch)
    assert brain.respond("who is ada lovelace") == "Ada Lovelace was a mathematician. She wrote the first program."
    assert "Sunny" in brain.respond("weather in chicago")


def test_offline_is_graceful(brain, monkeypatch):
    monkeypatch.setenv("SRAVS_OFFLINE", "1")
    assert "can't reach" in brain.respond("weather in paris")
    assert "couldn't look up" in brain.respond("who is alan turing")


def test_broken_skill_does_not_crash(brain, monkeypatch):
    monkeypatch.setattr(web, "fetch", lambda *a, **k: "not json")
    assert brain.respond("who is someone")  # returns an apology, no exception


def test_cli_text_mode(monkeypatch, tmp_path, capsys):
    from sravs.__main__ import run

    inputs = iter(["my name is ravi", "what is 6 times 7", "bye"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert run(["--text", "--mute", "--memory", str(tmp_path / "m.json")]) == 0
    out = capsys.readouterr().out
    assert "Ravi" in out and "6 times 7 is 42." in out and ("Goodbye" in out or "See you" in out or "Bye" in out)
