#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Any

from kutil.language.Error import LexerError


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
