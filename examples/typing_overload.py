#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

# Sorry for bad example

from kutil.typing import overload_args

if __name__ == '__main__':
    @overload_args
    def my_func():
        return "Hello world!"


    @overload_args
    def my_func(differentName: str, end="!"):
        # Shows how overload works with the same arguments + types,
        # but different names
        return f"Different name in {differentName}{end}"


    @overload_args
    def my_func(name: str, end="!"):
        return f"Hello {name}{end}"


    @overload_args
    def my_func(name: str):
        return f"Hello {name} (no end)"


    # print(my_func)
    assert my_func() == "Hello world!"
    assert my_func("John") == "Hello John (no end)"
    assert my_func(name="Python", end=".") == "Hello Python."
    assert my_func(name="Python", end="...") == "Hello Python..."
    assert my_func(differentName="Python", end=".") == "Different name in Python."
