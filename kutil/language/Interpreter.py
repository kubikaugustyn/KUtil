#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC
from enum import Enum, unique

from kutil.buffer.TextOutput import TextOutput
from kutil.language.BytecodeFile import BytecodeFile

from kutil.language.Error import InterpreterError

from kutil.language.AST import AST


@unique
class InterpreterExitCode(Enum):
    OK = 0
    WARNING = 1
    ERROR = 2


class Interpreter(ABC):
    @abstractmethod
    def interpret(self, ast: AST, output: TextOutput) \
            -> tuple[InterpreterExitCode, InterpreterError | None]:
        """
        Interprets the given AST and returns the exit code. Never throws an error.
        :param ast: The code described by an AST
        :param output: The text output that serves as a console for the language
        :return: The exit code and the error (optional)
        """
        raise NotImplementedError("You must implement the interpret method")


class BytecodeInterpreter(ABC):
    @abstractmethod
    def interpret(self, file: BytecodeFile) \
            -> tuple[InterpreterExitCode, InterpreterError | None]:
        """
        Interprets the given compiled file and returns the exit code. Never throws an error.
        :param file: The file to be run
        :return: The exit code and the error (optional)
        """
        raise NotImplementedError("You must implement the interpret method")
