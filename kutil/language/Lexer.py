#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC
from typing import Iterator

from kutil.language.Options import Options
from kutil.language.Token import Token, TokenOutput
from kutil.language.Error import LexerError


class Lexer(ABC):
    def tokenize(self, inputCode: str, options: Options) -> TokenOutput:
        try:
            output: TokenOutput = TokenOutput()
            iterator: Iterator[Token] = self.tokenizeInner(inputCode, options, output)
            output.setIterator(iterator)
            return output
        except Exception as e:
            raise LexerError(e)

    @abstractmethod
    def tokenizeInner(self, inputCode: str, options: Options, output: TokenOutput) \
            -> Iterator[Token]:
        output.cancel()  # This will crash the method before yielding None
        yield None


class OneUseLexer(Lexer):
    __used: bool

    def __init__(self):
        super().__init__()
        self.__used = False

    def tokenize(self, inputCode: str, options: Options) -> TokenOutput:
        if self.__used:
            raise ValueError("Lexer already used")
        self.__used = True
        return super().tokenize(inputCode, options)

    @abstractmethod
    def tokenizeInner(self, inputCode: str, options: Options, output: TokenOutput) \
            -> Iterator[Token]:
        raise NotImplementedError
