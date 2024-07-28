#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import unique, Enum
from typing import Any, Optional, Generator, Iterator

from kutil.buffer.DataBuffer import DataBuffer
from kutil.language.Error import CompilerError

from kutil import ByteBuffer, MemoryByteBuffer
from kutil.language.AST import AST, ASTNode
from kutil.language.BytecodeFile import InstructionGenerator, Instruction, Bytecode, BytecodeFile, \
    CRC32MismatchError
from kutil.language.Compiler import Compiler
from kutil.language.Options import CompiledLanguageOptions
from kutil.language.languages.paint_tryhard.PTLexer import WorkKind, PT_DIGITS, PT_STR
from kutil.language.languages.paint_tryhard.PTParser import PTNode, ContractCodeNode


@unique
class PTInstruction(Instruction):  # Stack #x --> xth item from the top of the stack
    LOAD_CONST = 0x00  # Push the const at the provided uint32 index to the stack
    DUPLICATE_STACK = 0x01  # Push stack #1 to the stack, duplicating the value on the stack
    SET_VAR = 0x02  # Set the var (stack #2) to a value (stack #1)
    GET_VAR = 0x03  # Get the var (stack #1) and add it to the stack
    SET_PROOF_OF_WORK = 0x04  # Set the proof of work to a value (stack #1)
    GET_PROOF_OF_WORK = 0x05  # Assign the pow of an employee (stack #1) to a variable (stack #2)
    JOB_METHOD = 0x06  # Method special for work kind, saved as another Enum + Any data (stack #1)


def PTInstructionParser(self: Bytecode, instruction: PTInstruction, buff: ByteBuffer) \
        -> Optional[bytes]:
    if instruction == PTInstruction.LOAD_CONST:
        return buff.read(4)
    elif instruction == PTInstruction.JOB_METHOD:
        return buff.read(1)
    return None


class PTBytecode(Bytecode):
    instructionClass = PTInstruction
    instructionParser = PTInstructionParser


@unique
class PoolValueKind(Enum):
    STRING = 0x00
    NUMBER = 0x01
    TUPLE = 0x02


class ContractInfo:
    workKind: Optional[WorkKind]
    name: Optional[str]
    arguments: list[tuple[str, str]]
    variables: list[tuple[str, str]]
    employees: list[str]
    proofOfWork: Optional[tuple[str, str]]

    def __init__(self):
        self.workKind = None
        self.name = None
        self.arguments = []
        self.variables = []
        self.employees = []
        self.proofOfWork = None

    def write(self, byteBuff: ByteBuffer):
        """Not readable? Well, it works..."""
        buff: DataBuffer = DataBuffer(byteBuff)
        buff.writeUInt8(list(WorkKind).index(self.workKind))
        buff.writeString(self.name, 1)
        buff.writeUInt8(len(self.arguments))
        for argName, argDefVal in self.arguments:
            buff.writeString(argName, 1)
            buff.writeString(argDefVal, 1)
        buff.writeUInt8(len(self.variables))
        for varName, varDefVal in self.variables:
            buff.writeString(varName, 1)
            buff.writeString(varDefVal, 1)
        buff.writeUInt8(len(self.employees))
        for employeeName in self.employees:
            buff.writeString(employeeName, 1)
        buff.writeBool(self.proofOfWork is not None)
        if self.proofOfWork is not None:
            buff.writeString(self.proofOfWork[0], 1)
            buff.writeString(self.proofOfWork[1], 1)

    def read(self, byteBuff: ByteBuffer):
        """Not readable? Well, it works..."""
        buff: DataBuffer = DataBuffer(byteBuff)
        self.workKind = list(WorkKind)[buff.readUInt8()]
        self.name = buff.readString(1)
        argumentAmount = buff.readUInt8()
        self.arguments = []
        for _ in range(argumentAmount):
            argName = buff.readString(1)
            argDefVal = buff.readString(1)
            self.arguments.append((argName, argDefVal))
        varAmount = buff.readUInt8()
        self.variables = []
        for _ in range(varAmount):
            varName = buff.readString(1)
            varDefVal = buff.readString(1)
            self.variables.append((varName, varDefVal))
        self.employees = []
        for _ in range(buff.readUInt8()):
            self.employees.append(buff.readString(1))
        self.proofOfWork = None
        if buff.readBool():
            self.proofOfWork = (buff.readString(1), buff.readString(1))


