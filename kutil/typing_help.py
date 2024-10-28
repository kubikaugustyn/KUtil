"""
This is the typing module of KUtil containing helpers for typing.
"""
#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import inspect
import sys
from abc import ABCMeta
from typing import *
from functools import wraps

from kutil.runtime import getCallerFrame

# Exported things
from frozenlist import FrozenList
from itertools import chain
from copy import deepcopy


# Class decorators
def singleton(cls):
    """
    A decorator, making a class be able to only have one instance. If you try to instantiate it
    multiple times, the same instance will be returned.

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
    instances: dict[type, object] = {}
    initialized: set[type] = set()
    originalNew = cls.__new__
    originalInit = cls.__init__

    def _singleton(_, *args, **kw):
        if cls not in instances:
            # instances[cls] = cls(*args, **kw)
            instances[cls] = originalNew(cls, *args, **kw)
        return instances[cls]

    def _init_handler(_, *args, **kw):
        if len(args) > 0 or len(kw) > 0:
            count: int = len(args) + len(kw)
            raise TypeError(f"A singleton's __init__ must take 0 arguments, "
                            f"but {count} {'were' if count > 1 else 'was'} given.")

        if cls not in initialized:
            initialized.add(cls)
            originalInit(cls)

        return None

    cls.__new__ = _singleton
    cls.__init__ = _init_handler
    return cls


@overload
def anyattribute(cls: type): ...


@overload
def anyattribute(attributeStorage: str): ...


def anyattribute(attributeStorageOrCls: str | type):
    """
    A decorator, making a class able to have any attribute names. Optionally you can provide
    attribute storage attribute name, which will make the class self-sustainable without any
    more configuration, just make sure to also define the attribute storage attribute.

    It makes mutating defined attributes (either annotated attribute or a getter and setter pair)
    possible and provides fallback for any other attribute name.

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
                raise ValueError("AnyAttribute class with attribute storage set must define the "
                                 "attribute storage name that is private, but not"
                                 " too much (e.g. _vals, but not __vals_)")
            # Check storage attribute itself
            if attributeStorage not in cls.__annotations__:
                raise ValueError("AnyAttribute class with attribute storage"
                                 " set must define the attribute storage attribute")
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
                elif name in clsVars and isinstance(clsVars[name],
                                                    property):  # A property setter + getter
                    # https://stackoverflow.com/questions/40357535/call-a-property-setter-dynamically
                    assert clsVars[
                               name].fset is not None, "You must implement a getter and setter pair"
                    clsVars[name].fset(self, value)
                else:  # Set property of any name
                    if attributeStorage is None or oldSetAttr is not None:
                        oldSetAttr(self, name, value)
                    else:
                        getattr(self, attributeStorage)[name] = value

            def __delattr__(self, name):
                if name in self.__annotations__:  # An annotated property
                    raise AttributeError
                elif name in clsVars and isinstance(clsVars[name],
                                                    property):  # A property setter + getter
                    raise AttributeError
                else:  # Set property of any name
                    if attributeStorage is None or oldDelAttr is not None:
                        oldDelAttr(self, name)
                    else:
                        del getattr(self, attributeStorage)[name]

            def __repr__(self) -> str:
                # return f"<kutil.typing_help.anyattribute._AnyAttributeHelper of {repr(cls)} at {hex(id(self))}>"
                # return f"<kutil.typing_help.anyattribute._AnyAttributeHelper of {cls.__repr__(self)} at {hex(id(self))}>"
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


class SuperMethodNotCalledError(RuntimeError): ...


