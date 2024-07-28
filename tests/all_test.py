#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import main

if __name__ == "__main__":
    from tests.doctest_test import Tester  # Test the thing itself

    from tests.tcp_connection import TestTCPConnection  # Test TCP connection
    from tests.http_connection import TestHTTPConnection  # Test HTTP request
    from tests.brainfuck import TestBrainFuck  # Test BrainFuck interpreter
    from tests.thread_waiter import TestThreadWaiter  # Test thread pausing
    from tests.typing_test import TestTyping  # Test typing
    from tests.test_bon import TestBON  # Test BON
    from tests.test_js import TestJavascript  # Test JS
    from tests.test_memorybytebuffer import TestMemoryByteBuffer  # Test TestMemoryByteBuffer
    from tests.test_filebytebuffer import TestFileByteBuffer  # Test TestFileByteBuffer

    main()

# TODO Use the PyCharm IDE's tests window
