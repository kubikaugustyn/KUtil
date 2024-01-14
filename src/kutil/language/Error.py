#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"


class LanguageError(ExceptionGroup):
    msg: str = "LOL"

    def __init__(self, e: Exception | list[Exception]):
        super().__init__(self.msg, e if isinstance(e, list) else [e])

    def __new__(cls, e: Exception | list[Exception]):
        return super().__new__(cls, cls.msg, e if isinstance(e, list) else [e])


class LexerError(LanguageError):
    msg: str = "Failed to tokenize"


class ParserError(LanguageError):
    msg: str = "Failed to parse"


class CompilerError(LanguageError):
    msg: str = "Failed to compile"


class InterpreterError(LanguageError):
    msg: str = "Failed to interpret"
