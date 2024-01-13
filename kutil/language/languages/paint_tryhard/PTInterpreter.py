#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil import InterpreterExitCode, InterpreterError

from kutil.language.Interpreter import BytecodeInterpreter
from kutil.language.languages.paint_tryhard.PTCompiler import PTBytecodeFile


class PTInterpreter(BytecodeInterpreter):
    def interpret(self, file: PTBytecodeFile) \
            -> tuple[InterpreterExitCode, InterpreterError | None]:
        if not isinstance(file, PTBytecodeFile):
            return InterpreterExitCode.ERROR, InterpreterError(
                TypeError(f"The provided file is invalid"))
        if len(file.contracts) == 0:
            return InterpreterExitCode.OK, None
        print(f"Interpret {file}")

        for info, bytecode in file.getContracts():
            pass

        return InterpreterExitCode.OK, None
