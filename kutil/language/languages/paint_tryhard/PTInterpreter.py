#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil import InterpreterExitCode, InterpreterError, ThreadWaiter

from kutil.language.Interpreter import BytecodeInterpreter
from kutil.language.languages.paint_tryhard.Canvas import Canvas
from kutil.language.languages.paint_tryhard.Employee import Employee
from kutil.language.languages.paint_tryhard.PTCompiler import PTBytecodeFile
from kutil.language.languages.paint_tryhard.PTLexer import WorkKind


class PTInterpreter(BytecodeInterpreter):
    def interpret(self, file: PTBytecodeFile) \
            -> tuple[InterpreterExitCode, InterpreterError | None]:
        if not isinstance(file, PTBytecodeFile):
            return InterpreterExitCode.ERROR, InterpreterError(
                TypeError(f"The provided file is invalid"))
        if len(file.contracts) == 0:
            return InterpreterExitCode.OK, None
        print(f"Interpret {file}")

        employees: dict[str, Employee] = {}
        exceptions: list[Exception] = []
        waiter: ThreadWaiter = ThreadWaiter()
        canvas = Canvas()
        canvas.start()

        try:
            usedEmployees: dict[str, bool] = {}

            for info, bytecode in file.getContracts():
                if info.name in employees:
                    return InterpreterExitCode.ERROR, InterpreterError(
                        ValueError(f"The provided employee {info.name} already exists"))
                employees[info.name] = Employee(info, file, bytecode, waiter, employees, canvas,
                                                exceptions)
                usedEmployees[info.name] = False

            for name, employee in employees.items():
                for subEmployeeName in employee.info.employees:
                    if usedEmployees[subEmployeeName]:
                        raise ValueError(f"The employee {subEmployeeName} is already in use")
                    usedEmployees[subEmployeeName] = True
                if employee.info.workKind == WorkKind.THE_BOSS:
                    if usedEmployees[name]:
                        raise ValueError(f"The boss {name} is already in use")
                    usedEmployees[name] = True
            if not all(usedEmployees.values()):
                unusedEmployees: list[str] = list(
                    map(
                        lambda keyVal: keyVal[0],
                        filter(lambda keyVal: not keyVal[1], usedEmployees.items())
                    )
                )
                raise ValueError(f"Not all employees are used: {', '.join(unusedEmployees)}")

            for employee in employees.values():
                employee.start()

            for employee in employees.values():
                if employee.info.workKind == WorkKind.THE_BOSS:
                    employee.call()  # Run the entry point
                    break

            while True:
                if len(exceptions) > 0:
                    raise exceptions[0]
                # Wait for the work to finish
                if not any(map(lambda employee: employee.is_alive(), employees.values())):
                    break
                waiter.wait()
        except Exception as e:
            for employee in employees.values():
                employee.exit()
                employee.waiter.reset()
            canvas.exit()
            return InterpreterExitCode.ERROR, InterpreterError(e)

        canvas.exit()

        return InterpreterExitCode.OK, None
