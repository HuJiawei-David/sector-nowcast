"""Calendar-quarter arithmetic and the clean-value rules of hard rule 4."""
from __future__ import annotations

import re
from dataclasses import dataclass

_Q_RE = re.compile(r"^(\d{4})Q([1-4])$")


@dataclass(frozen=True, order=True)
class Quarter:
    year: int
    q: int

    @classmethod
    def parse(cls, s: str) -> "Quarter":
        m = _Q_RE.match(str(s))
        if not m:
            raise ValueError(f"not a calendar quarter label: {s!r}")
        return cls(int(m.group(1)), int(m.group(2)))

    def __add__(self, n: int) -> "Quarter":
        idx = self.year * 4 + (self.q - 1) + n
        return Quarter(idx // 4, idx % 4 + 1)

    def __sub__(self, n: int) -> "Quarter":
        return self + (-n)

    def __str__(self) -> str:
        return f"{self.year}Q{self.q}"


def qrange(start: Quarter, end: Quarter) -> list[Quarter]:
    if end < start:
        return []
    out, q = [], start
    while q <= end:
        out.append(q)
        q = q + 1
    return out


def in_window(q: Quarter, window: tuple[Quarter, Quarter]) -> bool:
    return window[0] <= q <= window[1]


def yoy_clean(q: Quarter, exclusion: tuple[Quarter, Quarter]) -> bool:
    """A YoY value for q is clean if neither q nor q-4 is in the exclusion window."""
    return not in_window(q, exclusion) and not in_window(q - 4, exclusion)


def d_clean(q: Quarter, exclusion: tuple[Quarter, Quarter]) -> bool:
    """d_q = YoY_q - YoY_{q-1} is clean if both YoY values it uses are clean."""
    return yoy_clean(q, exclusion) and yoy_clean(q - 1, exclusion)
