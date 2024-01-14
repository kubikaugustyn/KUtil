#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase
from time import sleep, time
from threading import Thread

from kutil import ThreadWaiter


class TestThreadWaiter(TestCase):
    waiter: ThreadWaiter

    def setUp(self):
        self.waiter = ThreadWaiter()

    def __otherThread(self):
        sleep(.1)
        self.waiter.release()

    def __waitAndCheck(self):
        sTime = time()
        self.assertTrue(self.waiter.wait(maxTime=1))
        deltaTime = time() - sTime
        self.assertGreater(deltaTime, .099)

    def test_waiting(self):
        Thread(target=self.__otherThread).start()
        Thread(target=self.__waitAndCheck).start()
        self.__waitAndCheck()
