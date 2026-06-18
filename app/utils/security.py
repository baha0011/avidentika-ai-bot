from __future__ import annotations

import html
import re
import time
from collections import defaultdict, deque

INJECTION_PATTERNS = (
    r"ignore (all|any|the|previous).*instructions",
    r"ігноруй .*інструкц",
    r"игнорируй .*инструкц",
    r"(show|reveal|print).*(system prompt|api key)",
    r"(покажи|раскрой|виведи).*(системн.*промпт|api.?ключ|інструкц)",
    r"developer message|system message|jailbreak",
)
EMERGENCY_PATTERNS = (
    r"невыносим.*боль|нестерпн.*біль|сильн.*кровотеч|не зупин.*кров",
    r"затруднен.*дыхан|важко дихати|потер.*сознани|втрат.*свідом",
    r"сильн.*от[её]к|виражен.*набряк|высок.*температур|висок.*температур",
    r"серьезн.*травм|серйозн.*травм",
)


def contains_prompt_injection(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in INJECTION_PATTERNS)


def is_emergency(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in EMERGENCY_PATTERNS)


def safe_html(text: object) -> str:
    return html.escape(str(text or ""), quote=False)


class RateLimiter:
    def __init__(self, requests: int, period_seconds: int) -> None:
        self.requests = requests
        self.period_seconds = period_seconds
        self._events: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        events = self._events[user_id]
        while events and events[0] <= now - self.period_seconds:
            events.popleft()
        if len(events) >= self.requests:
            return False
        events.append(now)
        return True
