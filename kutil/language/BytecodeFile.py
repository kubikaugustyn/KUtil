#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractproperty, ABC, abstractmethod
from enum import Enum, unique
from typing import Iterator, Optional, BinaryIO, Callable, Any

from kutil.buffer.DataBuffer import DataBuffer
from kutil.io.file import readFile, writeFile

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer


class CRC32MismatchError(AssertionError):
    msg = "Code mismatch - recompile the code"

    def __init__(self):
        super().__init__(self.msg)


@unique
class Instruction(Enum):  # Will be extended by subclasses
    pass


type InstructionGenerator = Iterator[tuple[Instruction, Optional[bytes]]]
# A method for reading optional additional bytes
type InstructionParser = Callable[[Instruction, ByteBuffer], Optional[bytes]]


class Bytecode(ABC):
    instructionSize: int = 1
    instructionParser: InstructionParser = None
    instructionClass: type[Instruction] = Instruction

    buff: ByteBuffer

    def __init__(self):
        self.buff = MemoryByteBuffer()

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
        self.buff = buff

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

    def __iter__(self):
        buff: ByteBuffer = self.buff.copy()
        buff.resetPointer()
        return self._generateInstructions(buff)

    def write(self, source: InstructionGenerator, fileName: Optional[str] = None,
              file: Optional[BinaryIO] = None, buff: Optional[ByteBuffer] = None):
        if buff is None:
            buff = self.buff  # ByteBuffer()
            buff.reset()

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


class BytecodeFile(ABC):
    bytecodeClass: type[Bytecode] = Bytecode

    @abstractmethod
    def write(self, buffer: ByteBuffer) -> None:
        """This is the method that should write the bytecode etc. into an ArrayBuffer,
         reading the data from self."""
        pass

    @abstractmethod
    def read(self, buffer: ByteBuffer, compareCrc32Data: Optional[bytes]) -> None:
        """This is the method that should read the bytecode etc. from an ArrayBuffer,
        storing the data in self.

        If compareCrc32Data is provided and mismatches the crc32 data of the file,
        an error is raised to let the programmer know new version of the bytecode file
        must be created (by compiling the code). The implementation depends on the subclass."""
        pass

    def writeValuePool(self, pool: list[Any], buff: ByteBuffer,
                       writer: Callable[[Any, DataBuffer], None] = None) -> None:
        """This is a method that writes the provided value pool into
        the buffer using the overwritten method writeValuePoolItem."""
        if writer is None:
            writer = self.writeValuePoolItem

        buff.write(len(pool).to_bytes(4, byteorder="big", signed=False))

        tmpBuff: ByteBuffer = MemoryByteBuffer()
        dataBuff: DataBuffer = DataBuffer(tmpBuff)
        for item in pool:
            writer(item, dataBuff)
            buff.write(len(tmpBuff).to_bytes(4, byteorder="big", signed=False))
            buff.write(tmpBuff.export())
            tmpBuff.reset()

    def readValuePool(self, buff: ByteBuffer, reader: Callable[[DataBuffer], Any] = None) \
            -> list[Any]:
        """This is a method that writes the provided value pool into
        the buffer using the overwritten method writeValuePoolItem."""
        if reader is None:
            reader = self.readValuePoolItem

        poolSize = int.from_bytes(buff.read(4), byteorder="big", signed=False)
        pool: list[Any] = [None] * poolSize

        tmpBuff: ByteBuffer = MemoryByteBuffer()
        dataBuff: DataBuffer = DataBuffer(tmpBuff)
        for i in range(poolSize):
            itemSize = int.from_bytes(buff.read(4), byteorder="big", signed=False)
            tmpBuff.write(buff.read(itemSize))
            pool[i] = reader(dataBuff)
            tmpBuff.reset()

        return pool

    @abstractmethod
    def writeValuePoolItem(self, item: Any, buff: DataBuffer) -> None:
        """This is the method that is called to write the item of the pool"""

    @abstractmethod
    def readValuePoolItem(self, buff: DataBuffer) -> Any:
        """This is the method that is called to read the item from the pool"""
