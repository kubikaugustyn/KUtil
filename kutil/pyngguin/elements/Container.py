#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tkinter as tk

from kutil.pyngguin.AbstractElement import AbstractContainerElement, TAbstractContainerElement

from kutil.pyngguin.enums_types import ChangeInfo


class Container(AbstractContainerElement):
    _underlying: tk.Frame

    def __init__(self, parent: TAbstractContainerElement):
        super().__init__(parent)
        self._underlying = tk.Frame(master=parent._underlying, width=600, height=500, bg="red")

        self._underlying.place(in_=parent._underlying, x=0, y=0)

    def _update_underlying_position(self, info: ChangeInfo) -> None:
        raise NotImplementedError

    def _update_underlying_x(self, info: ChangeInfo) -> None:
        self._underlying.place(x=self._x)

    def _update_underlying_y(self, info: ChangeInfo) -> None:
        self._underlying.place(y=self._y)

    def _update_underlying_width(self, info: ChangeInfo) -> None:
        self._underlying.place(width=self._width)

    def _update_underlying_height(self, info: ChangeInfo) -> None:
        self._underlying.place(height=self._height)
