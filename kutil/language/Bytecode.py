#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum
from typing import Iterator, Optional, BinaryIO, Callable

from kutil.io.file import readFile, writeFile

from kutil.buffer.ByteBuffer import ByteBuffer


class Instruction(Enum):  # Will be extended by subclasses
    pass


type InstructionGenerator = Iterator[Instruction, Optional[bytes]]
# A method for reading optional additional bytes
type InstructionParser = Callable[[Instruction, ByteBuffer], Optional[bytes]]


class Bytecode:
    instructionSize: int = 1
    instructionParser: InstructionParser = None
    instructionClass: type[Instruction] = Instruction

    buff: ByteBuffer
    instructionGenerator: Optional[InstructionGenerator]

    def __init__(self):
        self.buff = ByteBuffer()
        self.instructionGenerator = None

    def load(self, fileName: Optional[str] = None, file: Optional[BinaryIO] = None,
             buff: Optional[ByteBuffer] = None):
        if fileName is not None:
            buff = ByteBuffer(readFile(fileName, "bytearray"))
        elif file is not None:
            buff = ByteBuffer(file.read())
        elif buff is not None:
            pass
        else:
            raise ValueError("No argument given")
        self.instructionGenerator = self._generateInstructions(buff)

    def _generateInstructions(self, buff: ByteBuffer) -> InstructionGenerator:
        while len(buff) > 0:
            instruction: Instruction = self.instructionClass(
                int.from_bytes(buff.read(self.instructionSize), "big", signed=False)
            )
            additionalBytes: Optional[bytes] = self.instructionParser(instruction, buff)
            yield instruction, additionalBytes

    def _writeInstruction(self, buff: ByteBuffer, instruction: Instruction,
                          additionalBytes: Optional[bytes]):
        buff.write(instruction.value.to_bytes(self.instructionSize, "big", signed=False))
        if additionalBytes is not None:
            buff.write(additionalBytes)

    @property
    def next(self) -> tuple[Instruction, Optional[bytes]]:
        return next(self.instructionGenerator)

    def write(self, source: InstructionGenerator, fileName: Optional[str] = None,
              file: Optional[BinaryIO] = None, buff: Optional[ByteBuffer] = None):
        if buff is None:
            buff = ByteBuffer()

        for instruction, additionalBytes in source:
            self._writeInstruction(buff, instruction, additionalBytes)

        if fileName is not None:
            writeFile(fileName, buff.export())
        elif file is not None:
            file.write(buff.export())
        elif buff is not None:
            pass
        else:
            raise ValueError("No argument given")
