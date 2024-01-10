#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import main

if __name__ == "__main__":
    from test.doctest_test import Tester  # Test the thing itself

    from test.tcp_connection import TestTCPConnection  # Test TCP connection
    from test.http_connection import TestHTTPConnection  # Test HTTP request
    from test.brainfuck import TestBrainFuck  # Test BrainFuck interpreter
    from test.thread_waiter import TestThreadWaiter  # Test thread pausing
    from test.typing_test import TestTyping  # Test typing
    from test.test_bon import TestBON  # Test BON

    main()
