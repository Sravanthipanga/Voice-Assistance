import pytest

from sravs import skills  # noqa: F401
from sravs.brain import Brain, Context
from sravs.skills import web
from sravs.storage import Memory


class Recorder:
    def __init__(self):
        self.messages = []

    def __call__(self, msg):
        self.messages.append(msg)


@pytest.fixture
def ctx(tmp_path):
    return Context(memory=Memory(tmp_path / "memory.json"), notify=Recorder())


@pytest.fixture
def brain(ctx):
    return Brain(ctx)


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr(web, "open_url", lambda url: urls.append(url) or True)
    return urls
