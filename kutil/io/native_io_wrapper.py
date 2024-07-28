#  -*- coding: utf-8 -*-
"""
This is a module used for importing the native, built-in Python module io.
When you try to import it from code located in ``kutil.*``, it will attempt to load the ``kutil.io``
package instead, which we don't want. I made the mistake of using the name ``io``, and this is an
easy solution that won't break any code that relies on ``kutil.io``.

Check if the ``io`` we import is indeed the native io module (the io.__file__ should look something
like this: ``'C:\\Python312\\Lib\\io.py'``):

>>> io_native.__file__.endswith("io.py")
True
>>> 'The io module provides the Python interfaces to stream handling.' in io_native.__doc__
True
"""
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

# Yes, the native io
import io as io_native
from io import *

# The __all__ is copy-pasted from io.__all__ except for the first item
__all__ = ["io_native", "BlockingIOError", "open", "open_code", "IOBase", "RawIOBase", "FileIO",
           "BytesIO", "StringIO", "BufferedIOBase", "BufferedReader", "BufferedWriter",
           "BufferedRWPair", "BufferedRandom", "TextIOBase", "TextIOWrapper",
           "UnsupportedOperation", "SEEK_SET", "SEEK_CUR", "SEEK_END", "DEFAULT_BUFFER_SIZE",
           "text_encoding", "IncrementalNewlineDecoder"]

for name in __all__:
    if name not in globals():
        raise RuntimeError(f"{name} is not defined (attempted to load from the native module 'io')")
