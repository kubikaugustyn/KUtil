#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil.typing_help import singleton, anyattribute


@singleton
class Number:
    value: int = 0


@anyattribute("_vals")
class AnyAttr:
    _myBool: bool  # Note that this attribute should be set
    publicAttribute: int
    _vals: dict

    def __init__(self):
        self._myBool = True
        self._vals = {}

    """Implemented by @anyattribute("_vals") - _vals is the storage
    def __setattr__(self, key, value):
        print(f"Set {key} to {value}")
        self._vals[key] = value

    def __getattr__(self, key):
        return self._vals[key]"""

    @property
    def myBool(self) -> bool:
        return self._myBool

    @myBool.setter
    def myBool(self, newVal: bool):
        self._myBool = newVal


class TestTyping(TestCase):
    a: Number
    b: Number

    x: AnyAttr

    def setUp(self):
        self.a = Number()
        self.b = Number()

        self.x = AnyAttr()

    def test_singleton(self):
        self.a.value = 9
        self.assertEqual(self.b.value, 9)
        self.assertEqual(id(self.a), id(self.b))

    def test_any_attribute(self):
        self.x.sus = 69
        self.x.publicAttribute = 666
        self.x.myBool = False
        self.assertEqual(self.x.sus, 69)
        self.assertEqual(self.x.publicAttribute, 666)
        self.assertFalse(self.x.myBool)
        # The keys are iterated over, but only the ones of _vals
        self.assertEqual(set(iter(self.x)), {'sus'})
