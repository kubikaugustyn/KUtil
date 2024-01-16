#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Callable

from kutil.language.Options import UnifiedOptions
from kutil.language.languages.javascript.error_handler import ErrorHandler




class JSOptions(UnifiedOptions):
    ignoreComments: bool
    errorHandlerLexer: ErrorHandler
    errorHandlerParser: ErrorHandler
    lexer: object  # JSLexer
    delegate: Callable

    range: bool
    loc: bool
    source: str | None
    tokens: bool
    comment: bool
    tolerant: bool

    def __init__(self, range=False, loc=False, source=None, tokens=False, comment=False,
                 tolerant=False, **options):
        self.ignoreComments = False
        self.errorHandlerLexer = ErrorHandler(True)
        self.errorHandlerParser = ErrorHandler(False)
        self.lexer = None

        self.range = range
        self.loc = loc
        self.source = source
        self.tokens = tokens
        self.comment = comment
        self.tolerant = tolerant
        for k, v in options.items():
            setattr(self, k, v)

    def toDict(self) -> dict:
        names = {"range", "loc", "source", "tokens", "comment", "tolerant"}
        vals = {}
        for name in names:
            vals[name] = getattr(self, name)
        return vals