class PTBytecodeFile(BytecodeFile):
    bytecodeClass = PTBytecode

    pool: list[Any]
    contracts: list[tuple[ByteBuffer, PTBytecode]]
    crc32: int

    def __init__(self):
        self.pool = []
        self.contracts = []
        self.crc32 = 0

    def addContract(self) -> tuple[ByteBuffer, PTBytecode]:
        buff: ByteBuffer = MemoryByteBuffer()
        bytecode: PTBytecode = PTBytecode()
        self.contracts.append((buff, bytecode))
        return buff, bytecode

    def getContracts(self) -> Iterator[tuple[ContractInfo, PTBytecode]]:
        for contractBuff, bytecode in self.contracts:
            info: ContractInfo = ContractInfo()
            info.read(contractBuff)
            yield info, bytecode

    def read(self, buffer: ByteBuffer, compareCrc32Data: Optional[bytes] = None) -> None:
        dBuff: DataBuffer = DataBuffer(buffer)

        self.crc32 = dBuff.readUInt32()
        if compareCrc32Data is not None:
            buffer.back(4)
            if not dBuff.readAndCompareCRC32(compareCrc32Data):
                raise CRC32MismatchError

        self.pool = self.readValuePool(buffer)

        contractCount: int = dBuff.readUInt32()
        contracts: list[tuple[ByteBuffer, PTBytecode]] = []
        for _ in range(contractCount):
            infoSize: int = dBuff.readUInt32()
            info: ByteBuffer = ByteBuffer(buffer.read(infoSize))
            bytecodeSize: int = dBuff.readUInt32()
            bytecode: PTBytecode = PTBytecode()
            bytecode.load(buff=ByteBuffer(buffer.read(bytecodeSize)))
            contracts.append((info, bytecode))
        self.contracts = contracts

    def write(self, buffer: ByteBuffer) -> None:
        dBuff: DataBuffer = DataBuffer(buffer)

        dBuff.writeUInt32(self.crc32)

        self.writeValuePool(self.pool, buffer)

        dBuff.writeUInt32(len(self.contracts))
        for info, bytecode in self.contracts:
            dBuff.writeUInt32(len(info))
            buffer.write(info.export())
            dBuff.writeUInt32(len(bytecode.buff))
            buffer.write(bytecode.buff.export())

    def readValuePoolItem(self, buff: DataBuffer) -> Any:
        kind: PoolValueKind = PoolValueKind(buff.buff.readByte())
        if kind == PoolValueKind.STRING:
            return buff.readString(2)
        if kind == PoolValueKind.NUMBER:
            return buff.readUInt32()
        if kind == PoolValueKind.TUPLE:
            size = buff.readUInt32()
            items = []
            for _ in range(size):
                items.append(self.readValuePoolItem(buff))
            return tuple(items)
        else:
            raise TypeError(f"Unsupported type {kind}")

    def writeValuePoolItem(self, item: Any, buff: DataBuffer) -> None:
        if isinstance(item, str):
            buff.buff.writeByte(PoolValueKind.STRING.value)
            buff.writeString(item, 2)
        elif isinstance(item, int):
            buff.buff.writeByte(PoolValueKind.NUMBER.value)
            buff.writeUInt32(item)
        elif isinstance(item, tuple):
            buff.buff.writeByte(PoolValueKind.TUPLE.value)
            buff.writeUInt32(len(item))
            for val in item:
                self.writeValuePoolItem(val, buff)
        else:
            raise TypeError(f"Unsupported type {type(item)}")


