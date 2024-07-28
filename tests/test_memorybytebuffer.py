#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil import ByteBuffer, MemoryByteBuffer


class TestMemoryByteBuffer(TestCase):
    buff: ByteBuffer

    def setUp(self):
        self.buff = MemoryByteBuffer()

    def tearDown(self):
        self.buff.reset()

    def test_bytebuffer(self):
        b = self.buff

        b.write(b'hello')
        b.write(b'world')
        self.assertEqual(b.export(), b'helloworld')
        self.assertEqual(b.read(5), b'hello')
        self.assertEqual(b.readRest(), b'world')
        b.reset()

        b.write(b'hello')
        b.write(b'world')
        b.read(5)
        b.resetBeforePointer()
        self.assertEqual(b.export(), b'world')
