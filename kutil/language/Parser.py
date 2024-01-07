#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC

from kutil.language.Token import TokenOutput

from kutil.language.AST import AST

from kutil.language.Error import ParserError


class Parser(ABC):
    def parse(self, tokens: TokenOutput) -> AST:
        try:
            return self.parseInner(tokens)
        except Exception as e:
            raise ParserError(e)

    @abstractmethod
    def parseInner(self, tokens: TokenOutput) -> AST:
        return AST()
