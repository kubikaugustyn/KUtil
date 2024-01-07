#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC
from typing import Iterator

from kutil.language.Token import Token, TokenOutput
from kutil.language.Error import LexerError


class Lexer(ABC):
    def tokenize(self, inputCode: str) -> TokenOutput:
        try:
            output: TokenOutput = TokenOutput()
            iterator: Iterator[Token] = self.tokenizeInner(inputCode, output)
            output.setIterator(iterator)
            return output
        except Exception as e:
            raise LexerError(e)

    @abstractmethod
    def tokenizeInner(self, inputCode: str, output: TokenOutput) -> Iterator[Token]:
        output.cancel()  # This will crash the method before yielding None
        yield None
