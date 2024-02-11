#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.io.file import readFile
from kutil.language.Token import TokenOutput

from kutil.language.languages.javascript import parseScript, tokenizeScript
from kutil.language.languages.javascript.JSOptions import JSOptions




if __name__ == '__main__':
    options: JSOptions = JSOptions()
    # tokens: TokenOutput = tokenizeScript(readFile("test.js", "text"), options)
    # for token in tokens:
    #     print(token)
    ast, script = parseScript(readFile("test.js", "text"), options)
    nodes = ast.getNodes(script.body)
    print(ast)  # Debug this to see more
