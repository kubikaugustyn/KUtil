#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Any

from kutil.language.AST import AST
from kutil.language.Compiler import Compiler


class PTCompiler(Compiler):
    def compile(self, ast: AST) -> Any:
        for contract in ast.rootNodes():
            nodes = ast.getNodes(contract.data)
            pass
