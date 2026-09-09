#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Any


# https://stackoverflow.com/questions/2082152/case-insensitive-dictionary
class CaseInsensitiveKey(object):
    key: str

    def __init__(self, key: str) -> None:
        self.key = key

    def __hash__(self) -> int:
        return hash(self.key.lower())

    def __eq__(self, other) -> bool:
        return self.key.lower() == other.key.lower()

    def __str__(self) -> str:
        return self.key

    def __repr__(self) -> str:
        return f"<CaseInsensitiveKey '{self.key}'>"


class HTTPHeaders(dict[str, str]):
    def __init__(self) -> None:
        super().__init__()

    def __setitem__(self, key: str, value: str) -> None:
        super().__setitem__(CaseInsensitiveKey(key), value)

    def __getitem__(self, key: str) -> str:
        return super().__getitem__(CaseInsensitiveKey(key))

    def __delitem__(self, key: str) -> None:
        return super().__delitem__(CaseInsensitiveKey(key))

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str): return False
        return super().__contains__(CaseInsensitiveKey(key))

    def get[T: Any](self, key: str, default: T = None) -> str | T:
        if key not in self: return default
        return super().__getitem__(CaseInsensitiveKey(key))


if __name__ == '__main__':
    headers: HTTPHeaders = HTTPHeaders()
    headers["Sus"] = "good"
    assert headers.get("sUS") == "good"
