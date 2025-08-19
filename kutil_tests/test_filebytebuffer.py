#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import BinaryIO
from unittest import TestCase
import os

from kutil import ByteBuffer, FileByteBuffer
from kutil.io.directory import getDunderFileDir


class TestFileByteBuffer(TestCase):
    path: str
    fileHandle: BinaryIO
    buff: ByteBuffer

    def setUp(self):
        self.path = os.path.join(getDunderFileDir(), "tmp.bin")
        self.fileHandle = open(self.path, "wb+")
        self.buff = FileByteBuffer(self.fileHandle)

    def tearDown(self):
        self.fileHandle.close()  # Save it!
        os.remove(self.path)  # Get rid of it!

    def test_filebytebuffer(self):
        fBuff = self.buff

        fBuff.write(b'hello')
        fBuff.write(b'world')
        self.assertEqual(fBuff.export(), b'helloworld')
        self.assertEqual(fBuff.read(5), b'hello')
        self.assertEqual(fBuff.readRest(), b'world')
        fBuff.reset()

        fBuff.write(b'hello')
        fBuff.write(b'world')
        fBuff.read(5)
        fBuff.resetBeforePointer()
        self.assertEqual(fBuff.export(), b'world')
