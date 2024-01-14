#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Iterator, Optional

from kutil.language.Error import LexerError

from kutil.language.Lexer import Lexer
from kutil.language.Token import TokenOutput, Token


@unique
class WorkKind(Enum):
    # Work kind = "code string", "code end (token C_JOB_END)"
    BADASS = "BADASS", "?"
    BOSS = "BOSS", "?"
    CAMERAMAN = "CAMERAMAN", "?"
    CLOCK_READER = "CLOCK READER", "?"
    COMPOSER = "COMPOSER", "?"
    HISTORIAN = "HISTORIAN", "?"
    LIBRARIAN = "LIBRARIAN", "?"
    MATHEMATICIAN = "MATHEMATICIAN", "DESTROY THE CALCULATOR WITH A HYDRAULIC PRESS"
    MUSICIAN = "MUSICIAN", "?"
    PAINTER = "PAINTER", "THROW THE BRUSH OUT OF THE WINDOW"
    SLEEPER = "SLEEPER", "?"
    THE_BOSS = "THE BOSS", "KILL ALL THE EMPLOYEES"
    TIMEKEEPER = "TIMEKEEPER", "?"


def getWorkKind(name: str) -> WorkKind:
    for kind in WorkKind:
        if kind.value[0] == name:
            return kind
    raise ValueError(f"Work kind called {name} wasn't found")


@unique
class PTToken(Enum):  # Just the token kind
    START_CONTRACT = 1
    SET_WORK_KIND = 2
    SET_NAME = 3
    SET_EMPLOYEE = 4
    SET_ARGUMENT = 5
    SET_VARIABLE = 6
    SET_PROOF_OF_WORK = 7
    SET_CODE = 8
    # Code
    C_SET_VAR = 9
    C_GET_PROOF_OF_WORK = 10
    C_JOB_METHOD = 11  # Method special for work kind, saved as another Enum + Any data
    C_JOB_END = 12
    # Code end
    END_CONTRACT = 13


PT_COMMENT = "IGNORE "
PT_DIGITS = "0123456789"
PT_STR = '"'


class UnknownTokenError(LexerError):
    msg = "Unknown token"


class PTLexer(Lexer):
    def tokenizeInner(self, inputCode: str, output: TokenOutput) -> Iterator[Token]:
        workKind: WorkKind = WorkKind.BOSS
        isCode: bool = False

        lineIter = iter(inputCode.splitlines(keepends=False))
        for line in lineIter:
            if PT_COMMENT in line:
                line = line[:line.index(PT_COMMENT)]
            line = line.strip()
            if not line:
                continue
            # The token logic itself
            token = self.createJobToken(line, workKind) if isCode else self.createToken(
                line)
            if token is None:
                continue
            if token.kind == PTToken.SET_WORK_KIND:
                workKind = token.content
            elif token.kind == PTToken.SET_CODE:
                isCode = True
            elif token.kind == PTToken.C_JOB_END:
                isCode = False
            yield token

    @staticmethod
    def createToken(line) -> Optional[Token]:
        content = None
        if line == "START OF CONTRACT":
            kind = PTToken.START_CONTRACT
        elif line.startswith("WORK KIND IS "):
            kind = PTToken.SET_WORK_KIND
            content = getWorkKind(line[13:])
        elif line.startswith("NAME IS "):
            kind = PTToken.SET_NAME
            content = line[8:]
        elif line.startswith("HIS EMPLOYEE IS "):
            kind = PTToken.SET_EMPLOYEE
            content = line[16:]
        elif line.startswith("HE NEEDS TO KNOW "):
            assert " TO WORK WHICH IS " in line
            assert " BY DEFAULT" in line
            assert line.index(" TO WORK WHICH IS ") < line.index(" BY DEFAULT")
            arg_name = line[17:line.index(" TO WORK WHICH IS ")]
            def_val = line[line.index(" TO WORK WHICH IS ") + 18:-11]

            kind = PTToken.SET_ARGUMENT
            content = arg_name, def_val
        elif line.startswith("HE REMEMBERS "):
            assert " WHICH IS " in line
            assert " BY DEFAULT" in line
            assert line.index(" WHICH IS ") < line.index(" BY DEFAULT")
            var_name = line[13:line.index(" WHICH IS ")]
            def_val = line[line.index(" WHICH IS ") + 10:-11]

            kind = PTToken.SET_VARIABLE
            content = var_name, def_val
        elif line.startswith("HIS PROOF OF WORK CALLED "):
            assert " IS " in line
            assert " BY DEFAULT" in line
            assert line.index(" IS ") < line.index(" BY DEFAULT")
            return_name = line[25:line.index(" IS ")]
            def_val = line[line.index(" IS ") + 4:-11]

            kind = PTToken.SET_PROOF_OF_WORK
            content = return_name, def_val
        elif line == "JOB IS":
            kind = PTToken.SET_CODE
        elif line == "END OF CONTRACT":
            kind = PTToken.END_CONTRACT
        else:
            raise UnknownTokenError(ValueError(line))
        return Token(kind, content)

    @staticmethod
    def createJobToken(line, workKind: WorkKind) -> Optional[Token]:
        endStr = workKind.value[1]
        content = None
        if line == endStr:
            kind = PTToken.C_JOB_END
        elif line.startswith("REMEMBER THAT "):
            assert " IS " in line
            var_name = line[14:line.index(" IS ")]
            val = line[line.index(" IS ") + 4:]

            kind = PTToken.C_SET_VAR
            content = var_name, val
        elif line.startswith("REMEMBER PROOF OF WORK THAT "):
            assert " WORKED AS " in line
            employee_name = line[28:line.index(" WORKED AS ")]
            val = line[line.index(" WORKED AS ") + 11:]

            kind = PTToken.C_GET_PROOF_OF_WORK
            content = employee_name, val
        else:
            # I hope it's cached
            from kutil.language.languages.paint_tryhard.jobs import parseJobMethod

            kind = PTToken.C_JOB_METHOD
            try:
                content = parseJobMethod(workKind, line)
            except LexerError as e:
                raise e
            except Exception as e:
                raise LexerError([e, ValueError(f"Line: {ascii(line)}")])
        return Token(kind, content)