class EnforceSuperCallMeta(ABCMeta, type):  # Extends ABC to not cause a TypeError in some scenarios
    def __new__(cls, name: str, bases: tuple[type], attrs: dict[str, Any]):
        """
        What the heck are metaclasses? https://stackoverflow.com/a/6581949
        :param name: Name of the class
        :param bases: Tuple of the parent class (for inheritance, but can also be empty)
        :param attrs: Dictionary containing attribute names and values
        """
        for attr_name, method in attrs.items():
            # If the entry's value is a method, e.g., is callable, we may wrap it
            if not callable(method):
                continue

            # If the method also exists in the parent class, we wrap it
            for base in bases:
                parent_method = getattr(base, attr_name, None)
                if parent_method is None:
                    continue
                elif not callable(parent_method):
                    continue
                elif not getattr(parent_method, "__EnforceSuperCallMeta_should_enforce_super_call",
                                 False):
                    continue

                attrs[attr_name] = cls._wrap_method(parent_method, name, method)  # Wrap it!
                break
        return super().__new__(cls, name, bases, attrs)

    @staticmethod
    def _wrap_method(parent_method: Callable, class_name: str, child_method: Callable):
        @wraps(child_method)
        def wrapper(self, *args, **kwargs):
            # Check if the parent method's attribute to later check whether super() was called
            # exists (e.g., some unexpected behavior occurred, probably caused by recursive calls of the child method)
            if hasattr(parent_method, "__EnforceSuperCallMeta_super_called"):
                raise RuntimeError(
                    f"You may not recursively call {class_name}.{parent_method.__name__}(), "
                    f"because the parent class's method used the @enforcesupercall decorator")

            # Set the parent method wrapper's attribute to later check whether super() was called
            setattr(parent_method, "__EnforceSuperCallMeta_super_called", False)

            # print(f"Wrapper for the child method called: wrapper({self}, *{args}, **{kwargs})")

            # TODO See the ChatGPT chat and see how to improve the error logs
            # Uložení aktuálního snímku volání (frame)
            # frame: FrameType = sys._getframe()  # Získání aktuálního snímku zásobníku

            # Call the child method
            # FIXME Fix the error when the arguments provided to the wrapper don't match the arguments of the child method so it doesn't show as it was caused by the wrapper
            result = child_method(self, *args, **kwargs)

            # Check whether super() was called, e.g. the @enforcesupercall -> wrapper() was called
            super_called = getattr(parent_method, "__EnforceSuperCallMeta_super_called", False)

            # Delete the parent method wrapper's attribute used to check whether super() was called
            delattr(parent_method, "__EnforceSuperCallMeta_super_called")

            # Throw a runtime exception if super() was not called
            if not super_called:
                # from types import TracebackType, FrameType
                err = SuperMethodNotCalledError(
                    f"You must call super().{parent_method.__name__}() "
                    f"in {class_name}.{parent_method.__name__}(), "
                    f"because the parent class's method used the @enforcesupercall decorator")
                # frame: FrameType = getattr(parent_method,
                #                            "__EnforceSuperCallMeta_decorator_usage_frame", None)
                # if frame is not None:
                #     tb = TracebackType(None, frame, frame.f_lasti, frame.f_lineno)
                #     cause = NotImplementedError("...").with_traceback(tb)
                #     raise err from cause
                # else:
                raise err

            return result

        return wrapper


def enforcesupercall(method: Callable) -> Callable:
    setattr(method, "__EnforceSuperCallMeta_should_enforce_super_call", True)

    # setattr(method, "__EnforceSuperCallMeta_decorator_usage_frame", getCallerFrame(skipFrames=0))

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        cls = type(self)
        if type(cls) is not EnforceSuperCallMeta:
            raise RuntimeError(f"You may not use the @enforcesupercall decorator on a method when "
                               f"its class's metaclass is not {EnforceSuperCallMeta.__name__}")
        # print(f"Wrapper for the parent method called: wrapper({self}, *{args}, **{kwargs})")
        # If the parent method (its wrapper to be clear) is called directly, the attribute isn't set
        if hasattr(wrapper, "__EnforceSuperCallMeta_super_called"):
            assert not getattr(wrapper, "__EnforceSuperCallMeta_super_called"), "...what did u do?!"
            setattr(wrapper, "__EnforceSuperCallMeta_super_called", True)
        return method(self, *args, **kwargs)

    return wrapper


"""
class Parent(metaclass=EnforceSuperCallMeta):
    @enforcesupercall
    def foo(self) -> None: ...
"""

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


def _overload_args_precompute_info(fn: Callable) -> tuple[Callable, Optional[list]]:
    sig: inspect.Signature = inspect.signature(fn)
    if sig.parameters == sig.empty:
        return fn, None
    params = dict(sig.parameters)
    info = []
    for name, arg in params.items():
        # print(name, arg)
        default = arg.default

        annotation = arg.annotation
        if annotation == arg.empty:
            if default == arg.empty:
                raise RuntimeError(f"You must either define a default value or "
                                   f"annotate the type - {fn.__name__}{str(sig)} - {arg}")
            annotation = type(default)

        info.append((annotation, name, default))
    return fn, info


