#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import Thread, Event
from typing import Self, Optional

from kutil import ThreadWaiter

from kutil.language.Stack import Stack
from kutil.language.languages.paint_tryhard.Canvas import Canvas
from kutil.language.languages.paint_tryhard.PTCompiler import PTBytecodeFile, ContractInfo, \
    PTBytecode, PTInstruction
from kutil.language.languages.paint_tryhard.PTLexer import WorkKind, PT_STR, PT_DIGITS


class Employee(Thread):
    info: ContractInfo
    file: PTBytecodeFile
    bytecode: PTBytecode
    interpreterWaiter: ThreadWaiter
    employees: dict[str, Self]
    waiter: ThreadWaiter
    stop: Event
    stack: Stack
    canvas: Canvas
    exceptions: list[Exception]
    doneWaiters: list[ThreadWaiter]
    arguments: dict[str, int | str]
    variables: dict[str, int | str]
    return_val: int | str | None

    def __init__(self, info: ContractInfo, file: PTBytecodeFile, bytecode: PTBytecode,
                 interpreterWaiter: ThreadWaiter, employees: dict[str, Self], canvas: Canvas,
                 exceptions: list[Exception]):
        Thread.__init__(self)
        self.name = f"Employee {info.name}"
        self.info = info
        self.file = file
        self.bytecode = bytecode
        self.interpreterWaiter = interpreterWaiter
        self.employees = employees
        self.waiter = ThreadWaiter()
        self.isRunning = Event()
        self.stop = Event()
        self.stack = Stack()
        self.exceptions = exceptions
        self.canvas = canvas
        self.doneWaiters = []
        self.arguments = {}
        for argName, argValue in self.info.arguments:
            self.arguments[argName] = argValue
        self.variables = {}
        for varName, varValue in self.info.variables:
            self.variables[varName] = varValue
        self.return_val = None if info.proofOfWork is None else info.proofOfWork[1]

    def throw(self, e: Exception):
        # This is the worst code I've ever written (I think)
        self.exit()
        self.exceptions.append(e)
        self.interpreterWaiter.release()

    def run(self) -> None:
        iterator = iter(self.bytecode)
        while not self.stop.is_set():
            if not self.isRunning.is_set():
                # print(self.info.name, "Skip")
                self.waiter.reset()
                self.waiter.wait(maxTime=.001)
                continue
            try:
                instruction, additionalBytes = next(iterator)
            except StopIteration:
                iterator = iter(self.bytecode)
                self.isRunning.clear()
                if self.info.workKind == WorkKind.THE_BOSS:
                    # print(self.info.name, "Boss break")
                    break  # The boss - entry point does stop after one iteration
                # print(self.info.name, "Non-boss repeat")

                for waiter in self.doneWaiters:
                    waiter.release()
                self.doneWaiters = []

                self.waiter.reset()
                self.waiter.wait(maxTime=.001)
                continue

            self.execInstruction(instruction, additionalBytes)

        # Exit all the sub-employees
        for name in self.info.employees:
            self.employees[name].exit()

        self.interpreterWaiter.release()

    def execInstruction(self, instruction: PTInstruction, additionalBytes: Optional[bytes]):
        additionalNumber = None
        if additionalBytes is not None:
            additionalNumber = int.from_bytes(additionalBytes, "big", signed=False)
        # Execute code here
        if instruction == PTInstruction.LOAD_CONST:
            self.stack.push(self.file.pool[additionalNumber])
        elif instruction == PTInstruction.SET_VAR:
            varVal = self.stack.pop()
            varName = self.stack.pop()
            self.setVar(varName, varVal)
        elif instruction == PTInstruction.GET_VAR:
            varName = self.stack.pop()
            self.stack.push(self.variables[varName])
        elif instruction == PTInstruction.DUPLICATE_STACK:
            val = self.stack.pop()
            self.stack.push(val)
            self.stack.push(val)
        elif instruction == PTInstruction.SET_PROOF_OF_WORK:
            val = self.stack.pop()
            self.return_val = val
        elif instruction == PTInstruction.GET_PROOF_OF_WORK:
            if not self.isBoss:
                self.throw(
                    ValueError(f"{self.info.name} cannot get proof of work without being a boss"))
            employeeName = self.stack.pop()
            varName = self.stack.pop()
            self.setVar(varName, self.employees[employeeName].return_val)
        elif instruction == PTInstruction.JOB_METHOD:
            # I hope the imported modules are cached
            from kutil.language.languages.paint_tryhard.jobs import execInstruction
            execInstruction(self, self.info.workKind, additionalNumber)
        else:
            self.throw(NotImplementedError(f"Unknown Instruction {instruction}"))

    @property
    def isBoss(self) -> bool:
        return self.info.workKind in (WorkKind.BOSS, WorkKind.THE_BOSS)

    def setVar(self, name: str, value: str | int):
        if name not in self.variables:
            self.throw(KeyError(f"{self.info.name} cannot find variable {name}"))
        if value is None:
            self.throw(ValueError(f"{self.info.name} cannot set a variable to nothing"))
        self.variables[name] = value

    def call(self):
        if self.isRunning.is_set():
            self.throw(ValueError(f"Cannot call {self.info.name} while he has work to do"))
        if self.stop.is_set():
            self.throw(ValueError(f"Cannot call {self.info.name} while he is going home"))
        self.isRunning.set()
        self.waiter.release()

    def exit(self):
        self.stop.set()
        self.waiter.release()
        for waiter in self.doneWaiters:
            waiter.release()  # Idk

    def waitUntilEmployeeDone(self, name: str):
        waiter: ThreadWaiter = ThreadWaiter()
        self.employees[name].doneWaiters.append(waiter)
        waiter.wait()

    def resolve(self, thing: str):
        if isinstance(thing, int):
            return thing

        if thing.startswith(PT_STR) and thing.endswith(PT_STR):
            return thing[len(PT_STR):-len(PT_STR)]
        elif all(map(lambda x: x in PT_DIGITS, thing)):
            return int(thing)
        elif thing in self.variables:
            return self.variables[thing]
        elif thing in self.arguments:
            return self.arguments[thing]
        else:
            self.throw(ValueError(f"{self.info.name} failed to resolve {thing}"))
