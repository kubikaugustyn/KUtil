#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tkinter as tk

from kutil.pyngguin.AbstractElement import AbstractContainerElement, TAbstractContainerElement


class Container(AbstractContainerElement):
    _underlying: tk.Frame

    def __init__(self, parent: TAbstractContainerElement):
        super().__init__(parent)
        self._underlying = tk.Frame(master=parent._underlying, width=600, height=500, bg="red")

        self._underlying.place(in_=parent._underlying, x=0, y=0)

    def _set_underlying_width(self, new_width: int | None) -> None:
        self._underlying.place(width=new_width)

    def _set_underlying_height(self, new_height: int | None) -> None:
        self._underlying.place(height=new_height)
