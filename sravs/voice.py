"""Speech in/out with graceful fallbacks.

* ``Speaker`` uses pyttsx3 (offline TTS). Without it, replies are printed.
* ``Listener`` uses SpeechRecognition + a microphone. Without them (or with
  ``--text``) it reads from the keyboard instead, so Sravs always works.
"""

from __future__ import annotations

import queue
import threading


class Speaker:
    def __init__(self, enabled: bool = True, rate: int = 180, voice: str | None = None):
        self.engine = None
        self._lock = threading.Lock()
        if not enabled:
            return
        try:
            import pyttsx3

            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", rate)
            if voice:
                for v in self.engine.getProperty("voices"):
                    if voice.lower() in (v.name or "").lower() or voice.lower() in (v.id or "").lower():
                        self.engine.setProperty("voice", v.id)
                        break
        except Exception as exc:  # missing package or no audio driver
            print(f"(voice output unavailable: {exc}; replies will be printed)")
            self.engine = None

    def say(self, text: str, name: str = "Sravs") -> None:
        print(f"{name}: {text}")
        if self.engine is not None and text:
            with self._lock:
                self.engine.say(text)
                self.engine.runAndWait()


class Listener:
    """Returns the next utterance as text, or None if nothing was understood."""

    def __init__(self, use_mic: bool = True, language: str = "en-US", timeout: float = 6, phrase_limit: float = 12):
        self.language = language
        self.timeout = timeout
        self.phrase_limit = phrase_limit
        self.sr = None
        self.mic = None
        self.recognizer = None
        if use_mic:
            try:
                import speech_recognition as sr

                self.sr = sr
                self.recognizer = sr.Recognizer()
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = 0.7
                self.mic = sr.Microphone()
                with self.mic as source:  # calibrate once, not on every turn
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
            except Exception as exc:
                print(f"(microphone unavailable: {exc}; switching to typing)")
                self.mic = None

    @property
    def voice(self) -> bool:
        return self.mic is not None

    def listen(self) -> str | None:
        if not self.voice:
            try:
                return input("You: ").strip()
            except EOFError:
                return "goodbye"
        sr = self.sr
        with self.mic as source:
            print("🎙  Listening…")
            try:
                audio = self.recognizer.listen(source, timeout=self.timeout, phrase_time_limit=self.phrase_limit)
            except sr.WaitTimeoutError:
                return None
        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            print(f"(speech service error: {exc})")
            return ""
        print(f"You: {text}")
        return text


class Inbox:
    """Thread-safe queue for messages from timers and reminders."""

    def __init__(self) -> None:
        self._q: queue.Queue[str] = queue.Queue()

    def put(self, message: str) -> None:
        self._q.put(message)

    def drain(self) -> list[str]:
        items = []
        while True:
            try:
                items.append(self._q.get_nowait())
            except queue.Empty:
                return items
