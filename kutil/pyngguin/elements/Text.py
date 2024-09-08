#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tkinter as tk

from kutil.pyngguin.AbstractElement import AbstractElement, TAbstractContainerElement

from kutil.pyngguin.enums_types import ChangeInfo


class Text(AbstractElement):
    _underlying: tk.Label
    _text: str

    def __init__(self, parent: TAbstractContainerElement):
        super().__init__(parent)
        self._underlying = tk.Label(master=parent._underlying, bg="cyan")
        self._text = ""

        self._underlying.pack()
        self._underlying.place(in_=parent._underlying, x=0, y=0)

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, new_text: str) -> None:
        self._text = new_text
        self._on_self_changed(ChangeInfo(self, text_changed=True))

    def _update_underlying_text(self, info: ChangeInfo) -> None:
        self._underlying.config(text=self._text)

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

    def _on_self_changed(self, info: ChangeInfo) -> None:
        super()._on_self_changed(info)
        if info.text_changed:
            self._update_underlying_text(info)
