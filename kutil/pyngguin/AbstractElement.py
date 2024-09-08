#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tkinter as tk
from abc import ABC, abstractmethod
from functools import lru_cache
from kutil.typing_help import Self, EnforceSuperCallMeta, enforcesupercall

from kutil.pyngguin.enums_types import STICK, POSITION, ChangeInfo, TAbstractElement, \
    TAbstractContainerElement


class AbstractElement(ABC, metaclass=EnforceSuperCallMeta):
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

    # Getters and setters
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
        self._on_self_changed(ChangeInfo(self,
                                         position_changed=True, x_changed=True, y_changed=True))

    @abstractmethod
    def _update_underlying_position(self, info: ChangeInfo) -> None:
        ...

    @property
    def x(self) -> int | None:
        return self._x

    @x.setter
    def x(self, new_x: int | None) -> None:
        if self._position is not POSITION.RELATIVE and new_x is not None:
            raise AttributeError("Attempted to set x, "
                                 "but the element's position is not relative")

        self._x = new_x
        self._on_self_changed(ChangeInfo(self, x_changed=True))

    @abstractmethod
    def _update_underlying_x(self, info: ChangeInfo) -> None:
        ...

    @property
    def y(self) -> int | None:
        return self._y

    @y.setter
    def y(self, new_y: int | None) -> None:
        if self._position is not POSITION.RELATIVE and new_y is not None:
            raise AttributeError("Attempted to set y, "
                                 "but the element's position is not relative")

        self._y = new_y
        self._on_self_changed(ChangeInfo(self, y_changed=True))

    @abstractmethod
    def _update_underlying_y(self, info: ChangeInfo) -> None:
        ...

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
        self._on_self_changed(ChangeInfo(self, width_changed=True))

    @abstractmethod
    def _update_underlying_width(self, info: ChangeInfo) -> None:
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
        self._on_self_changed(ChangeInfo(self, height_changed=True))

    @abstractmethod
    def _update_underlying_height(self, info: ChangeInfo) -> None:
        ...

    def set_stick(self, new_stick: int | STICK) -> Self:
        self.reset_stick()
        self.add_stick(new_stick)
        self._on_self_changed(ChangeInfo(self, stick_changed=True))
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
        self._on_self_changed(ChangeInfo(self, stick_changed=True))
        return self

    def reset_stick(self) -> Self:
        self._stick = 0
        self._on_self_changed(ChangeInfo(self, stick_changed=True))
        return self

    def get_stick(self) -> int:
        return self._stick

    # Methods
    def _notify_parent_changed(self, info: ChangeInfo) -> None:
        """
        A function called whenever a parent of this element has changed.

        The changes include the parent being resized, moved, a child being added (including self), etc.
        """

    @enforcesupercall
    def _on_self_changed(self, info: ChangeInfo) -> None:
        """
        A function called whenever the element has changed.

        The changes include the parent being resized, moved, a child being added (including self), etc.

        This function is overridden in AbstractContainerElement
        to call _notify_parent_changed() on its children.
        """

        if info.position_changed:
            self._update_underlying_position(info)
        if info.x_changed:
            self._update_underlying_x(info)
        if info.y_changed:
            self._update_underlying_y(info)
        if info.width_changed:
            self._update_underlying_width(info)
        if info.height_changed:
            self._update_underlying_height(info)
        print(f"Self changed: {repr(info)}")

    def __repr__(self) -> str:
        # TODO
        return f"kutil.pyngguin.{self.__class__.__name__}(...)"


class AbstractContainerElement(AbstractElement, ABC):
    _children: list[TAbstractElement | TAbstractContainerElement]

    def __init__(self, parent: Self | None):
        self._children = []  # DO NOT MOVE UNDER super().__init__(parent) UNDER ANY CIRCUMSTANCES
        super().__init__(parent)

    @property
    def children(self) -> list[TAbstractElement | TAbstractContainerElement]:
        """
        Returns a copy of the container element's children.
        :return: A copy of the container element's children
        """
        return self._children.copy()

    def _on_self_changed(self, info: ChangeInfo) -> None:
        super()._on_self_changed(info)
        self._notify_children_parent_changed(info)

    def _notify_children_parent_changed(self, info: ChangeInfo) -> None:
        info_for_children: ChangeInfo = ChangeInfo(target=info.target, cause=info)
        for child in self._children:
            child._notify_parent_changed(info_for_children)

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
        self._notify_children_parent_changed(ChangeInfo(self, children_list_changed=True))
        return self
