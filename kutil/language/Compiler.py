#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer

from kutil.io.file import writeFile
from kutil.language.AST import AST
from kutil.language.BytecodeFile import BytecodeFile
from kutil.language.Options import CompiledLanguageOptions


class Compiler(ABC):
    bytecodeFile: type[BytecodeFile] = BytecodeFile

    def compile(self, ast: AST, outputFile: str, codeCRC32: int, options: CompiledLanguageOptions) \
            -> BytecodeFile:
        """
        Compiles the given AST into Any data structure
        :param ast: The code described by an AST
        :param outputFile: The output file to write to
        :param codeCRC32: The CRC32 checksum of the source code file
        :param options: The options for the compiler
        :return: The bytecode file
        """
        file = self.compileInner(ast, codeCRC32, options)
        buff: ByteBuffer = MemoryByteBuffer()
        file.write(buff)
        writeFile(outputFile, buff.export())
        return file

    @abstractmethod
    def compileInner(self, ast: AST, codeCRC32: int, options: CompiledLanguageOptions) \
            -> BytecodeFile:
        """
        Compiles the given AST into Any data structure
        :param ast: The code described by an AST
        :param codeCRC32: The CRC32 checksum of the source code file
        :param options: The options for the compiler
        :return: The bytecode file
        """
        raise NotImplementedError("You must implement the compile method")
