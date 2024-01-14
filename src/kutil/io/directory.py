#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import os
from typing import Iterator, overload, Literal


@overload
def enumFiles(path: str, extendedInfo: Literal[True]) -> Iterator[tuple[str, str, os.DirEntry]]: ...


@overload
def enumFiles(path: str, extendedInfo: Literal[False]) -> Iterator[tuple[str, str]]: ...


def enumFiles(path: str, extendedInfo: bool) -> Iterator[tuple[str, str] | tuple[str, str, os.DirEntry]]:
    """Returns an iterator, that yields file name, file path and (optionally, if extendedInfo=True) os.DirEntry.
    :param path: Path of the directory
    :param extendedInfo: Whether you want extended info about the files
    :return: An iterator yielding file name, file path and (optionally, if extendedInfo=True) os.DirEntry
    """
    dirIter = os.scandir(path) if extendedInfo else os.listdir(path)
    for dirEntryOrFN in dirIter:
        if extendedInfo:  # Yield name, path, os.DirEntry
            if os.path.isdir(dirEntryOrFN.path):
                continue
            yield dirEntryOrFN.name, dirEntryOrFN.path, dirEntryOrFN
        else:  # Yield name, path
            fullPath = os.path.join(path, dirEntryOrFN)
            if os.path.isdir(fullPath):
                continue
            yield dirEntryOrFN, fullPath


@overload
def enumDirs(path: str, extendedInfo: Literal[True]) -> Iterator[tuple[str, str, os.DirEntry]]: ...


@overload
def enumDirs(path: str, extendedInfo: Literal[False]) -> Iterator[tuple[str, str]]: ...


def enumDirs(path: str, extendedInfo: bool) -> Iterator[tuple[str, str] | tuple[str, str, os.DirEntry]]:
    """Returns an iterator, that yields subdirectory name, subdirectory path and
    (optionally, if extendedInfo=True) os.DirEntry.
    :param path: Path of the directory
    :param extendedInfo: Whether you want extended info about the subdirectories
    :return: An iterator yielding subdirectory name, subdirectory path and (optionally, if extendedInfo=True) os.DirEntry
    """
    dirIter = os.scandir(path) if extendedInfo else os.listdir(path)
    for dirEntryOrFN in dirIter:
        if extendedInfo:  # Yield name, path, os.DirEntry
            if os.path.isfile(dirEntryOrFN.path):
                continue
            yield dirEntryOrFN.name, dirEntryOrFN.path, dirEntryOrFN
        else:  # Yield name, path
            fullPath = os.path.join(path, dirEntryOrFN)
            if os.path.isfile(fullPath):
                continue
            yield dirEntryOrFN, fullPath


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
