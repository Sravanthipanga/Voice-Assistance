"""Intent matching and the skill registry.

Skills register themselves with the ``@skill`` decorator. Each skill owns one
or more regular expressions; named groups become keyword arguments. Matching
is done in a single pass over pre-compiled patterns, ordered by priority, and
falls back to fuzzy keyword matching so slightly misheard phrases still work.
"""

from __future__ import annotations

import difflib
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable

Handler = Callable[..., "str | None"]


@dataclass(frozen=True)
class Skill:
    name: str
    patterns: tuple[re.Pattern[str], ...]
    handler: Handler
    keywords: tuple[str, ...] = ()
    priority: int = 0
    help: str = ""


_REGISTRY: list[Skill] = []


def skill(
    name: str,
    *patterns: str,
    keywords: Iterable[str] = (),
    priority: int = 0,
    help: str = "",
) -> Callable[[Handler], Handler]:
    """Register ``fn`` as a skill triggered by any of ``patterns``."""

    def wrap(fn: Handler) -> Handler:
        compiled = tuple(re.compile(p, re.IGNORECASE) for p in patterns)
        _REGISTRY.append(Skill(name, compiled, fn, tuple(keywords), priority, help))
        _REGISTRY.sort(key=lambda s: -s.priority)
        return fn

    return wrap


def registry() -> list[Skill]:
    return list(_REGISTRY)


def pick(*options: str) -> str:
    """Pick one phrasing at random so Sravs never sounds like a recording."""
    return random.choice(options)


@dataclass
class Context:
    """Shared state handed to every skill."""

    assistant_name: str = "Sravs"
    user_name: str | None = None
    memory: "object | None" = None  # sravs.storage.Memory
    notify: Callable[[str], None] = print
    last_reply: str = ""
    turns: int = 0
    extras: dict = field(default_factory=dict)


_FILLERS = re.compile(r"^(?:hey|hi|ok|okay|please|so|um+|uh+)[,\s]+|[,\s]+please$|[?.!]+$", re.IGNORECASE)


def normalise(text: str) -> str:
    text = text.strip()
    prev = None
    while prev != text:
        prev, text = text, _FILLERS.sub("", text).strip()
    return text


class Brain:
    def __init__(self, ctx: Context, fuzzy_cutoff: float = 0.8):
        self.ctx = ctx
        self.fuzzy_cutoff = fuzzy_cutoff

    def match(self, text: str) -> tuple[Skill, dict[str, str]] | None:
        for s in _REGISTRY:
            for p in s.patterns:
                m = p.search(text)
                if m:
                    return s, {k: v.strip() for k, v in m.groupdict().items() if v}
        # Fuzzy fallback: compare each spoken word with skill keywords.
        words = re.findall(r"[a-z']+", text.lower())
        best: tuple[float, Skill] | None = None
        for s in _REGISTRY:
            for kw in s.keywords:
                for w in words:
                    score = difflib.SequenceMatcher(None, w, kw).ratio()
                    if score >= self.fuzzy_cutoff and (best is None or score > best[0]):
                        best = (score, s)
        return (best[1], {}) if best else None

    def respond(self, raw: str) -> str:
        text = normalise(raw)
        self.ctx.turns += 1
        if not text:
            return pick("I'm listening.", "Go on, I'm all ears.")
        found = self.match(text)
        if found is None:
            return pick(
                f"I didn't catch a command in “{text}”. Say “help” to hear what I can do.",
                f"Hmm, “{text}” is new to me. Try “help”, or ask me to search the web for it.",
            )
        s, kwargs = found
        try:
            reply = s.handler(self.ctx, **kwargs) or ""
        except Exception as exc:  # a broken skill must never crash the assistant
            reply = f"Oops, my {s.name} skill tripped over something: {exc}"
        self.ctx.last_reply = reply
        return reply
