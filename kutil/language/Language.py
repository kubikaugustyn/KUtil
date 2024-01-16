#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import zlib
from abc import abstractmethod
from typing import Optional

from kutil.buffer.TextOutput import TextOutput
from kutil.io.file import readFile

from kutil.language.AST import AST
from kutil.language.BytecodeFile import BytecodeFile, CRC32MismatchError
from kutil.language.Options import Options, CompiledLanguageOptions, InterpretedLanguageOptions

from kutil.language.Token import TokenOutput

from kutil.language.Lexer import Lexer
from kutil.language.Parser import Parser
from kutil.language.Compiler import Compiler
from kutil.language.Interpreter import Interpreter, InterpreterExitCode, BytecodeInterpreter
from kutil.language.Error import InterpreterError


class GenericLanguage:
    optionsClass: type[Options] = Options

    lexer: Lexer
    parser: Parser

    def __init__(self, lexer: Lexer, parser: Parser):
        self.lexer = lexer
        self.parser = parser

    def run(self, inputCode: str, options: Options) -> AST:
        if options is None:
            options = self.optionsClass()
        tokens: TokenOutput = self.tokenizeInner(inputCode, options)
        ast: AST = self.parseInner(tokens, options)
        return ast

    def tokenizeInner(self, inputCode: str, options: Options) -> TokenOutput:
        return self.lexer.tokenize(inputCode, options)

    def parseInner(self, tokens: TokenOutput, options: Options) -> AST:
        return self.parser.parse(tokens, options)

    @staticmethod
    @abstractmethod
    def name() -> str:
        return "A generic language"


class InterpretedLanguage(GenericLanguage):
    interpreter: Interpreter

    def __init__(self, lexer: Lexer, parser: Parser, interpreter: Interpreter):
        super().__init__(lexer, parser)
        self.interpreter = interpreter

    def run(self, inputCode: str, options: InterpretedLanguageOptions,
            output: Optional[TextOutput] = None) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        ast: AST = super().run(inputCode, options)
        if output is None:
            output = TextOutput()
        return self.interpretInner(ast, output, options)

    def interpretInner(self, ast: AST, output: TextOutput, options: InterpretedLanguageOptions) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        return self.interpreter.interpret(ast, output, options)

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

    def compile(self, inputCode: str, options: CompiledLanguageOptions,
                outputFile: str = None) -> BytecodeFile:
        if outputFile is None:
            raise ValueError("No output file specified")
        ast: AST = super().run(inputCode, options)
        return self.compileInner(ast, outputFile, zlib.crc32(inputCode.encode("utf-8")), options)

    def run(self, inputCode: str, options: CompiledLanguageOptions, outputFile: str = None) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        try:
            file = self.compiler.bytecodeFile()
            file.read(readFile(outputFile, "buffer"), inputCode.encode("utf-8"))
        except (CRC32MismatchError, FileNotFoundError):
            file = self.compile(inputCode, options, outputFile)
        return self.interpreter.interpret(file)

    def compileInner(self, ast: AST, outputFile: str, codeCRC32: int,
                     options: CompiledLanguageOptions) -> BytecodeFile:
        return self.compiler.compile(ast, outputFile, codeCRC32, options)

    @staticmethod
    @abstractmethod
    def name() -> str:
        return "A compiled language"
