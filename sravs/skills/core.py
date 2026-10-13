"""Everyday skills: small talk, time, maths, games."""

from __future__ import annotations

import ast
import operator
import random
import re
from datetime import datetime

from ..brain import Context, pick, skill

JOKES = (
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break. It said: no problem, I'll go to sleep.",
    "Why did the developer go broke? Because they used up all their cache.",
    "There are 10 kinds of people: those who understand binary and those who don't.",
    "Why was the JavaScript developer sad? Because they didn't Node how to Express themselves.",
    "A SQL query walks into a bar, walks up to two tables and asks: can I join you?",
)

FACTS = (
    "Honey never spoils. Archaeologists have eaten 3,000-year-old honey from Egyptian tombs.",
    "Octopuses have three hearts and blue blood.",
    "The first computer bug was an actual moth, found in a Harvard relay in 1947.",
    "Bananas are berries, but strawberries are not.",
    "A day on Venus is longer than a year on Venus.",
    "The word 'robot' comes from the Czech 'robota', meaning forced labour.",
)

MOTIVATION = (
    "Small steps every day beat giant leaps once a year. Keep going!",
    "You've debugged harder things than today. You've got this.",
    "Done is better than perfect. Ship it, then make it shine.",
    "Every expert was once a beginner who refused to quit.",
)


def _part_of_day(hour: int) -> str:
    return "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"


def greeting(ctx: Context, now: datetime | None = None) -> str:
    now = now or datetime.now()
    name = f", {ctx.user_name}" if ctx.user_name else ""
    return pick(
        f"Good {_part_of_day(now.hour)}{name}! I'm {ctx.assistant_name}. What shall we do?",
        f"Hey{name}! {ctx.assistant_name} here, ready when you are.",
    )


@skill("greet", r"^(hello|hi|hey|good (morning|afternoon|evening)|yo)\b", keywords=("hello",), help="say hello")
def greet(ctx: Context) -> str:
    return greeting(ctx)


@skill("how are you", r"how (are|r) (you|u)|how do (you|u) do|how's it going", priority=1)
def how_are_you(ctx: Context) -> str:
    return pick(
        "Running at full speed and zero bugs, as far as I know. How about you?",
        "I'm great, thanks for asking! What's on your mind?",
        "Fantastic. Every conversation makes me a little smarter.",
    )


@skill("identity", r"who are you|what('s| is) your name|introduce yourself", priority=2)
def identity(ctx: Context) -> str:
    return (
        f"I'm {ctx.assistant_name}, your voice assistant. I can tell the time, do maths, check the weather, "
        "look things up, take notes, set timers and remember things for you."
    )


@skill("set name", r"(my name is|call me) (?P<name>[a-z][a-z \-']{0,30})$", priority=3, help="tell me your name")
def set_name(ctx: Context, name: str) -> str:
    name = name.title()
    ctx.user_name = name
    if ctx.memory is not None:
        ctx.memory.set_profile("name", name)
    return pick(f"Nice to meet you, {name}! I'll remember that.", f"Got it, {name}. Saved to my memory.")


@skill("get name", r"what('s| is) my name|who am i|do you (know|remember) me", priority=4)
def get_name(ctx: Context) -> str:
    if ctx.user_name:
        return f"You're {ctx.user_name}, of course!"
    return "I don't know your name yet. Tell me by saying “my name is …”."


@skill("time", r"\b(what('s| is) the )?time\b|what time is it", keywords=("time",), help="ask the time")
def tell_time(ctx: Context) -> str:
    return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')}."


@skill(
    "date",
    r"\b(date|day) (is it )?today\b|what('s| is) the date|what day is it",
    keywords=("date",),
    priority=1,
    help="ask the date",
)
def tell_date(ctx: Context) -> str:
    return f"Today is {datetime.now().strftime('%A, %B %d, %Y').replace(' 0', ' ')}."


@skill("joke", r"\bjoke\b|make me laugh|something funny", keywords=("joke",), help="hear a joke")
def joke(ctx: Context) -> str:
    return random.choice(JOKES)


@skill("fact", r"fun fact|tell me (a |something )?(fact|interesting)", keywords=("fact",), help="learn a fun fact")
def fact(ctx: Context) -> str:
    return random.choice(FACTS)


