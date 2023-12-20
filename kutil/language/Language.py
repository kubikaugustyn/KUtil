#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod
from typing import Any, Optional

from kutil.buffer.TextOutput import TextOutput

from kutil.language.AST import AST

from kutil.language.Token import TokenOutput

from kutil.language.Lexer import Lexer
from kutil.language.Parser import Parser
from kutil.language.Compiler import Compiler
from kutil.language.Interpreter import Interpreter, InterpreterExitCode
from kutil.language.Error import LanguageError, InterpreterError


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

    def interpretInner(self, ast: AST,output:TextOutput) -> tuple[InterpreterExitCode, InterpreterError | None]:
        return self.interpreter.interpret(ast,output)

    @staticmethod
    @abstractmethod
    def name() -> str:
        return "An interpreted language"


class CompiledLanguage(GenericLanguage):
    compiler: Compiler

    def __init__(self, lexer: Lexer, parser: Parser, compiler: Compiler):
        super().__init__(lexer, parser)
        self.compiler = compiler

    def run(self, inputCode: str) -> Any:
        ast: AST = super().run(inputCode)
        return self.compileInner(ast)

    def compileInner(self, ast: AST) -> Any:
        return self.compiler.compile(ast)

    @staticmethod
    @abstractmethod
    def name() -> str:
        return "A compiled language"
