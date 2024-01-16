#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil.language.languages.javascript import parse
from kutil.language.languages.javascript.JSOptions import JSOptions

from kutil.language.AST import AST
from kutil.language.languages import Javascript


class TestJavascript(TestCase):
    def test_brain_fuck(self):
        js = Javascript()
        # Doesn't run the code, called run for subclass compatability
        ast: AST = parse("""
        var a = 8;
        var b = 7 // Comment test
        var c = a + b
        if (c !== 15) throw Error("Bad math")
        """, JSOptions())
        self.fail("Not implemented thus the test fails")
