#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import inspect
import os.path
from typing import TypeVar, Optional

from kutil.typing_help import singleton, anyattribute
from kutil.io.directory import getDirParent
from kutil.io.file import readFile, writeFile

TConfigEntry = TypeVar("TConfigEntry", bound="ConfigEntry")


@anyattribute("_raw")
class ConfigEntry:
    _raw: dict
    _path: str
    _parent: Optional[TConfigEntry]  # If none, this entry is the root one

    def __init__(self, raw: dict, path: str, parent: Optional[TConfigEntry] = None):
        self._path = path
        self._parent = parent
        self._raw = self._processForSubEntries(raw)

    def _processForSubEntries(self, raw: dict) -> dict:
        copy: dict = {}
        for key, value in raw.items():
            if isinstance(value, dict):
                copy[key] = ConfigEntry(value, self._path, self)
            else:
                copy[key] = value
        return copy

    @staticmethod
    def _processForSubEntriesToJson(raw: dict) -> dict:
        copy: dict = {}
        for key, value in raw.items():
            if isinstance(value, ConfigEntry):
                copy[key] = value.getJson()
            else:
                copy[key] = value
        return copy

    def isRoot(self):
        return self._parent is None

    def getParent(self):
        return self._parent

    def getRaw(self):
        return self._raw

    def getJson(self) -> dict:
        return ConfigEntry._processForSubEntriesToJson(self.getRaw())

    def getPath(self):
        return self._path

    def __setattr__(self, key, value):
        # self.__raw[key] = value
        Config().write(key, value, self)

    def get(self, key: str, default=None):
        return self._raw.get(key, default)

    def __repr__(self) -> str:
        return (f"<kutil.storage.Config.ConfigEntry object stored"
                f" somewhere in {os.path.join(self.getPath(), Config.CONFIG_FILE)} at {hex(id(self))}>")


@singleton
@anyattribute
class Config:
    """
    A class that holds all the configuration for your project.
    """

    CONFIG_FILE = "config.json"
    # https://stackoverflow.com/questions/2860153/how
    _backupConfigPath: str = getDirParent(os.path.dirname(__file__))  # C:\Users\...\KUtil\kutil

    _startDirPath: str
    _descendentConfigPaths: list[str]  # The last item is the most unlikely config to be used
    _configEntries: list[ConfigEntry]

    def __init__(self):
        # https://stackoverflow.com/questions/13699283/how-tf
        # get the caller's stack frame and extract its file path
        frame_info = inspect.stack()[2]  # Index 2 - __init__, @anyattribute, @singleton, <caller>
        filepath = frame_info.filename
        del frame_info  # drop the reference to the stack frame to avoid reference cycles
        # make the path absolute (optional)
        self._startDirPath = os.path.dirname(os.path.abspath(filepath))
        self._configEntries = []

        self._populateConfigPaths()
        # print(self.descendentConfigPaths)

    def _populateConfigPaths(self):
        paths = [self._backupConfigPath]
        path = self._startDirPath
        try:
            while True:
                if path not in paths:
                    paths.append(path)
                path = getDirParent(path)
        except ValueError:
            pass
        paths.reverse()
        # Filter out non-existent paths
        paths = list(filter(lambda path: os.path.exists(self._getConfigPath(path)), paths))
        assert len(paths) > 0, f"Failed to find {self.CONFIG_FILE}"
        self._descendentConfigPaths = paths

    def _getConfigPath(self, dirPath: str) -> str:
        return os.path.join(dirPath, self.CONFIG_FILE)

    def _loadConfig(self, depth: int) -> ConfigEntry:
        assert depth < len(self._descendentConfigPaths), f"No path for such deep {self.CONFIG_FILE} file"
        if depth < len(self._configEntries):
            return self._configEntries[depth]
        for i, path in enumerate(self._descendentConfigPaths):
            if i < len(self._configEntries):
                continue  # We have already loaded that one
            elif i > depth:
                break
            raw = readFile(self._getConfigPath(path), "json")
            entry = ConfigEntry(raw, path)
            assert i == len(self._configEntries)  # All good, just checking
            self._configEntries.append(entry)
        return self._configEntries[depth]

    def _getSuitableEntryToRead(self, key: str) -> ConfigEntry:
        try:
            depth = 0
            while True:
                entry = self._loadConfig(depth)
                if key in entry:
                    break
                depth += 1
        except AssertionError:
            raise AttributeError(f"Couldn't find the key '{key}'")
        return entry

    def _getSuitableEntryToWrite(self) -> ConfigEntry:
        return self._loadConfig(depth=0)

    def _getSuitableEntryToDelete(self, key: str) -> ConfigEntry:
        return self._getSuitableEntryToRead(key)

    def read(self, key: str, default=None, raiseError: bool = True):
        entry = self._getSuitableEntryToRead(key)
        # print(f"Read {key} from {entry}")
        if raiseError:
            return entry[key]
        return entry.get(key, default)

    def write(self, key: str, value, entry: ConfigEntry):
        # print(f"Write {key} = {value} of {entry}")
        if isinstance(value, dict):
            value = ConfigEntry(value, entry.getPath(), entry)
        entry.getRaw()[key] = value
        root = entry
        while not root.isRoot():
            root = root.getParent()
        writeFile(self._getConfigPath(root.getPath()), root.getJson())

    def delete(self, key: str, entry: ConfigEntry):
        del entry.getRaw()[key]
        root = entry
        while not root.isRoot():
            root = root.getParent()
        writeFile(self._getConfigPath(root.getPath()), root.getJson())

    def __getattr__(self, key):
        return self.read(key)

    def __setattr__(self, key, value):
        self.write(key, value, self._getSuitableEntryToWrite())

    def __delattr__(self, key):
        self.delete(key, self._getSuitableEntryToDelete(key))

    def get(self, key: str, default=None):
        return self.read(key, default, raiseError=False)


if __name__ == '__main__':
    c = Config()
    c.debug = True