class PTCompiler(Compiler):
    bytecodeFile = PTBytecodeFile

    def compileInner(self, ast: AST, codeCRC32: int,
                     options: CompiledLanguageOptions) -> PTBytecodeFile:
        file: PTBytecodeFile = PTBytecodeFile()
        file.crc32 = codeCRC32
        self.compileCode(ast, file)
        return file

    def compileCode(self, ast: AST, file: PTBytecodeFile):
        for contract in ast.rootNodes():
            nodes = ast.getNodes(contract.data)
            self.compileContract(ast, nodes, file)

    def compileContract(self, ast: AST, nodes: list[ASTNode],
                        file: PTBytecodeFile):
        headBuffer, bytecode = file.addContract()
        codeNodes = []

        info: ContractInfo = ContractInfo()

        for node in nodes:
            if node.type == PTNode.CONTRACT_CODE:
                assert isinstance(node, ContractCodeNode)
                codeNodes = ast.getNodes(node.data)
            elif node.type == PTNode.WORK_KIND:
                info.workKind = node.data
            elif node.type == PTNode.NAME:
                info.name = node.data
            elif node.type == PTNode.VARIABLE:
                info.variables.append(node.data)
            elif node.type == PTNode.ARGUMENT:
                info.arguments.append(node.data)
            elif node.type == PTNode.EMPLOYEES:
                info.employees.extend(node.data)
            elif node.type == PTNode.PROOF_OF_WORK:
                info.proofOfWork = node.data
            else:
                raise CompilerError(ValueError(f"Unknown node type {node.type}"))

        info.write(headBuffer)

        bytecode.write(self.compileContractCode(codeNodes, file), buff=bytecode.buff)

    def compileContractCode(self, nodes: list[ASTNode],
                            file: PTBytecodeFile) -> InstructionGenerator:
        for node in nodes:
            if node.type == PTNode.C_SET_VAR:
                yield from self.readFromPool(node.data[0], file)  # Var name
                yield from self.parseCodeValue(node.data[1], file)  # Var value
                yield PTInstruction.SET_VAR, None
            elif node.type == PTNode.C_GET_PROOF_OF_WORK:
                yield from self.readFromPool(node.data[1], file)  # Target variable
                yield from self.readFromPool(node.data[0], file)  # Source employee name
                yield PTInstruction.GET_PROOF_OF_WORK, None
            elif node.type == PTNode.C_JOB_METHOD:
                if node.data[1] is not None:
                    yield from self.readFromPool(node.data[1], file)  # Method info
                methodInstruction: Enum = node.data[0]  # Method index of work kind
                yield PTInstruction.JOB_METHOD, bytes([methodInstruction.value])
            else:
                raise CompilerError(ValueError(f"Unsupported node type {node.type} - {node}"))

    @staticmethod
    def readFromPool(value: Any, file: PTBytecodeFile) -> InstructionGenerator:
        """Stores a value in the pool, returning an instruction
         that loads the value from the pool"""
        if value not in file.pool:
            if not value:
                raise ValueError(f"No value: {value}")
            file.pool.append(value)
        yield PTInstruction.LOAD_CONST, file.pool.index(value).to_bytes(4, "big", signed=False)

    def parseCodeValue(self, value: str, file: PTBytecodeFile) -> InstructionGenerator:
        """Parses the value, storing it in the pool properly and returning an instruction
         that loads the value from the pool"""
        if value.startswith(PT_STR) and value.endswith(PT_STR):
            # String
            yield from self.readFromPool(value[len(PT_STR):-len(PT_STR)], file)
        elif all(map(lambda x: x in PT_DIGITS, value)):
            # Number
            yield from self.readFromPool(int(value), file)
        else:
            # Variable name
            yield from self.readFromPool(value, file)
            yield PTInstruction.GET_VAR, None
