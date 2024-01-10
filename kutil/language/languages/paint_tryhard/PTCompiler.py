#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.language.AST import AST
from kutil.language.Bytecode import InstructionGenerator, Instruction
from kutil.language.Compiler import Compiler


class PTInstruction(Instruction):
    pass


class PTCompiler(Compiler):
    def compile(self, ast: AST) -> InstructionGenerator:
        for contract in ast.rootNodes():
            nodes = ast.getNodes(contract.data)
            pass
            # TODO reinvent the bytecode and compiled output format

        a = 1
        if a == 1:
            raise RuntimeError
        yield PTInstruction.SUS, None
