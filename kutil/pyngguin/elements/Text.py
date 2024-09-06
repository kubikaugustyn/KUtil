#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tkinter as tk
from typing import Self

from kutil.pyngguin.AbstractElement import AbstractElement, TAbstractContainerElement


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
        self._underlying.config(text=new_text)

    def _set_underlying_width(self, new_width: int | None) -> None:
        self._underlying.place(width=new_width)

    def _set_underlying_height(self, new_height: int | None) -> None:
        self._underlying.place(height=new_height)
