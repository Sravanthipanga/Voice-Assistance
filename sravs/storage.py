"""Tiny JSON-backed memory (facts, notes, the user's name)."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path


def default_path() -> Path:
    base = os.environ.get("SRAVS_HOME") or Path.home() / ".sravs"
    return Path(base) / "memory.json"


class Memory:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else default_path()
        self._lock = threading.Lock()
        self._data: dict = {"facts": {}, "notes": [], "profile": {}}
        if self.path.exists():
            try:
                self._data.update(json.loads(self.path.read_text("utf-8")))
            except (OSError, json.JSONDecodeError):
                pass  # corrupt file: start fresh rather than crash

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), "utf-8")
        tmp.replace(self.path)  # atomic on POSIX and Windows

    # profile -----------------------------------------------------------
    def get_profile(self, key: str) -> str | None:
        return self._data["profile"].get(key)

    def set_profile(self, key: str, value: str) -> None:
        with self._lock:
            self._data["profile"][key] = value
            self._save()

    # facts -------------------------------------------------------------
    def remember(self, key: str, value: str) -> None:
        with self._lock:
            self._data["facts"][key.lower()] = value
            self._save()

    def recall(self, key: str) -> str | None:
        return self._data["facts"].get(key.lower())

    def forget(self, key: str) -> bool:
        with self._lock:
            found = self._data["facts"].pop(key.lower(), None) is not None
            if found:
                self._save()
            return found

    def facts(self) -> dict[str, str]:
        return dict(self._data["facts"])

    # notes -------------------------------------------------------------
    def add_note(self, note: str) -> int:
        with self._lock:
            self._data["notes"].append(note)
            self._save()
            return len(self._data["notes"])

    def notes(self) -> list[str]:
        return list(self._data["notes"])

    def clear_notes(self) -> int:
        with self._lock:
            n = len(self._data["notes"])
            self._data["notes"] = []
            self._save()
            return n
