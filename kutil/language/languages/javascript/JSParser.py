#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique

from kutil.language.AST import AST, ASTNode
from kutil.language.Parser import Parser
from kutil.language.Token import TokenOutput, Token


@unique
class JSNode(Enum):
    pass


class JSParser(Parser):
    def parseInner(self, tokens: TokenOutput) -> AST:
        tokens.cancel()  # To be done
        return AST()

        ast: AST = AST()
        # for token in tokens:
        #     print(token)
        while True:
            token = tokens.nextTokenDef()
            if token is None:
                break

        return ast
