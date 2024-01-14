#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import Thread, Event
import cv2, numpy as np

from kutil import ThreadWaiter


class Canvas(Thread):
    stop: Event
    waiter: ThreadWaiter
    img: np.ndarray

    def __init__(self):
        Thread.__init__(self)
        self.stop = Event()
        self.waiter = ThreadWaiter()
        self.img = np.zeros((100, 100, 3), dtype=np.uint8)

    def resize(self, w: int, h: int):
        self.img = np.zeros((h, w, 3), dtype=np.uint8)

    def fill(self, colorBGR: tuple[int, int, int]):
        self.img[:] = colorBGR

    def run(self) -> None:
        FPS: int = 30
        while not self.stop.is_set():
            cv2.imshow("Paint tryhard", self.img)

            self.waiter.wait(maxTime=1 / FPS)
        cv2.destroyAllWindows()

    def exit(self):
        self.stop.set()
        self.waiter.release()

    @property
    def width(self):
        return self.img.shape[1]

    @property
    def height(self):
        return self.img.shape[0]
