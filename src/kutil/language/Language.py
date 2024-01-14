#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import zlib
from abc import abstractmethod
from typing import Optional

from kutil.buffer.TextOutput import TextOutput
from kutil.io.file import readFile

from kutil.language.AST import AST
from kutil.language.BytecodeFile import BytecodeFile, CRC32MismatchError

from kutil.language.Token import TokenOutput

from kutil.language.Lexer import Lexer
from kutil.language.Parser import Parser
from kutil.language.Compiler import Compiler
from kutil.language.Interpreter import Interpreter, InterpreterExitCode, BytecodeInterpreter
from kutil.language.Error import InterpreterError


class GenericLanguage:
    lexer: Lexer
    parser: Parser

    def __init__(self, lexer: Lexer, parser: Parser):
        self.lexer = lexer
        self.parser = parser

    def run(self, inputCode: str) -> AST:
        tokens: TokenOutput = self.tokenizeInner(inputCode)
        ast: AST = self.parseInner(tokens)
        return ast

    def tokenizeInner(self, inputCode: str) -> TokenOutput:
        return self.lexer.tokenize(inputCode)

    def parseInner(self, tokens: TokenOutput) -> AST:
        return self.parser.parse(tokens)

    @staticmethod
    @abstractmethod
    def name() -> str:
        return "A generic language"


class InterpretedLanguage(GenericLanguage):
    interpreter: Interpreter

    def __init__(self, lexer: Lexer, parser: Parser, interpreter: Interpreter):
        super().__init__(lexer, parser)
        self.interpreter = interpreter

    def run(self, inputCode: str, output: Optional[TextOutput] = None) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        ast: AST = super().run(inputCode)
        if output is None:
            output = TextOutput()
        return self.interpretInner(ast, output)

    def interpretInner(self, ast: AST, output: TextOutput) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        return self.interpreter.interpret(ast, output)

    @staticmethod
    @abstractmethod
    def name() -> str:
        return "An interpreted language"


class CompiledLanguage(GenericLanguage):
    compiler: Compiler
    interpreter: BytecodeInterpreter

    def __init__(self, lexer: Lexer, parser: Parser, compiler: Compiler,
                 interpreter: BytecodeInterpreter):
        super().__init__(lexer, parser)
        self.compiler = compiler
        self.interpreter = interpreter

    def compile(self, inputCode: str, outputFile: str = None) -> BytecodeFile:
        if outputFile is None:
            raise ValueError("No output file specified")
        ast: AST = super().run(inputCode)
        return self.compileInner(ast, outputFile, zlib.crc32(inputCode.encode("utf-8")))

    def run(self, inputCode: str, outputFile: str = None) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        try:
            file = self.compiler.bytecodeFile()
            file.read(readFile(outputFile, "buffer"), inputCode.encode("utf-8"))
        except (CRC32MismatchError, FileNotFoundError):
            file = self.compile(inputCode, outputFile)
        return self.interpreter.interpret(file)

    def compileInner(self, ast: AST, outputFile: str, codeCRC32: int) -> BytecodeFile:
        return self.compiler.compile(ast, outputFile, codeCRC32)

    @staticmethod
    @abstractmethod
    def name() -> str:
        return "A compiled language"
