#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

if __name__ == "__main__":
    # import doctest
    # import kutil
    #
    # doctest.testmod(m=kutil, verbose=True)
    # TODO test all doctests in all docstrings

    import test.tcp_connection  # Test TCP connection
    import test.http_connection  # Test HTTP request
    import test.http_server  # Test HTTP server + WS server
    import test.brainfuck  # Test BrainFuck interpreter
    import test.thread_waiter  # Test thread pausing
    import test.mapy_cz  # Test Mapy.cz webscraper
    import test.typing_test  # Test typing

    print("All tests passed")
