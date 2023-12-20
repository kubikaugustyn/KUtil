#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.language.languages import BrainFuck

assert BrainFuck.fuck("+[-->-[>>+>-----<<]<--<---]>-.>>>+.>>..+++[.>]<<<<.+++.------.<<-.>>>>+.",
                      callPrint=False) == "Hello, World!"
