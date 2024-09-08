#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tkinter as tk
from typing import Self

from kutil import singleton
from kutil.typing_help import Final, Set

from kutil.pyngguin.AbstractElement import AbstractElement, AbstractContainerElement
from kutil.pyngguin.enums_types import STICK, ChangeInfo

_WINDOWS: Final[Set["Window"]] = set()


@singleton
class WindowParent(AbstractContainerElement):
    def __init__(self) -> None:
        super().__init__(parent=self)

    def _notify_child_added(self, child: AbstractElement | Self) -> Self:
        if child is not self:
            return super()._notify_child_added(child)
        return self

    def _update_underlying_position(self, info: ChangeInfo) -> None:
        pass

    def _update_underlying_x(self, info: ChangeInfo) -> None:
        pass

    def _update_underlying_y(self, info: ChangeInfo) -> None:
        pass

    def _update_underlying_width(self, info: ChangeInfo) -> None:
        pass

    def _update_underlying_height(self, info: ChangeInfo) -> None:
        pass

    def __repr__(self) -> str:
        return f"kutil.pyngguin.WindowParent(parent=self)"


class Window(AbstractContainerElement):
    _underlying: tk.Tk
    _title: str

    def __init__(self):
        self._underlying = tk.Tk()  # DO NOT MOVE UNDER super().__init__(...) UNDER ANY CIRCUMSTANCES
        self._title = "Window"
        super().__init__(parent=WindowParent())
        self._underlying.bind("<Configure>", self._configure_listener)

        _WINDOWS.add(self)

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, new_title: str) -> None:
        self._title = new_title
        self._underlying.wm_title(new_title)

    def _update_underlying_position(self, info: ChangeInfo) -> None:
        raise NotImplementedError

    def _update_underlying_x(self, info: ChangeInfo) -> None:
        raise NotImplementedError

    def _update_underlying_y(self, info: ChangeInfo) -> None:
        raise NotImplementedError

    def _update_underlying_width(self, info: ChangeInfo) -> None:
        self._underlying.geometry(f"{self._width or 0}x{self._height or 0}")

    def _update_underlying_height(self, info: ChangeInfo) -> None:
        self._underlying.geometry(f"{self._width or 0}x{self._height or 0}")

    def set_stick(self, new_stick: int | STICK) -> Self:
        raise RuntimeError("You cannot stick the window in any direction.")

    def add_stick(self, additional_stick: int | STICK) -> Self:
        raise RuntimeError("You cannot stick the window in any direction.")

    def reset_stick(self) -> Self:
        raise RuntimeError("You cannot stick the window in any direction.")

    def get_stick(self) -> int:
        raise RuntimeError("You cannot stick the window in any direction.")

    def _configure_listener(self, event) -> None:
        print("Window configured")
        self._on_self_changed(ChangeInfo(self, ))


def main_loop() -> None:
    if len(_WINDOWS) == 0:
        raise RuntimeError("Too early to run the main loop: no window")

    tk.mainloop()
