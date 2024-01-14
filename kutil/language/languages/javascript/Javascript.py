#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.language.Language import GenericLanguage
from kutil.language.languages.javascript.JSLexer import JSLexer
from kutil.language.languages.javascript.JSParser import JSParser


# This is a GenericLanguage because I'm not trying to run JS, but only to parse it
class Javascript(GenericLanguage):
    def __init__(self):
        super().__init__(JSLexer(), JSParser())

    @staticmethod
    def name() -> str:
        return "Javascript"
