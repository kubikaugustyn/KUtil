#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tkinter as tk
from abc import ABC, abstractmethod
from functools import lru_cache

from matplotlib.lines import drawStyles

from kutil.typing_help import Self, TypeVar

from kutil.pyngguin.enums import STICK, POSITION

TAbstractElement = TypeVar('TAbstractElement', bound="AbstractElement")
TAbstractContainerElement = TypeVar('TAbstractContainerElement', bound="AbstractContainerElement")


class AbstractElement(ABC):
    _underlying: tk.Tk  # FIXME Bad type
    _parent: TAbstractContainerElement | None
    _position: POSITION
    _x: int | None
    _y: int | None
    _width: int | None
    _height: int | None
    _stick: int

    def __init__(self, parent: TAbstractContainerElement):
        self._parent = parent
        self._position = POSITION.RELATIVE
        self._x = self._y = 0
        self._width = self._height = None
        self._stick = 0

        parent._notify_child_added(self)

    @property
    def parent(self) -> TAbstractContainerElement:
        return self._parent

    @property
    @lru_cache(maxsize=512)  # TODO Does this help?
    def root(self) -> TAbstractContainerElement:
        from kutil.pyngguin.Window import WindowParent

        container: TAbstractContainerElement = self._parent
        root_parent = WindowParent()
        while container.parent is not root_parent:
            container = container.parent
        return container

    @property
    def position(self) -> POSITION:
        return self._position

    @position.setter
    def position(self, new_position: POSITION) -> None:
        assert new_position is POSITION.RELATIVE

        self._position = new_position
        if new_position is POSITION.RELATIVE:
            self._underlying.place(in_=self._parent._underlying, x=self._x, y=self._y)
        else:
            raise NotImplementedError

    @property
    def x(self) -> int | None:
        return self._x

    @x.setter
    def x(self, new_x: int | None) -> None:
        if self._position is not POSITION.RELATIVE and new_x is not None:
            raise AttributeError("Attempted to set x, "
                                 "but the element's position is not relative")

        self._x = new_x
        if new_x is not None:
            self._underlying.place(in_=self._parent._underlying, x=new_x, y=self._y)
        else:
            raise NotImplementedError

    @property
    def y(self) -> int | None:
        return self._y

    @y.setter
    def y(self, new_y: int | None) -> None:
        if self._position is not POSITION.RELATIVE and new_y is not None:
            raise AttributeError("Attempted to set y, "
                                 "but the element's position is not relative")

        self._y = new_y
        if new_y is not None:
            self._underlying.place(in_=self._parent._underlying, x=self._x, y=new_y)
        else:
            raise NotImplementedError

    @property
    def width(self) -> int | None:
        return self._width

    @width.setter
    def width(self, new_width: int | None) -> None:
        all_: set[STICK] = STICK.decompose(None, self._stick)
        if STICK.LEFT in all_ and STICK.RIGHT in all_ and new_width is not None:
            raise AttributeError("Attempted to set width, "
                                 "but the element is already sticking to both left and right")

        self._width = new_width
        self._set_underlying_width(new_width)

    @abstractmethod
    def _set_underlying_width(self, new_width: int | None) -> None:
        ...

    @property
    def height(self) -> int | None:
        return self._height

    @height.setter
    def height(self, new_height: int | None) -> None:
        all_: set[STICK] = STICK.decompose(None, self._stick)
        if STICK.TOP in all_ and STICK.BOTTOM in all_ and new_height is not None:
            raise AttributeError("Attempted to set height, "
                                 "but the element is already sticking to both top and bottom")

        self._height = new_height
        self._set_underlying_height(new_height)

    @abstractmethod
    def _set_underlying_height(self, new_height: int | None) -> None:
        ...

    def set_stick(self, new_stick: int | STICK) -> Self:
        self.reset_stick()
        self.add_stick(new_stick)
        return self

    def add_stick(self, additional_stick: int | STICK) -> Self:
        if isinstance(additional_stick, int):
            combined_stick = self._stick | additional_stick
        else:
            combined_stick = self._stick | additional_stick.value

        combined_all: set[STICK] = STICK.decompose(None, combined_stick)
        if STICK.LEFT in combined_all and STICK.RIGHT in combined_all and self._width is not None:
            raise AttributeError("Attempted to stick to both left and right, "
                                 "but width is already set")
        elif STICK.TOP in combined_all and STICK.BOTTOM in combined_all and self._height is not None:
            raise AttributeError("Attempted to stick to both top and bottom, "
                                 "but height is already set")

        self._stick = combined_stick
        return self

    def reset_stick(self) -> Self:
        self._stick = 0
        return self

    def get_stick(self) -> int:
        return self._stick


class AbstractContainerElement(AbstractElement):
    _children: list[TAbstractElement | TAbstractContainerElement]

    def __init__(self, parent: Self | None):
        super().__init__(parent)
        self._children = []

    @property
    def children(self) -> list[TAbstractElement | TAbstractContainerElement]:
        """
        Returns a copy of the container element's children.
        :return: A copy of the container element's children
        """
        return self._children.copy()

    def _notify_child_added(self, child: TAbstractElement | TAbstractContainerElement) -> Self:
        if child.parent is not self:  # Yes, compare the addresses
            raise RuntimeError(
                "Attempted to notify a container that a child has been created for it, "
                "but the child's parent is not the container, "
                "e.g. you called the private method_notify_child_added() incorrectly.")
        elif child in self._children:
            raise RuntimeError(
                "Attempted to notify a container that a child has been created for it, "
                "but the container already contains that child.")
        self._children.append(child)
        return self
