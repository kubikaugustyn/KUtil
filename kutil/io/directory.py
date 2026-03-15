#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import os
import warnings
from typing import Iterator, overload, Literal
from kutil.runtime import getVariableValueByName


@overload
def enumFiles(path: str, extendedInfo: Literal[True]) -> Iterator[tuple[str, str, os.DirEntry]]: ...


@overload
def enumFiles(path: str, extendedInfo: Literal[False]) -> Iterator[tuple[str, str]]: ...


def enumFiles(path: str, extendedInfo: bool) -> \
        Iterator[tuple[str, str] | tuple[str, str, os.DirEntry]]:
    """
    Returns an iterator that yields a file name, file path, and (optionally, if extendedInfo=True) os.DirEntry.
    :param path: Path of the directory
    :param extendedInfo: Whether you want extended info about the files
    :return: An iterator yielding a file name, file path, and (optionally, if extendedInfo=True) os.DirEntry
    """
    with os.scandir(path) as iterator:
        for dirEntry in iterator:
            if not dirEntry.is_file():
                continue

            if extendedInfo:  # Yield name, path, os.DirEntry
                yield dirEntry.name, dirEntry.path, dirEntry
            else:  # Yield name, path
                yield dirEntry.name, dirEntry.path


@overload
def enumDirs(path: str, extendedInfo: Literal[True]) -> Iterator[tuple[str, str, os.DirEntry]]: ...


@overload
def enumDirs(path: str, extendedInfo: Literal[False]) -> Iterator[tuple[str, str]]: ...


def enumDirs(path: str, extendedInfo: bool) -> \
        Iterator[tuple[str, str] | tuple[str, str, os.DirEntry]]:
    """
    Returns an iterator that yields a subdirectory name, subdirectory path, and (optionally, if extendedInfo=True) os.DirEntry.
    :param path: Path of the directory
    :param extendedInfo: Whether you want extended info about the subdirectories
    :return: An iterator yielding a subdirectory name, subdirectory path, and (optionally, if extendedInfo=True) os.DirEntry
    """
    with os.scandir(path) as iterator:
        for dirEntry in iterator:
            if not dirEntry.is_dir():
                continue

            if extendedInfo:  # Yield name, path, os.DirEntry
                yield dirEntry.name, dirEntry.path, dirEntry
            else:  # Yield name, path
                yield dirEntry.name, dirEntry.path


def getDirParent(path: str) -> str:
    """
    Gets the parent directory of a provided directory.
    :param path: The directory's path
    :return: The parent directory's path
    """
    path = os.path.abspath(path)
    parent = os.path.abspath(os.path.join(path, os.pardir))
    if parent == path:  # If the path is C:\, we cannot go higher
        raise ValueError("Cannot go out of bounds for paths")
    return parent


def getDunderFileDir(*, skipFrames: int = 0) -> str:
    """
    Gets the __file__ variable (can be overwritten locally) and extracts its directory.

    This is basically an equivalent of calling ``os.path.dirname(os.path.abspath(__file__))``
    :param skipFrames: How many frames to skip (e.g., how many parent functions do you skip)
    :return: The __file__'s full directory path
    """
    warnings.warn(
        "kutil.io.directory's getDunderFileDir() is deprecated, use os.getcwd() instead",
        category=DeprecationWarning
    )

    dunderFile: str = getVariableValueByName("__file__", variableType=str,
                                             skipFrames=skipFrames + 1, localsOnly=False)
    return os.path.dirname(os.path.abspath(dunderFile))


__all__ = ["enumFiles", "enumDirs", "getDirParent", "getDunderFileDir"]
