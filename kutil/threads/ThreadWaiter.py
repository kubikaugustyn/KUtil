#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import BoundedSemaphore


class ThreadWaiter:
    canBeWaiting: bool
    isWaiting: bool
    semaphore: BoundedSemaphore

    def __init__(self):
        self.canBeWaiting = True
        self.isWaiting = False
        self.semaphore = BoundedSemaphore(1)
        self.semaphore.acquire(blocking=True)  # Make sure the internal counter is 0

    def wait(self, maxTime: float | None = None) -> bool:
        """
        Blocks the caller thread until the release() method is called. If it was called before the wait call,
        the thread execution will immediately continue.
        :param maxTime: The maximum time the thread can be blocked for, otherwise times out
        :return: Whether the wait completed successfully (True) or timed out (False)
        """
        if self.isWaiting:
            raise ValueError("Cannot wait while waiting")
        if not self.canBeWaiting:
            return True
        self.isWaiting = True
        result: bool = True
        if maxTime is None:
            self.semaphore.acquire(blocking=True)
        else:
            try:
                result = self.semaphore.acquire(blocking=True, timeout=maxTime)
            except TimeoutError:
                result = False
        self.isWaiting = False
        return result

    def release(self):
        """
        Releases the thread that called wait(). If wait() wasn't called yet,
        make sure the wait thread won't wait even if called.
        """
        if not self.isWaiting:
            self.canBeWaiting = False
            return
        if not self.canBeWaiting:
            raise ValueError("Cannot be waiting when waiting is forbidden")
        self.semaphore.release(1)
