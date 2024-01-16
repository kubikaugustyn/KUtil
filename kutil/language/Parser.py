#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC

from kutil.language.Options import Options
from kutil.language.Token import TokenOutput

from kutil.language.AST import AST

from kutil.language.Error import ParserError


class Parser(ABC):
    def parse(self, tokens: TokenOutput, options: Options) -> AST:
        try:
            return self.parseInner(tokens, options)
        except Exception as e:
            raise ParserError(e)

    @abstractmethod
    def parseInner(self, tokens: TokenOutput, options: Options) -> AST:
        return AST()


class OneUseParser(Parser):
    __used: bool

    def __init__(self):
        super().__init__()
        self.__used = False

    def parse(self, tokens: TokenOutput, options: Options) -> AST:
        if self.__used:
            raise ValueError("Parser already used")
        self.__used = True
        return super().parse(tokens, options)

    @abstractmethod
    def parseInner(self, tokens: TokenOutput, options: Options) -> AST:
        return AST()
