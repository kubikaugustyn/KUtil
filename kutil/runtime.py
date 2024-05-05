#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import inspect
import itertools
import re
from collections.abc import ItemsView
from typing import Any, Callable


def getScopes(*, skipFrames: int = 0, localsOnly: bool = False) -> list[ItemsView[str, Any]]:
    """
    Retrieves all the caller's scopes.
    :param skipFrames: How many frames to skip (e.g., how many parent functions do you not care about)
    :param localsOnly: Whether only local scopes should be retrieved
    :return: List of scope dict item iterables (`dict.items()`)
    """
    if skipFrames < 0:
        raise ValueError("Cannot skip less than 0 frames")

    scopes = []

    frames = inspect.stack()
    for i in range(skipFrames + 1, len(frames)):
        frameInfo: inspect.FrameInfo = frames[i]
        caller = frameInfo.frame

        scopes.append(caller.f_locals.copy().items())
        if not localsOnly:
            scopes.append(caller.f_globals.copy().items())

    return scopes


def getVariableNames(value: Any, *, skipFrames: int = 0, localsOnly: bool = False,
                     comparator: Callable[[Any, Any], bool] | None = None) -> set[str]:
    """
    Retrieves given object's Python variable names.
    :param value: Object to get variable names of
    :param skipFrames: How many frames to skip (e.g., how many parent functions do you skip)
    :param localsOnly: Whether only local scopes should be retrieved.
    :param comparator: A custom compare function to compare two values (the order isn't guaranteed)
    :return: Given object's Python variable names

    >>> arr = [1,2,3]
    >>> anotherRef = arr
    >>> sorted(list(getVariableNames(arr)))
    ['anotherRef', 'arr']

    >>> getVariableNames([6])
    set()

    >>> '__name__' in getVariableNames(__name__)
    True
    """

    variableNames = set()

    scopes = getScopes(skipFrames=skipFrames + 1, localsOnly=localsOnly)

    # Duplicate code for fewer if-else checks
    if comparator is not None:
        for varName, varVal in itertools.chain(*scopes):
            if comparator(varVal, value):
                variableNames.add(varName)
    else:
        for varName, varVal in itertools.chain(*scopes):
            if varVal is value:  # Compares the memory addresses (intentional)!
                variableNames.add(varName)

    return variableNames


def getVariableName(value: Any, skipFrames: int = 0, localsOnly: bool = False) -> str:
    """
    Retrieves given object's Python variable name.
    :param value: Object to get variable names of
    :param skipFrames: How many frames to skip (e.g., how many parent functions do you skip)
    :param localsOnly: Whether only local scopes should be retrieved
    :return: Given object's Python variable name

    >>> arr = [1,2,3]
    >>> getVariableName(arr)
    'arr'

    >>> getVariableName([6]) # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ValueError: Variable name for value [6] not found

    >>> getVariableName(__name__)
    '__name__'
    """

    names = getVariableNames(value, skipFrames=skipFrames + 1, localsOnly=localsOnly)

    if len(names) == 0:
        raise ValueError(f"Variable name for value {repr(value)} not found")
    elif len(names) == 1:
        return names.pop()

    # Attempt to find the call using regex (not 100% reliable)

    # My own pattern!
    # Matches `identifier(varName)` or `identifier(..., value=varName, ...)` as good as possible
    pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\s*\((\s*([A-Za-z_][A-Za-z0-9_]*)\s*|"
                         r"[A-Za-z0-9_=+\-*/,\s]*value\s*=\s*([A-Za-z_][A-Za-z0-9_]*)[^)]*)\)")
    # Breaks in this case:
    # arr = [1, 2, 3]
    # anotherRef = arr
    # print(getVariableName(arr), getVariableName(anotherRef))
    # And many more cases (but that doesn't matter)

    frames = inspect.stack()
    for i in range(skipFrames + 1, len(frames)):
        frameInfo: inspect.FrameInfo = frames[i]
        for code in frameInfo.code_context:
            match = pattern.search(code)
            if match is not None:
                if match.group(2) in names:
                    return match.group(2)
                elif match.group(3) in names:
                    return match.group(3)

    return names.pop()  # Pick one randomly if regex fails
