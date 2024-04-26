#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import Semaphore
from typing import Optional


class ThreadWaiter:
    canBeWaiting: bool
    waitingThreadCount: int
    semaphore: Semaphore

    def __init__(self):
        self.canBeWaiting = True
        self.waitingThreadCount = 0
        self.semaphore = Semaphore(0)

    def wait(self, maxTime: Optional[float] = None) -> bool:
        """
        Blocks the caller thread until the release() method is called. If it was called before the wait call,
        the thread execution will immediately continue.
        :param maxTime: The maximum time the thread can be blocked for, otherwise times out
        :return: Whether the wait completed successfully (True) or timed out (False)
        """
        if not self.canBeWaiting:
            return True
        self.waitingThreadCount += 1
        result: bool = True
        if maxTime is None:
            self.semaphore.acquire(blocking=True)
        else:
            try:
                result = self.semaphore.acquire(blocking=True, timeout=maxTime)
            except TimeoutError:
                result = False
        self.waitingThreadCount -= 1
        return result

    def release(self):
        """
        Releases all threads that called wait(). If wait() wasn't called yet,
        make sure the threads won't wait even if they call wait().
        """
        self.canBeWaiting = False
        if self.waitingThreadCount > 0:
            self.semaphore.release(self.waitingThreadCount)

    def reset(self):
        """Resets the waiter, """
        if self.waitingThreadCount > 0:
            self.release()
        self.canBeWaiting = True
