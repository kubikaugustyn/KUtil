#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import doctest, os
from unittest import TestCase, main
from importlib import import_module
from colorama import Fore, Style


def getTestsFolder() -> str:
    import kutil
    kutilRoot = os.path.dirname(os.path.abspath(kutil.__file__))
    return os.path.join(os.path.dirname(kutilRoot), "test")


class Tester(TestCase):  # The test methods will be added dynamically
    failureException = RuntimeError


def _genFilesWalker(rootPath):
    for root, dirs, files in os.walk(rootPath, topdown=True):
        for name in files:
            fn, ext = os.path.splitext(name)
            filePath = os.path.abspath(os.path.join(root, fn))
            fileDir = os.path.dirname(filePath)
            if fileDir.endswith("__pycache__") or fn == "__init__" or ext != ".py":
                continue
            yield filePath
        # for name in dirs:
        #     print(os.path.join(root, name))


def genFiles():
    import kutil
    kutilRoot = os.path.dirname(os.path.abspath(kutil.__file__))
    for filePath in _genFilesWalker(kutilRoot):
        fileModuleLoc = "kutil" + filePath[len(kutilRoot):].replace(os.path.sep, ".")
        # print(fileModuleLoc)
        yield fileModuleLoc


def _testMethod(self: Tester, moduleName: str):
    # print(moduleName)
    module = import_module(moduleName)
    print(Fore.RED, end="")
    result = doctest.testmod(m=module, verbose=False)
    print(Style.RESET_ALL, end="")
    # if result.failed > 0:
    #     self.fail(f"{Fore.LIGHTRED_EX}Test of {moduleName} failed "
    #               f"with {result.failed} failures{Style.RESET_ALL}")


def testMethodFactory(moduleName: str):
    return lambda self: _testMethod(self, moduleName)


def initTests():
    for file in genFiles():
        testName = "test_" + file.replace(".", "_")

        setattr(Tester, testName, testMethodFactory(file))


# doctest.testmod(m=?)
initTests()

if __name__ == '__main__':
    main()
