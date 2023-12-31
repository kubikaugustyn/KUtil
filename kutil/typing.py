"""
This is the typing module of KUtil containing the singleton decorator (just now).
"""
#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import inspect
import sys
from typing import Optional, overload, Iterable


# Class decorators
def singleton(cls):
    """
    A decorator, making a class be able to only have one instance. If you try to instantiate it multiple times,
    the same instance will be returned.

    >>> @singleton
    ... class Number:
    ...     value: int = 0
    >>> a = Number()
    >>> b = Number()
    >>> a.value = 9
    >>> b.value
    9
    >>> id(a) == id(b)
    True
    """
    # https://stackoverflow.com/questions/42237752/single-instance-of-class-in-python
    instances = {}
    originalNew = cls.__new__

    def _singleton(_, *args, **kw):
        if cls not in instances:
            # instances[cls] = cls(*args, **kw)
            instances[cls] = originalNew(cls, *args, **kw)
        return instances[cls]

    cls.__new__ = _singleton
    return cls


@overload
def anyattribute(cls: type): ...


@overload
def anyattribute(attributeStorage: str): ...


def anyattribute(attributeStorageOrCls: str | type):
    """
    A decorator, making a class able to have any attribute names. Optionally you can provide attribute storage
    attribute name, which will make the class self-sustainable without any more configuration, just make sure to
    also define the attribute storage attribute.

    It makes mutating defined attributes (either annotated attribute or a getter and setter pair) possible
    and provides fallback for any other attribute name.

    Note that you need to make sure you won't accidentally change defined attribute
    while wanting to change the fallback attribute's item.

    For more info about this decorator, see the AnyAttr class
    in the test file: https://github.com/kubikaugustyn/KUtil/blob/main/test/typing_test.py
    """
    if isinstance(attributeStorageOrCls, str):
        attributeStorage = attributeStorageOrCls
        returnWrapper = True
    elif inspect.isclass(attributeStorageOrCls):
        attributeStorage = None
        returnWrapper = False
    else:
        raise ValueError("Cannot use the anyattribute decorator without a class "
                         "and optional attribute storage property name")

    # print("Attribute storage:", attributeStorage)

    def wrapper(cls):
        clsVars = vars(cls)
        # print("Class:", clsVars)

        # Check item manipulators
        if ("__getitem__" in clsVars or
                "__setitem__" in clsVars or
                "__delitem__" in clsVars):
            raise ValueError("AnyAttribute class must not implement any item setter or getter")

        oldSetAttr = getattr(cls, "__setattr__") if "__setattr__" in clsVars else None
        oldGetAttr = getattr(cls, "__getattr__") if "__getattr__" in clsVars else None
        oldDelAttr = getattr(cls, "__delattr__") if "__delattr__" in clsVars else None
        oldIter = getattr(cls, "__iter__") if "__iter__" in clsVars else None

        if attributeStorage is not None:
            # Check attribute storage name
            if (not attributeStorage.startswith("_") or
                    attributeStorage.startswith("__") or
                    attributeStorage.endswith("_")):
                raise ValueError("AnyAttribute class with attribute storage set must define the attribute storage name"
                                 " that is private, but not too much (e.g. _vals, but not __vals_)")
            # Check storage attribute itself
            if attributeStorage not in cls.__annotations__:
                raise ValueError("AnyAttribute class with attribute storage set must define the attribute storage")
            # Check attribute manipulators
            if "__getattr__" in clsVars or "__delattr__" in clsVars:
                raise ValueError("AnyAttribute class with attribute storage set must not implement"
                                 " any attribute deleter or getter")
        else:
            # Check attribute manipulators
            if ("__setattr__" not in clsVars or
                    "__getattr__" not in clsVars or
                    "__delattr__" not in clsVars):
                raise ValueError("AnyAttribute class must implement attribute setter and getter")

        class _AnyAttributeHelper(cls, Iterable):
            def __init__(self, *args, **kwargs):
                if attributeStorage is not None:
                    super(cls, self).__setattr__(attributeStorage, {})
                super().__init__(*args, **kwargs)

            def __getitem__(self, key):
                return self.__getattr__(key)

            def __setitem__(self, key, value):
                self.__setattr__(key, value)

            def __delitem__(self, key):
                self.__delattr__(key)

            def __contains__(self, name) -> bool:
                try:
                    if attributeStorage is None:
                        oldGetAttr(self, name)
                        return True
                    return name in getattr(self, attributeStorage)
                except KeyError:
                    return False

            def __iter__(self):
                if attributeStorage is None:
                    if oldIter:
                        return oldIter(self)
                    raise TypeError("AnyAttribute class isn't iterable")
                return iter(getattr(self, attributeStorage))

            def __getattr__(self, name):
                if attributeStorage is None:
                    return oldGetAttr(self, name)
                return getattr(self, attributeStorage)[name]

            def __setattr__(self, name, value):
                if name in self.__annotations__:  # An annotated property
                    super(cls, self).__setattr__(name, value)
                elif name in clsVars and isinstance(clsVars[name], property):  # A property setter + getter
                    # https://stackoverflow.com/questions/40357535/call-a-property-setter-dynamically
                    assert clsVars[name].fset is not None, "You must implement a getter and setter pair"
                    clsVars[name].fset(self, value)
                else:  # Set property of any name
                    if attributeStorage is None or oldSetAttr is not None:
                        oldSetAttr(self, name, value)
                    else:
                        getattr(self, attributeStorage)[name] = value

            def __delattr__(self, name):
                if name in self.__annotations__:  # An annotated property
                    raise AttributeError
                elif name in clsVars and isinstance(clsVars[name], property):  # A property setter + getter
                    raise AttributeError
                else:  # Set property of any name
                    if attributeStorage is None or oldDelAttr is not None:
                        oldDelAttr(self, name)
                    else:
                        del getattr(self, attributeStorage)[name]

            def __repr__(self) -> str:
                # return f"<kutil.typing.anyattribute._AnyAttributeHelper of {repr(cls)} at {hex(id(self))}>"
                # return f"<kutil.typing.anyattribute._AnyAttributeHelper of {cls.__repr__(self)} at {hex(id(self))}>"
                return cls.__repr__(self)

        # print("Updated class:", vars(_AnyAttributeHelper))

        # def _anyattribute(*args, **kwargs):
        #     instance = _AnyAttributeHelper(*args, **kwargs)
        # print("Instance:", vars(instance))
        # return instance

        # return _anyattribute
        return _AnyAttributeHelper

    if returnWrapper:
        return wrapper
    else:
        return wrapper(cls=attributeStorageOrCls)


# Function decorators
"""def export(fn):
    "-""
    A decorator making a function exported from the file
    "-""
    # https://stackoverflow.com/questions/44834/what-does-all-mean-in-python
    mod = sys.modules[fn.__module__]
    if hasattr(mod, '__all__'):
        mod.__all__.append(fn.__name__)
    else:
        mod.__all__ = [fn.__name__]
    return fn"""
