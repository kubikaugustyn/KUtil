#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum
from typing import Any

from kutil.language.Error import LexerError

from kutil.language.languages.paint_tryhard.jobs.boss import parseBossMethod, execBossInstruction, \
    BossInstruction
from kutil.language.languages.paint_tryhard.jobs.mathematician import parseMathematicianMethod, \
    execMathematicianInstruction, MathematicianInstruction
from kutil.language.languages.paint_tryhard.jobs.painter import parsePainterMethod, \
    execPainterInstruction, PainterInstruction


def parseJobMethod(workKind, code: str) -> tuple[Enum, Any]:
    from kutil.language.languages.paint_tryhard.PTLexer import WorkKind
    if workKind in (WorkKind.BOSS, WorkKind.THE_BOSS):
        return parseBossMethod(code)
    elif workKind == WorkKind.MATHEMATICIAN:
        return parseMathematicianMethod(code)
    elif workKind == WorkKind.PAINTER:
        return parsePainterMethod(code)
    raise LexerError(ValueError(f"Unknown work kind {workKind.name}"))


def execInstruction(self, workKind, instruction: int):
    from kutil.language.languages.paint_tryhard.PTLexer import WorkKind
    if workKind in (WorkKind.BOSS, WorkKind.THE_BOSS):
        execBossInstruction(self, BossInstruction(instruction))
    elif workKind == WorkKind.MATHEMATICIAN:
        execMathematicianInstruction(self, MathematicianInstruction(instruction))
    elif workKind == WorkKind.PAINTER:
        execPainterInstruction(self, PainterInstruction(instruction))
    else:
        raise ValueError(f"Unknown work kind {workKind.name}")
