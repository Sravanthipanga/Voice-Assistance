"""Command-line entry point: ``python -m sravs``."""

from __future__ import annotations

import argparse
import re
import sys

from . import (
    __version__,
    skills,  # noqa: F401  (registers skills)
)
from .brain import Brain, Context, pick
from .skills.core import greeting
from .storage import Memory
from .voice import Inbox, Listener, Speaker

EXIT = re.compile(r"\b(goodbye|bye|exit|quit|stop listening|shut down|see you)\b", re.IGNORECASE)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sravs", description="Sravs, a friendly voice assistant.")
    p.add_argument("--text", action="store_true", help="type instead of speaking")
    p.add_argument("--mute", action="store_true", help="print replies instead of speaking them")
    p.add_argument("--wake", action="store_true", help='only respond after the wake word ("hey sravs")')
    p.add_argument("--name", default="Sravs", help="what the assistant calls itself")
    p.add_argument("--rate", type=int, default=180, help="speaking speed (words per minute)")
    p.add_argument("--voice", help="part of a system voice name, e.g. 'zira' or 'female'")
    p.add_argument("--lang", default="en-US", help="speech recognition language, e.g. en-IN")
    p.add_argument("--memory", help="path to the memory file (default ~/.sravs/memory.json)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    memory = Memory(args.memory)
    inbox = Inbox()
    ctx = Context(assistant_name=args.name, user_name=memory.get_profile("name"), memory=memory, notify=inbox.put)
    brain = Brain(ctx)
    speaker = Speaker(enabled=not args.mute, rate=args.rate, voice=args.voice)
    listener = Listener(use_mic=not args.text, language=args.lang)
    if not listener.voice:
        # Typing blocks the loop, so show timer alerts the moment they fire.
        def notify(message: str) -> None:
            print(f"\n⏰ {args.name}: {message}\nYou: ", end="", flush=True)

        ctx.notify = notify
    wake = re.compile(rf"\b(hey|hi|ok|okay)?\s*{re.escape(args.name)}\b[,!]?", re.IGNORECASE)

    speaker.say(greeting(ctx) + (f" Say “hey {args.name}” to wake me." if args.wake else ""), args.name)
    misses = 0
    try:
        while True:
            for message in inbox.drain():
                speaker.say(message, args.name)
            heard = listener.listen()
            if heard is None:  # silence
                continue
            if heard == "":
                misses += 1
                if misses % 2 == 1:
                    speaker.say(pick("Sorry, I didn't catch that.", "Could you say that again?"), args.name)
                continue
            misses = 0
            if args.wake:
                m = wake.search(heard)
                if not m:
                    continue
                heard = heard[m.end() :].strip() or "hello"
            if EXIT.search(heard):
                speaker.say(pick("Goodbye! Talk soon.", "See you later!", "Bye! Have a great day."), args.name)
                return 0
            speaker.say(brain.respond(heard), args.name)
    except KeyboardInterrupt:
        print()
        speaker.say("Bye for now!", args.name)
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
