#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Optional

from kutil.language.Token import TokenOutput
from kutil.language.languages.javascript.nodes import Script, Module
from kutil.language.languages.javascript.Javascript import Javascript

from kutil.language.AST import AST, ASTNode
from kutil.language.languages.javascript.JSOptions import JSOptions

js: Javascript = Javascript()


def parseScript(code, options: Optional[JSOptions] = None) -> tuple[AST, Script]:
    options = JSOptions() if options is None else options
    options.module = False

    parser = js
    # Doesn't run the code, called run for subclass compatability
    ast: AST = parser.run(code, options)
    script: ASTNode = next(ast.rootNodes())
    assert isinstance(script, Script)
    return ast, script


def parseModule(code, options: Optional[JSOptions] = None) -> tuple[AST, Module]:
    options = JSOptions() if options is None else options
    options.module = True

    parser = js
    ast: AST = parser.run(code, options)
    module: ASTNode = next(ast.rootNodes())
    assert isinstance(module, Module)
    return ast, module


def tokenizeScript(code: str, options: Optional[JSOptions] = None) -> TokenOutput:
    options = JSOptions() if options is None else options
    options.module = False

    parser = js
    return parser.tokenizeInner(code, options)


def tokenizeModule(code: str, options: Optional[JSOptions] = None) -> TokenOutput:
    options = JSOptions() if options is None else options
    options.module = True

    parser = js
    return parser.tokenizeInner(code, options)
