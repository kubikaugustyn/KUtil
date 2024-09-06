#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

from functools import lru_cache
from kutil.typing_help import Self
from enum import Enum, IntEnum, auto, unique


@unique
class STICK(IntEnum):
    LEFT = 0b0001
    RIGHT = 0b0010
    TOP = 0b0100
    BOTTOM = 0b1000

    def __ior__(self, other: Self):
        return self.value | other.value

    @lru_cache(maxsize=14)  # 4 modes + 10 combinations of modes
    def decompose(self, stick: int | Self) -> set[Self]:
        """
        Decomposes either the stick mode itself or a combination of them into a set of all set modes.
        :param self: Use None, I can't type-annotate it with Self
        :param stick: Either the stick mode itself or a combination of them
        :return: The set of all set modes
        """
        if isinstance(stick, STICK):
            return {stick}
        assert isinstance(stick, int)
        assert 0b0000 <= stick <= 0b1111

        all_: set[STICK] = set()
        if stick | STICK.LEFT == 1:
            all_.add(STICK.LEFT)
        if stick | STICK.RIGHT == 1:
            all_.add(STICK.RIGHT)
        if stick | STICK.TOP == 1:
            all_.add(STICK.TOP)
        if stick | STICK.BOTTOM == 1:
            all_.add(STICK.BOTTOM)
        return all_


@unique
class POSITION(Enum):
    RELATIVE = auto()

