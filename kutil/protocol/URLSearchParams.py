#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Optional


class URLSearchParams:
    params: dict[str, str]

    def __init__(self, val: Optional[str] = None):
        self.params = {}
        if val.startswith("?") or val.startswith("&"):
            val = val[1:]
        if val:
            self.parse(val)

    def parse(self, val: str):
        self.params = {}
        for part in val.split("&"):
            key, value = part.split("=", maxsplit=1)
            self.params[key] = value

    def __getitem__(self, item):
        return self.params.__getitem__(item)

    def get(self, key, default=None):
        return self.params.get(key, default)

    def __str__(self):
        resultParts: list[str] = []
        for key, value in self.params.items():
            resultParts.append(f"{key}={value}")
        return "&".join(resultParts)
