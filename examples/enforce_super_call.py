#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>, ChatGPT 3"

from kutil.typing_help import EnforceSuperCallMeta, enforcesupercall


class Parent(metaclass=EnforceSuperCallMeta):
    @enforcesupercall
    def foo(self) -> None:
        print("Parent method")


class GoodChild(Parent):
    def foo(self):
        super().foo()
        print("GoodChild method")


class BadChild(Parent):
    def foo(self):
        print("BadChild method")


def main() -> None:
    print("Test 1 - Parent")
    parent = Parent()
    parent.foo()  # Passes

    print("\nTest 2 - GoodChild")
    child = GoodChild()
    child.foo()  # Passes

    print("\nTest 3 - BadChild")
    bad_child = BadChild()
    # Throws a kutil.typing_help.SuperMethodNotCalledError, because super().foo() was not called
    bad_child.foo()


if __name__ == '__main__':
    main()
