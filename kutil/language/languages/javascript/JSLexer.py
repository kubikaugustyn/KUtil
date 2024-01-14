#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Iterator

from kutil.language.Lexer import Lexer
from kutil.language.Token import TokenOutput, Token


@unique
class JSToken(Enum):
    pass


class JSLexer(Lexer):
    def tokenizeInner(self, inputCode: str, output: TokenOutput) -> Iterator[Token]:
        raise NotImplementedError