@skill("motivate", r"motivat|inspire me|i('m| am) (tired|sad|stressed|bored)", priority=4, help="get some motivation")
def motivate(ctx: Context) -> str:
    return random.choice(MOTIVATION)


@skill("coin", r"flip a coin|toss a coin|heads or tails", keywords=("coin",), help="flip a coin")
def coin(ctx: Context) -> str:
    return f"It's {random.choice(('heads', 'tails'))}!"


@skill("dice", r"roll (a |the )?(?P<sides>\d+)?[- ]?(sided )?di(c)?e", keywords=("dice",), help="roll a dice")
def dice(ctx: Context, sides: str = "6") -> str:
    n = max(2, min(int(sides), 1000))
    return f"You rolled a {random.randint(1, n)}."


@skill("spell", r"(how do you )?spell (?P<word>[a-z']+)", priority=1, help="spell a word")
def spell(ctx: Context, word: str) -> str:
    return f"{word}: " + " - ".join(word.upper())


# --- safe calculator --------------------------------------------------------

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
_WORDS = (
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\b(times|multiplied by|x)\b", "*"),
    (r"\b(divided by|over)\b", "/"),
    (r"\bmod(ulo)?\b", "%"),
    (r"\b(to the power of|power)\b", "**"),
    (r"\bsquared\b", "**2"),
    (r"\bcubed\b", "**3"),
    (r"(\d)\s*percent of\s*", r"\1/100*"),
)


def evaluate(expr: str) -> float:
    """Evaluate arithmetic without ``eval`` — only numbers and operators are allowed."""
    for pat, rep in _WORDS:
        expr = re.sub(pat, rep, expr, flags=re.IGNORECASE)
    expr = expr.replace("^", "**").replace(",", "")

    def walk(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("that exponent is too big")
            return _OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](walk(node.operand))
        raise ValueError("I can only do arithmetic")

    return walk(ast.parse(expr.strip(), mode="eval"))


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:,.6g}"


@skill(
    "calculate",
    r"^(what('s| is)|calculate|compute|how much is)\s+(?P<expr>[\d\s.()+\-*/^%,]*\d[\d\s.()+\-*/^%,a-z]*)$",
    r"^(?P<expr>\d[\d\s.()+\-*/^%,]*)$",
    priority=5,
    help="do maths, like “what is 12 times 7”",
)
def calculate(ctx: Context, expr: str) -> str | None:
    try:
        return f"{expr.strip()} is {_fmt(evaluate(expr))}."
    except ZeroDivisionError:
        return "Dividing by zero? Even I can't do that."
    except (ValueError, SyntaxError):
        return f"I couldn't work out “{expr}”."


@skill("thanks", r"\b(thanks|thank you|cheers)\b", priority=-1)
def thanks(ctx: Context) -> str:
    return pick("You're welcome!", "Anytime!", "Happy to help.")


@skill("repeat", r"(say that again|repeat( that)?|come again|pardon)$", priority=2)
def repeat(ctx: Context) -> str:
    return ctx.last_reply or "I haven't said anything yet."


HELP_TOPICS = (
    ("time & date", "“what time is it”, “what's the date”"),
    ("maths", "“what is 15 percent of 80”"),
    ("weather", "“what's the weather in Chicago”"),
    ("look-ups", "“who is Ada Lovelace”, “search for pasta recipes”"),
    ("web & music", "“open GitHub”, “play lofi beats”"),
    ("timers", "“set a timer for 5 minutes”, “remind me in 10 minutes to stretch”"),
    ("memory", "“remember that my locker code is 4512”, “take a note buy milk”"),
    ("fun", "jokes, fun facts, coin flips, dice and pep talks"),
)


@skill("help", r"\bhelp\b|what can you do|commands", priority=6)
def help_(ctx: Context, topic_count: int = 3) -> str:
    """Short enough to listen to: a few random examples plus the full topic list."""
    picks = random.sample(HELP_TOPICS, topic_count)
    examples = "; ".join(f"{name}: {ex}" for name, ex in picks)
    topics = ", ".join(name for name, _ in HELP_TOPICS)
    return f"Try things like {examples}. I also know {topics}. Say “goodbye” to stop."
