#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.io.file import readFile
from kutil.language.AST import AST
from kutil.language.Token import TokenOutput

from kutil.language.languages.javascript import parse, tokenize
from kutil.language.languages.javascript.JSOptions import JSOptions

if __name__ == '__main__':
    options: JSOptions = JSOptions()
    # tokens: TokenOutput = tokenize(readFile("test.js", "text"), options)
    # for token in tokens:
    #     print(token)
    ast: AST = parse(readFile("test.js", "text"), options)
    print(ast)
