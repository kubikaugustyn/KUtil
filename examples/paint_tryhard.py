#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.io.file import readFile

from kutil.language.languages.paint_tryhard.PaintTryhard import PaintTryhard

if __name__ == '__main__':
    pt = PaintTryhard()
    pt.run(readFile("smiley.pt", "text"))
