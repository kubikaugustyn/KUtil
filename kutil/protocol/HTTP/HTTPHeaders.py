#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"


# https://stackoverflow.com/questions/2082152/case-insensitive-dictionary
class CaseInsensitiveKey(object):
    key: str

    def __init__(self, key: str):
        self.key = key

    def __hash__(self):
        return hash(self.key.lower())

    def __eq__(self, other):
        return self.key.lower() == other.key.lower()

    def __str__(self):
        return self.key

    def __repr__(self):
        return f"<CaseInsensitiveKey '{self.key}'>"


class HTTPHeaders(dict[str, str]):
    def __init__(self):
        super().__init__()

    def __setitem__(self, key: str, value: str):
        key = CaseInsensitiveKey(key)
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> str:
        key = CaseInsensitiveKey(key)
        return super().__getitem__(key)

    def __delitem__(self, key: str) -> None:
        key = CaseInsensitiveKey(key)
        return super().__delitem__(key)

    def get(self, key: str, default=None):
        key = CaseInsensitiveKey(key)
        if key not in self:
            return default
        return super().__getitem__(key)


if __name__ == '__main__':
    headers: HTTPHeaders = HTTPHeaders()
    headers["Sus"] = "good"
    assert headers.get("sUS") == "good"
