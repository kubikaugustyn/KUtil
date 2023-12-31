#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from time import sleep, time
from threading import Thread

from kutil import ThreadWaiter

waiter: ThreadWaiter = ThreadWaiter()


def otherThread():
    sleep(.1)
    waiter.release()


def waitAndCheck():
    sTime = time()
    assert waiter.wait(maxTime=1)
    deltaTime = time() - sTime
    assert deltaTime > .099


Thread(target=otherThread).start()
Thread(target=waitAndCheck).start()
waitAndCheck()
