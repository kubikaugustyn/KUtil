#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Any

from kutil.language.Error import LexerError
from kutil.language.languages.paint_tryhard.PTInterpreter import Employee


@unique
class PainterInstruction(Enum):
    RESIZE_WIDTH = 0x00
    RESIZE_HEIGHT = 0x01
    FILL_WHOLE = 0x02
    CHANGE_BRUSH = 0x03
    RINSE_BRUSH = 0x04
    COLOR_BRUSH = 0x05
    MOVE_BRUSH_FROM_LEFT = 0x06
    MOVE_BRUSH_FROM_RIGHT = 0x07
    MOVE_BRUSH_FROM_TOP = 0x08
    MOVE_BRUSH_FROM_BOTTOM = 0x09
    MOVE_BRUSH_TO_HORIZONTAL_CENTER = 0x0A
    MOVE_BRUSH_TO_VERTICAL_CENTER = 0x0B
    MOVE_BRUSH_DOWN = 0x0C
    MOVE_BRUSH_UP = 0x0D
    MOVE_BRUSH_LEFT = 0x0E
    MOVE_BRUSH_RIGHT = 0x0F
    DRAW_SQUARE = 0x10  # Width and height depend on brush size
    START_LINE = 0x11
    END_LINE = 0x12


@unique
class Color(Enum):
    # NAME = (B, G, R)
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (0, 0, 255)
    GREEN = (0, 255, 0)
    BLUE = (255, 0, 0)
    CYAN = (255, 255, 0)
    MAGENTA = (255, 0, 255)
    YELLOW = (0, 255, 255)


def parsePainterMethod(code: str) -> tuple[PainterInstruction, Any]:
    if "1 PIXELS" in code:
        raise LexerError(ValueError(f"Bad English"))
    code = code.replace("1 PIXEL", "1 PIXELS")  # Make my life easier

    if code.startswith("RESIZE CANVAS TO BE "):
        # RESIZE CANVAS TO BE canvas_size PIXELS WIDE
        assert code.endswith(" PIXELS WIDE") or code.endswith(" PIXELS TALL")
        height: bool = code.endswith(" PIXELS TALL")
        value = code[20:-12]
        if height:
            return PainterInstruction.RESIZE_HEIGHT, value
        else:
            return PainterInstruction.RESIZE_WIDTH, value
    elif code.startswith("FILL CANVAS WITH "):
        # FILL CANVAS WITH "blue"
        return PainterInstruction.FILL_WHOLE, code[17:]
    elif code.startswith("CHANGE BRUSH FOR A ONE THAT IS "):
        # CHANGE BRUSH FOR A ONE THAT IS 1 PIXEL WIDE
        assert code.endswith(" PIXELS WIDE")
        return PainterInstruction.CHANGE_BRUSH, code[31:-12]
    elif code == "RINSE BRUSH":
        # RINSE BRUSH
        return PainterInstruction.RINSE_BRUSH, None
    elif code.startswith("TIP BRUSH IN "):
        # TIP BRUSH IN color PAINT
        assert code.endswith(" PAINT")
        return PainterInstruction.COLOR_BRUSH, code[13:-6]
    elif code == "MOVE BRUSH TO BE IN HORIZONTAL CENTER":
        # MOVE BRUSH TO BE IN HORIZONTAL CENTER
        return PainterInstruction.MOVE_BRUSH_TO_HORIZONTAL_CENTER, None
    elif code == "MOVE BRUSH TO BE IN VERTICAL CENTER":
        # MOVE BRUSH TO BE IN VERTICAL CENTER
        return PainterInstruction.MOVE_BRUSH_TO_VERTICAL_CENTER, None
    elif code.startswith("MOVE BRUSH TO BE "):
        # MOVE BRUSH TO BE 3 PIXELS FROM TOP
        assert (code.endswith(" PIXELS FROM LEFT") or
                code.endswith(" PIXELS FROM RIGHT") or
                code.endswith(" PIXELS FROM TOP") or
                code.endswith(" PIXELS FROM BOTTOM"))
        # Just a trick to extract the last word (e.g. 'LEFT')
        anchor = code[-code[::-1].index(" "):]
        value = code[17:-13 - len(anchor)]
        anchor = anchor.replace(" ", "_")
        return PainterInstruction[f"MOVE_BRUSH_FROM_{anchor}"], value
    elif code.startswith("MOVE BRUSH "):
        # MOVE BRUSH 1 PIXEL DOWN
        assert (code.endswith(" PIXELS LEFT") or
                code.endswith(" PIXELS RIGHT") or
                code.endswith(" PIXELS UP") or
                code.endswith(" PIXELS DOWN"))
        # Just a trick to extract the last word (e.g. 'LEFT')
        anchor = code[-code[::-1].index(" "):]
        value = code[11:-8 - len(anchor)]
        return PainterInstruction[f"MOVE_BRUSH_{anchor}"], value
    elif code == "DRAW ONE LITTLE SQUARE":
        # DRAW ONE LITTLE SQUARE
        return PainterInstruction.DRAW_SQUARE, None
    elif code == "PUT THE BRUSH DOWN":
        # PUT THE BRUSH DOWN
        return PainterInstruction.START_LINE, None
    elif code == "PUT THE BRUSH UP":
        # PUT THE BRUSH UP
        return PainterInstruction.END_LINE, None

    raise LexerError(ValueError(f"Invalid code: {ascii(code)}"))


def execPainterInstruction(self: Employee, instruction: PainterInstruction):
    if instruction == PainterInstruction.RESIZE_WIDTH:
        self.canvas.resize(self.resolve(self.stack.pop()), self.canvas.height)
    elif instruction == PainterInstruction.RESIZE_HEIGHT:
        self.canvas.resize(self.canvas.width, self.resolve(self.stack.pop()))
    elif instruction == PainterInstruction.FILL_WHOLE:
        color = self.resolve(self.stack.pop())
        color = Color[color.upper()]
        self.canvas.fill(color.value)
    else:
        self.throw(NotImplementedError(f"Invalid instruction: {instruction}"))
