#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

from time import perf_counter_ns


# https://web.dev/articles/custom-metrics#server-timing-api
class HTTPRequestTiming:
    events: list[tuple[str, int | None]]
    lastEvent: int

    def __init__(self) -> None:
        self.events = []
        self.lastEvent = 0

    def event(self, name: str, forceNoTime: bool = False) -> None:
        lastTime = self.lastEvent
        self.lastEvent = perf_counter_ns()
        deltaTime: int = self.lastEvent - lastTime
        self.events.append((name, None if forceNoTime else deltaTime))

    def __str__(self) -> str:
        # Code I never write, but whatever...
        return ", ".join(
            (name if deltaTime is None else f"{name};dur={deltaTime / 1e6:.6f}")
            for name, deltaTime in self.events
        )


__all__ = ["HTTPRequestTiming"]
