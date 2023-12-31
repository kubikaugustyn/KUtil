#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.typing import singleton, anyattribute


@singleton
class Number:
    value: int = 0


a = Number()
b = Number()
a.value = 9
assert b.value == 9
assert id(a) == id(b)


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


x = AnyAttr()
x.sus = 69
x.publicAttribute = 666
x.myBool = False
assert x.sus == 69
assert x.publicAttribute == 666
assert x.myBool is False
assert set(iter(x)) == {'sus'}  # The keys are iterated over, but only the ones of _vals