# This is the function that gets to replace the function that is being overloaded
def _overloader_factory() -> Callable:
    def wrapper(self, *args, **kwargs):
        # print("Call the method with arguments", args, kwargs)
        argTypes = list(map(lambda x: type(x), args))
        candidates = []
        for func, info in self.__overloads__:
            if len(info) == 0:
                # No arguments accepted
                if len(args) == 0 and len(kwargs) == 0:
                    candidates.append((func, info))
                continue

            filledArgs = dict(
                map(
                    lambda infoArg: (infoArg[1], infoArg[2] != inspect.Parameter.empty),
                    info
                )
            )

            for name, _ in zip(filledArgs.keys(), args):
                filledArgs[name] = True

            for name in kwargs.keys():
                # assert filledArgs[name] is False, "Cannot overwrite a set positional argument"
                filledArgs[name] = True

            filledArgsCount = sum(filledArgs.values())

            if filledArgsCount < len(info):
                # Bad argument amount
                continue
            for ourArgType, ourArg, arg in zip(argTypes, args, info):
                if arg[0] != ourArgType and not isinstance(ourArg, arg[0]):
                    break
            else:
                candidates.append((func, info))
        if len(candidates) == 1:
            return candidates[0][0](*args, **kwargs)
        elif len(candidates) > 1:
            # Positional argument check
            if len(kwargs) == 0:
                correctArgCountFunc = None
                for func, info in candidates:
                    allPositional = all(
                        map(lambda infoArg: infoArg[2] == inspect.Parameter.empty, info)
                    )
                    if len(info) == len(args) and allPositional:
                        if correctArgCountFunc is not None:
                            correctArgCountFunc = None
                            break  # This search failed
                        correctArgCountFunc = func
                if correctArgCountFunc is not None:
                    return correctArgCountFunc(*args, **kwargs)
            # Hopefully occurs only when kwargs must decide
            if len(kwargs) > 0:
                for func, info in candidates:
                    for i, arg in enumerate(info):
                        if i < len(args):
                            continue
                        if arg[1] not in kwargs and arg[2] == inspect.Parameter.empty:
                            break
                    else:
                        return func(*args, **kwargs)
            raise ValueError("No suiting overload method found - keyword "
                             "arguments must be added to choose one exact method")
        raise ValueError("No suiting overload method found")

    class ReprWrapper:
        __overloads__: dict

        def __call__(self, *args, **kwargs):
            return wrapper(self, *args, **kwargs)

        def __repr__(self):
            funcs = map(
                lambda info: info[0].__name__ + str(inspect.signature(info[0])),
                self.__overloads__
            )
            return f"<kutil.typing_help.overload_args wrapper for {', '.join(funcs)} at {hex(id(self))}>"

    return ReprWrapper()


def overload_args(fn: Callable) -> Callable:
    """ DO NOT USE!!! """
    raise NotImplementedError("It's implemented, but not properly :-/")
    # TODO Fix it
    """
    A decorator for overloading a function depending on it's provided arguments.

    You should use the built-in typing.overload decorator instead and check the arguments by hand,
    this is just for educational purposes.

    Sadly it isn't supported by IDEs, but Python works with it.

    >>> @overload_args
    ... def my_func():
    ...     print("Hello world!")
    >>> @overload_args
    ... def my_func(name):
    ...     print(f"Hello {name}!")
    >>> my_func()
    Hello world!
    >>> my_func("John")
    Hello John!
    """

    assert inspect.isfunction(fn), "This decorator only works for def functions"
    fn.__overloaded__ = True

    callerInfo: inspect.FrameInfo = inspect.stack()[1]
    func_locals = callerInfo.frame.f_locals

    overloadInfo = _overload_args_precompute_info(fn)

    if fn.__name__ not in func_locals:
        _overloader = _overloader_factory()  # It's actually a class (needs __repr__)
        _overloader.__overloader__ = True
        overloader = _overloader
        overloads = [overloadInfo]
        setattr(overloader, "__overloads__", overloads)
    else:
        overloader = func_locals[fn.__name__]
        assert isinstance(overloader, object) and getattr(overloader, "__overloader__") is True
        overloads = getattr(overloader, "__overloads__")
        assert overloadInfo not in overloads, ("Cannot overload a function with a certain signature"
                                               " multiple times")
        overloads.append(overloadInfo)

    return overloader


# Useful functions
def dictUnion(*dicts: MutableMapping):
    """
    Given a list of dictionaries, return a dictionary containing all the key-value pairs of the given
    dictionaries, but with the last dictionary to contain the key determining the value.
    :param dicts:
    :return:
    """
    if not all(map(lambda x: isinstance(x, MutableMapping), dicts)):
        raise TypeError("Dicts should be a list of type MutableMapping")
    if len(dicts) < 2:
        raise ValueError("There should be 2 or more dictionaries to union")

    newDict: dict = {}
    for d in dicts:
        newDict.update(d)
    return newDict


# dictUnion({"a": 6}, {"a": 8}, {"b": 7})


def neverCall(*args, **kwargs) -> Never:
    """
    A function that should never be called.
    Useful as a placeholder, for example, before an event listener function is registered.
    """
    raise Exception("This function should never be called")


def returnTrue(*args, **kwargs) -> Literal[True]:
    """
    A function that will always return True when called.
    Useful as a placeholder, for example, before an event listener function is registered.
    """
    return True


def returnFalse(*args, **kwargs) -> Literal[False]:
    """
    A function that will always return False when called.
    Useful as a placeholder, for example, before an event listener function is registered.
    """
    return False


def returnFactory[T:Any](returnValue: T) -> Callable[..., T]:
    """
    A function that will always return the provided argument when called.
    Useful as a placeholder, for example, before an event listener function is registered.
    """
    return lambda *args, **kwargs: returnValue


# Additional types
type FinalStr = Final[str]
type LiteralTrue = Literal[True]
type LiteralFalse = Literal[False]
