#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Any

from kutil.language.Error import LexerError


@unique
class BossInstruction(Enum):
    SET_EMPLOYEE_ARGUMENT_VAR = 0x00
    SET_EMPLOYEE_ARGUMENT_LITERAL = 0x01
    RUN_EMPLOYEE = 0x02
    WAIT_UNTIL_EMPLOYEE_DONE = 0x03
    STORE_EMPLOYEE_RETURN_VALUE = 0x04


def parseBossMethod(code: str) -> tuple[BossInstruction, Any]:
    if code.startswith("TELL "):
        if code.endswith(" TO START WORKING"):
            # TELL Bob Counter TO START WORKING
            name = code[5:code.index(" TO START WORKING")]
            return BossInstruction.RUN_EMPLOYEE, name
        else:
            # TELL Bob Counter THAT n IS redraw_count
            assert " THAT " in code and " IS " in code
            assert code.index(" THAT ") < code.index(" IS ")
            name = code[5:code.index(" THAT ")]
            argName = code[code.index(" THAT ") + 6:code.index(" IS ")]
            value = code[code.index(" IS ") + 4:]
            from kutil.language.languages.paint_tryhard.PTLexer import PT_STR, PT_DIGITS
            if value.startswith(PT_STR) or value[0] in PT_DIGITS:
                return BossInstruction.SET_EMPLOYEE_ARGUMENT_LITERAL, (name, argName, value)
            return BossInstruction.SET_EMPLOYEE_ARGUMENT_VAR, (name, argName, value)
    elif code.startswith("WAIT UNTIL "):
        # WAIT UNTIL Bob Counter IS DONE
        assert code.endswith(" IS DONE")
        name = code[11:code.index(" IS DONE")]
        return BossInstruction.WAIT_UNTIL_EMPLOYEE_DONE, name
    elif code.startswith("REMEMBER PROOF OF WORK THAT "):
        # REMEMBER PROOF OF WORK THAT Bob Counter WORKED AS redraw_count
        assert " WORKED AS " in code
        name = code[28:code.index(" WORKED AS ")]
        varName = code[code.index(" WORKED AS ") + 11:]
        return BossInstruction.STORE_EMPLOYEE_RETURN_VALUE, (name, varName)
    raise LexerError(ValueError(f"Invalid code: {ascii(code)}"))
