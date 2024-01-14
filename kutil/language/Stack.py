#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Any


class Stack:
    values: list[Any]

    def __init__(self):
        self.values = []

    def push(self, value: Any):
        if not self.validateItem(value):
            raise ValueError(f"Invalid item {value}")
        self.values.append(value)

    def pop(self) -> Any:
        return self.values.pop()

    def validateItem(self, item: Any) -> bool:
        """
        Validates an item and returns True if the item is allowed.

        Can be overwritten by subclasses.
        """
        return True
