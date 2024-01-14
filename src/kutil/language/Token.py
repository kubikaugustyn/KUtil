#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum
from typing import Any, Iterator


class Token:
    kind: Enum  # A token kind defined by the language
    content: Any  # Any arbitrary content of the token

    def __init__(self, kind: Enum, content: Any):
        self.kind = kind
        self.content = content

    def __eq__(self, other) -> bool:
        if not isinstance(other, Token):
            return False
        return self.kind == other.kind and self.content == other.content

    def __ne__(self, other) -> bool:
        return not (self == other)

    def __str__(self) -> str:
        if self.content is None:
            return f"<Token {self.kind.name}>"
        return f"<Token {self.kind.name} - {ascii(self.content)}>"


class TokenOutput(Iterator[Token]):
    __iter: Iterator[Token]

    def __init__(self, iterator: Iterator[Token] | None = None):
        self.__iter = iterator

    def setIterator(self, iterator: Iterator[Token]):
        if self.__iter is not None:
            raise ValueError("The iterator is already set")
        self.__iter = iterator

    def nextToken(self) -> Token:
        return next(self.__iter)

    def nextTokens(self, amount: int) -> list[Token]:
        tokens: list[Token] = []
        for _ in range(amount):
            tokens.append(self.nextToken())
        return tokens

    def nextTokenDef(self, default: Any = None) -> Token | Any:
        return next(self.__iter, default)

    def cancel(self):
        raise StopIteration

    '''def all(self) -> list[Token]:
        """
        Do not use this function.
        :returns: All the remaining tokens in the TokenOutput
        """
        tokens: list[Token] = []
        try:
            while True:
                tokens.append(self.nextToken())
        except StopIteration:
            pass
        return tokens'''

    def __next__(self) -> Token:
        return self.nextToken()
