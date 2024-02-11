#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.language.AST import AST
from kutil.language.Options import Options
from kutil.language.Token import TokenOutput

from kutil.language.languages.javascript.JSOptions import JSOptions

from kutil.language.Language import GenericLanguage
from kutil.language.languages.javascript.JSLexer import JSLexer
from kutil.language.languages.javascript.JSParser import JSParser


# This is a GenericLanguage because I'm not trying to run JS, but only to parse it
class Javascript(GenericLanguage):
    optionsClass = JSOptions
    lexer: JSLexer
    parser: JSParser

    def __init__(self):
        super().__init__(JSLexer(), JSParser())

    def run(self, inputCode: str, options: Options) -> AST:
        # Both are one-use
        self.lexer = JSLexer()
        self.parser = JSParser()

        # This is a bit different from usual classes
        if options is None:
            options = self.optionsClass()
        self.lexer.prepare(inputCode, options)
        ast: AST = self.parseInner(TokenOutput(), options)
        return ast

    @staticmethod
    def name() -> str:
        return "Javascript"
