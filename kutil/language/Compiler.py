#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC
from typing import Any

from kutil.language.AST import AST


class Compiler(ABC):
    @abstractmethod
    def compile(self, ast: AST) -> Any:
        """
        Compiles the given AST into Any data structure
        :param ast: The code described by an AST
        :return: Any data structure
        """
        raise NotImplementedError("You must implement the compile method")
