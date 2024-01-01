#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil.language.languages import BrainFuck


class TestBrainFuck(TestCase):
    def test_brain_fuck(self):
        output = BrainFuck.fuck(
            "+[-->-[>>+>-----<<]<--<---]>-.>>>+.>>..+++[.>]<<<<.+++.------.<<-.>>>>+.",
            callPrint=False)
        self.assertEqual(output, "Hello, World!")
