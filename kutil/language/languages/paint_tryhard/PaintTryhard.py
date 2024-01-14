#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.language.Language import CompiledLanguage
from kutil.language.languages.paint_tryhard.PTLexer import PTLexer
from kutil.language.languages.paint_tryhard.PTParser import PTParser
from kutil.language.languages.paint_tryhard.PTCompiler import PTCompiler
from kutil.language.languages.paint_tryhard.PTInterpreter import PTInterpreter


class PaintTryhard(CompiledLanguage):
    def __init__(self):
        super().__init__(PTLexer(), PTParser(), PTCompiler(),PTInterpreter())

    @staticmethod
    def name() -> str:
        return "PaintTryhard"
