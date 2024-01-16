#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.io.file import readFile
from kutil.language.BytecodeFile import BytecodeFile
from kutil.language.Options import CompiledLanguageOptions

from kutil.language.languages.paint_tryhard.PaintTryhard import PaintTryhard

if __name__ == '__main__':
    pt = PaintTryhard()
    # file: BytecodeFile = pt.compile(readFile("smiley.pt", "text"), "smiley.ptc")
    # print(file)
    # pt.interpreter.interpret(file)
    exitCode, error = pt.run(readFile("smiley.pt", "text"), CompiledLanguageOptions(), "smiley.ptc")
    print(f"Process finished with exit code {exitCode.name}")
    if error is not None:
        raise error
