#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Any

from kutil.language.Error import LexerError
from kutil.language.languages.paint_tryhard.PTInterpreter import Employee


@unique
class MathematicianInstruction(Enum):
    CALC_ADD = 0x00
    CALC_SUBTRACT = 0x01
    CALC_MULTIPLY = 0x02
    CALC_DIVIDE = 0x03


def parseMathematicianMethod(code: str) -> tuple[MathematicianInstruction, Any]:
    if code.startswith("CALCULATE "):
        # CALCULATE result IS ADD n AND 1
        assert (" IS ADD " in code or " IS SUBTRACT " in code or
                " IS MULTIPLY " in code or " IS DIVIDE " in code)
        assert " AND " in code
        assert code.index(" IS ") < code.index(" AND ")

        if " IS ADD " in code:
            op = "ADD"
        elif " IS SUBTRACT " in code:
            op = "SUBTRACT"
        elif " IS MULTIPLY " in code:
            op = "MULTIPLY"
        else:
            op = "DIVIDE"

        resultName = code[10:code.index(f" IS {op} ")]
        first, second = code[code.index(f" IS {op} ") + 8:].split(" AND ")

        return MathematicianInstruction[f"CALC_{op}"], (resultName, first, second)

    raise LexerError(ValueError(f"Invalid code: {ascii(code)}"))


def execMathematicianInstruction(self: Employee, instruction: MathematicianInstruction):
    if instruction in (MathematicianInstruction.CALC_ADD,
                       MathematicianInstruction.CALC_SUBTRACT,
                       MathematicianInstruction.CALC_MULTIPLY,
                       MathematicianInstruction.CALC_DIVIDE):
        varName, a, b = self.stack.pop()
        a = self.resolve(self.resolve(a))  # Double resolve :-/
        b = self.resolve(self.resolve(b))

        if instruction == MathematicianInstruction.CALC_ADD:
            result = a + b
        elif instruction == MathematicianInstruction.CALC_SUBTRACT:
            result = a - b
        elif instruction == MathematicianInstruction.CALC_MULTIPLY:
            result = a * b
        else:
            result = a / b

        self.variables[varName] = result
    else:
        self.throw(NotImplementedError(f"Invalid instruction: {instruction}"))
