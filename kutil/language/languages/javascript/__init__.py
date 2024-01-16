#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Optional

from kutil.language.Token import TokenOutput
from kutil.language.languages.javascript.Javascript import Javascript

from kutil.language.AST import AST
from kutil.language.languages.javascript.JSOptions import JSOptions

js: Javascript = Javascript()


def parse(code, options: Optional[JSOptions] = None) -> AST:
    options = JSOptions() if options is None else options

    parser = js
    return parser.run(code, options)


def tokenize(code: str, options: Optional[JSOptions] = None) -> TokenOutput:
    options = JSOptions() if options is None else options

    parser = js
    return parser.tokenizeInner(code, options)
