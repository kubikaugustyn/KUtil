#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

from functools import lru_cache
from kutil.typing_help import Self, TypeVar
from enum import Enum, IntEnum, auto, unique

TAbstractElement = TypeVar('TAbstractElement', bound="AbstractElement")
TAbstractContainerElement = TypeVar('TAbstractContainerElement', bound="AbstractContainerElement")


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


class ChangeInfo:
    target: TAbstractElement
    cause: Self | None
    parent_changed: bool

    position_changed: bool
    x_changed: bool
    y_changed: bool
    width_changed: bool
    height_changed: bool
    stick_changed: bool
    children_list_changed: bool
    title_changed: bool
    text_changed: bool

    def __init__(self, target: TAbstractElement, *, cause: Self | None = None,
                 position_changed: bool = False, x_changed: bool = False, y_changed: bool = False,
                 width_changed: bool = False, height_changed: bool = False,
                 stick_changed: bool = False, children_list_changed: bool = False,
                 title_changed: bool = False, text_changed: bool = False):
        from kutil.pyngguin.AbstractElement import AbstractElement

        assert isinstance(target, AbstractElement)
        self.target = target
        self.cause = cause
        self.parent_changed = cause is not None
        if self.parent_changed:
            assert self.target is cause.target

        self.position_changed = position_changed
        self.x_changed = x_changed
        self.y_changed = y_changed
        self.width_changed = width_changed
        self.height_changed = height_changed
        self.stick_changed = stick_changed
        self.children_list_changed = children_list_changed
        self.title_changed = title_changed
        self.text_changed = text_changed

    def __repr__(self) -> str:
        changes: list[str] = []
        for name in dir(self):
            if not name.endswith("_changed") or name == "parent_changed":
                continue
            changed = getattr(self, name)
            if changed:
                changes.append(name[:-8])
        return (f"kutil.pyngguin.ChangeInfo(target={self.target}, cause={self.cause}, "
                f"parent_changed={self.parent_changed}, changes=[{', '.join(changes)}])")
