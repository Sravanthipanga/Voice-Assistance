"""Remembering facts, notes, timers and reminders."""

from __future__ import annotations

import re
import threading

from ..brain import Context, pick, skill

_UNITS = {"second": 1, "sec": 1, "minute": 60, "min": 60, "hour": 3600, "hr": 3600}
_NUM_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "forty five": 45,
    "half an": 0.5,
}
_DURATION = r"(?P<amount>\d+(?:\.\d+)?|half an|forty five|[a-z]+)\s*(?P<unit>sec(?:ond)?s?|min(?:ute)?s?|h(?:ou)?rs?)"


def parse_seconds(amount: str, unit: str) -> float:
    n = float(amount) if re.fullmatch(r"\d+(\.\d+)?", amount) else _NUM_WORDS.get(amount.lower())
    if n is None:
        raise ValueError(f"I don't know how long “{amount}” is")
    key = next(k for k in _UNITS if unit.lower().startswith(k[:3]) or unit.lower().startswith(k))
    return n * _UNITS[key]


def _human(seconds: float) -> str:
    for unit, size in (("hour", 3600), ("minute", 60), ("second", 1)):
        if seconds >= size and seconds % size == 0:
            n = int(seconds // size)
            return f"{n} {unit}{'s' if n != 1 else ''}"
    return f"{int(seconds)} seconds"


def _schedule(ctx: Context, seconds: float, message: str) -> None:
    t = threading.Timer(seconds, ctx.notify, args=(message,))
    t.daemon = True
    t.start()
    ctx.extras.setdefault("timers", []).append(t)


@skill("timer", rf"(set (a |an )?)?timer (for )?{_DURATION}", priority=3, help="set a timer")
def timer(ctx: Context, amount: str, unit: str) -> str:
    secs = parse_seconds(amount, unit)
    if not 0 < secs <= 24 * 3600:
        return "Timers can run from one second up to a day."
    _schedule(ctx, secs, pick("Ding ding! Your timer is done.", "Time's up!"))
    return f"Timer set for {_human(secs)}. I'll shout when it's done."


@skill(
    "remind",
    rf"remind me (in|after) {_DURATION} (to |that |about )?(?P<what>.+)",
    priority=4,
    help="remind you, like “remind me in 10 minutes to stretch”",
)
def remind(ctx: Context, amount: str, unit: str, what: str) -> str:
    secs = parse_seconds(amount, unit)
    _schedule(ctx, secs, f"Reminder: {what}.")
    return f"Okay, I'll remind you to {what} in {_human(secs)}."


@skill(
    "remember",
    r"remember (that )?(?P<key>[a-z0-9' ]+?) (is|are|was) (?P<value>.+)",
    priority=3,
    help="remember facts, like “remember that my locker code is 4512”",
)
def remember(ctx: Context, key: str, value: str) -> str:
    key = re.sub(r"^(my|the)\s+", "", key)
    ctx.memory.remember(key, value)
    return pick(f"Got it. Your {key} is {value}.", f"Saved! I'll remember your {key}.")


@skill(
    "recall",
    r"what('s| is| are) my (?P<key>[a-z0-9' ]+)$",
    r"(do you remember|what do you know about) (my |the )?(?P<key>[a-z0-9' ]+)$",
    priority=2,
)
def recall(ctx: Context, key: str) -> str | None:
    value = ctx.memory.recall(key) if ctx.memory else None
    if value:
        return f"Your {key} is {value}."
    if key in ("name",):
        return None
    return f"I don't have anything saved about your {key}. Say “remember that my {key} is …”."


@skill("memories", r"what do you remember|list (my |your )?memor", priority=3)
def memories(ctx: Context) -> str:
    facts = ctx.memory.facts()
    if not facts:
        return "My memory is a blank page so far."
    return "Here's what I remember: " + "; ".join(f"your {k} is {v}" for k, v in facts.items()) + "."


@skill("forget", r"forget (about )?(my |the )?(?P<key>[a-z0-9' ]+)$", priority=3)
def forget(ctx: Context, key: str) -> str:
    return f"Forgotten: {key}." if ctx.memory.forget(key) else f"I wasn't remembering anything about {key}."


@skill(
    "note",
    r"(take|make|add|write) (a )?note:?\s*(that )?(?P<note>.+)",
    r"note (that|down) (?P<note>.+)",
    priority=3,
    help="take notes",
)
def note(ctx: Context, note: str) -> str:
    n = ctx.memory.add_note(note)
    return f"Noted. You have {n} note{'s' if n != 1 else ''}."


@skill("read notes", r"(read|show|list|what are) (me )?my notes", priority=4)
def read_notes(ctx: Context) -> str:
    notes = ctx.memory.notes()
    if not notes:
        return "You don't have any notes yet."
    return "Your notes: " + " ".join(f"{i}. {n}." for i, n in enumerate(notes, 1))


@skill("clear notes", r"(clear|delete|erase) (all )?(my )?notes", priority=4)
def clear_notes(ctx: Context) -> str:
    n = ctx.memory.clear_notes()
    return f"Cleared {n} note{'s' if n != 1 else ''}."
