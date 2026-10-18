"""Random sources for the v3 polish cores (docs/current2/STRONGER_MEMETIC_DESIGN.md §7.3).

Every v3 core draws through two methods only:

    randbelow(n) -> int in [0, n)      (n >= 1)
    random()     -> float in [0, 1)

`MTRng` wraps `random.Random(seed)` and forwards to the same two calls v2 makes
(`rng._randbelow`, `rng.random`), so a v3 core with every new option off makes
v2's draws in v2's order and reproduces its trajectory exactly.

`PortableRng` is xoshiro256** seeded by splitmix64, written so that the C core
(src/native/ls_core.c) produces the same numbers bit for bit:

    randbelow(n) = (next() >> 11) % n            (bias < 2**-40 for n < 2**13; fine)
    random()     = (next() >> 11) * 2**-53

The Python twin of a core run with `PortableRng` and the C core run with the
same seed make the same flips; that equality is what B5 is tested on.
"""
from __future__ import annotations

import random

_M64 = (1 << 64) - 1
_INV53 = 1.0 / (1 << 53)


class MTRng:
    """random.Random behind the v3 interface; draws identical to v2's."""

    __slots__ = ("_r", "randbelow", "random")

    def __init__(self, seed: int) -> None:
        self._r = random.Random(seed)
        self.randbelow = self._r._randbelow  # what random.choice / shuffle call
        self.random = self._r.random


def splitmix64(x: int):
    """One splitmix64 step: (new state, output)."""
    x = (x + 0x9E3779B97F4A7C15) & _M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _M64
    return x, z ^ (z >> 31)


def _rotl(x: int, k: int) -> int:
    return ((x << k) | (x >> (64 - k))) & _M64


class PortableRng:
    """xoshiro256** (Blackman and Vigna), state seeded from `seed` by splitmix64."""

    __slots__ = ("s",)

    def __init__(self, seed: int) -> None:
        x = int(seed) & _M64
        s = []
        for _ in range(4):
            x, z = splitmix64(x)
            s.append(z)
        self.s = s

    def next(self) -> int:
        s = self.s
        result = (_rotl((s[1] * 5) & _M64, 7) * 9) & _M64
        t = (s[1] << 17) & _M64
        s[2] ^= s[0]
        s[3] ^= s[1]
        s[1] ^= s[2]
        s[0] ^= s[3]
        s[2] ^= t
        s[3] = _rotl(s[3], 45)
        return result

    def randbelow(self, n: int) -> int:
        return (self.next() >> 11) % n

    def random(self) -> float:
        return (self.next() >> 11) * _INV53

    def state(self):
        return list(self.s)
