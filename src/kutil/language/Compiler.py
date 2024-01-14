#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC

from kutil.buffer.ByteBuffer import ByteBuffer

from kutil.io.file import writeFile
from kutil.language.AST import AST
from kutil.language.BytecodeFile import BytecodeFile


class Compiler(ABC):
    bytecodeFile: type[BytecodeFile] = BytecodeFile

    def compile(self, ast: AST, outputFile: str, codeCRC32: int) -> BytecodeFile:
        """
        Compiles the given AST into Any data structure
        :param ast: The code described by an AST
        :param outputFile: The output file to write to
        :param codeCRC32: The CRC32 checksum of the source code file
        :return: The bytecode file
        """
        file = self.compileInner(ast, codeCRC32)
        buff: ByteBuffer = ByteBuffer()
        file.write(buff)
        writeFile(outputFile, buff.export())
        return file

    @abstractmethod
    def compileInner(self, ast: AST, codeCRC32: int) -> BytecodeFile:
        """
        Compiles the given AST into Any data structure
        :param ast: The code described by an AST
        :return: The bytecode file
        """
        raise NotImplementedError("You must implement the compile method")
