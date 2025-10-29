"""
This is the progress module of KUtil containing functionality for displaying progress using
the native print() method.
"""
#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import sys
from enum import Enum, unique, auto
from itertools import chain
from threading import Thread, Lock
from typing import Never, Iterator

import colorama
from colorama.ansi import Cursor, clear_line

from kutil.typing_help import Optional, Final, Self, Callable, Any
from kutil.math_help import clamp, floor
from kutil.threads.ThreadWaiter import ThreadWaiter

from kutil.io.file import CR, LF

# Important for Windows apparently
colorama.deinit()
colorama.init(autoreset=False)


@unique
class ProgressBarState(Enum):
    INITIALIZED = auto()  # Waiting to call ProgressBar.begin()
    BEGAN = auto()  # Waiting to call ProgressBar.update() or ProgressBar.end()
    ENDED = auto()  # Waiting to call ProgressBar.delete()
    DELETED = auto()  # Done


class ProgressBar:
    # https://stackoverflow.com/a/75051405
    PREFIX_CHARACTERS: Final[str] = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    # https://en.wikipedia.org/wiki/Block_Elements#Character_table
    PROGRESS_BAR_CHARACTERS: Final[str] = '▏▎▍▌▋▊▉█'  # 1/8 up to 8/8
    _updaterThreadWaiter: Final[ThreadWaiter] = ThreadWaiter()
    _updaterThread: Thread | None = None
    _updaterThreadLock: Final[Lock] = Lock()
    _progressBars: Final[list[Self]] = []
    _lastProgressBars: set[Self] = set()
    _progressBarsLock: Final[Lock] = Lock()
    _globalUpdateLock: Final[Lock] = Lock()

    _lock: Lock
    _state: ProgressBarState
    _progress: int  # How much is progressed
    _maxProgress: int  # Out of the total
    _prefix: int
    _width: int
    _showPercentage: bool  # Show progress percentage
    _showProgressCount: bool  # Show progress like "progress/maxProgress" e.g., "42/100"
    _title: Optional[str]
    _deleteBarOnEnded: bool
    _singleRenderOnEnd: bool

    def __init__(self,
                 maxProgress: int,
                 title: Optional[str] = None, *,
                 width: int = 10,
                 showPercentage: bool = True,
                 showProgressCount: bool = False,
                 deleteBarOnEnded: bool = True) -> None:
        self._lock = Lock()
        with self._lock:
            self._state = ProgressBarState.INITIALIZED
            self._progress = 0
            self._maxProgress = maxProgress
            self._prefix = 0
            self._title = title
            self._width = width
            self._showPercentage = showPercentage
            self._showProgressCount = showProgressCount
            self._deleteBarOnEnded = deleteBarOnEnded
            self._singleRenderOnEnd = False

        self._registerProgressBar(self)

    # Class methods
    @classmethod
    def _registerProgressBar(cls, bar: Self) -> None:
        with cls._progressBarsLock:
            cls._progressBars.append(bar)
        cls._wakeupProgressUpdaterThread()

    @classmethod
    def _unregisterProgressBar(cls, bar: Self) -> None:
        with cls._progressBarsLock:
            cls._progressBars.remove(bar)

    @classmethod
    def _wakeupProgressUpdaterThread(cls) -> None:
        cls._updaterThreadWaiter.reset()

        with cls._updaterThreadLock:
            if cls._updaterThread is None:
                t = cls._updaterThread = Thread(target=cls._progressUpdaterThread)
                t.name = "KUtil.progress.ProgressBar progress updater"
                t.start()

    @classmethod
    def _progressUpdaterThread(cls) -> None:
        isTTY: bool = sys.stdout.isatty()
        try:
            while True:
                with cls._progressBarsLock:
                    if len(cls._progressBars) == 0 and len(cls._lastProgressBars) == 0:
                        break

                shouldDoRenders: bool = True
                while shouldDoRenders:
                    with cls._globalUpdateLock:
                        endedBars: list[ProgressBar] = []
                        workingBars: list[ProgressBar] = []
                        lines: int = 0
                        trailingBlankLines: int = 0
                        with cls._progressBarsLock:
                            bars: Iterator[ProgressBar] = chain(
                                cls._progressBars,
                                cls._lastProgressBars.difference(cls._progressBars)
                            )
                            for bar in bars:
                                if bar.state is ProgressBarState.BEGAN or bar._singleRenderOnEnd:
                                    barLines: int = 2 if bar.title is not None else 1
                                    lines += barLines

                                    if bar._singleRenderOnEnd:
                                        if bar.deleteBarOnEnded:
                                            trailingBlankLines += barLines
                                        else:
                                            endedBars.append(bar)
                                    else:
                                        workingBars.append(bar)
                            cls._lastProgressBars = set(cls._progressBars)  # Makes a copy!!!
                        shouldDoRenders = lines > 0
                        if not shouldDoRenders:
                            break

                        # The rendering itself
                        if isTTY:
                            print(Cursor.UP(lines), end="", sep="")
                        else:
                            print(CR, end="")
                        for bar in endedBars:
                            bar._render(isTTY=isTTY)
                        if isTTY:
                            for bar in workingBars:
                                bar._render(isTTY=True)

                            if trailingBlankLines > 1:
                                for _ in range(trailingBlankLines):
                                    print(clear_line(), Cursor.DOWN(1), end="", sep="")
                                print(Cursor.UP(trailingBlankLines), end="")
                        else:
                            if len(workingBars) > 0:
                                progresses: list[float] = []
                                width: int = 1
                                for bar in workingBars:
                                    progress: float = bar.progress / bar.maxProgress
                                    progresses.append(progress)
                                    width = max(width, bar.width)
                                totalProgress: float = sum(progresses) / len(progresses)

                                parts: list[str] = [
                                    str(len(progresses)),
                                    "bar" if len(progresses) == 1 else "bars",
                                    f"{totalProgress * 100:.2f}%",
                                ]
                                if len(progresses) > 1:
                                    if len(progresses) <= 10:
                                        percentages = [f"{p * 100:.2f}%" for p in progresses]
                                    else:
                                        percentages = [f"min {min(progresses) * 100:.2f}%",
                                                       f"max {max(progresses) * 100:.2f}%"]
                                    parts.append(f"({', '.join(percentages)})")
                                parts.append(cls._renderLinearPart(
                                    clamp(int(totalProgress * 10000), 0, 10000),
                                    10000,
                                    width,
                                ))

                                print(" ".join(parts), end="")
                        print(end="", flush=True)

                    # That's the delay between renders, so the prefix is always changing
                    cls._updaterThreadWaiter.wait(0.1)

                if not shouldDoRenders:
                    break

            with cls._updaterThreadLock:
                cls._updaterThread = None
        except Exception:
            from traceback import print_exc
            from time import sleep

            sleep(0.1)  # Prevent printing the progress 'into' the exception
            print(Cursor.DOWN(1), clear_line(), CR, LF, end="", sep="", flush=True)
            print_exc()
            sys.exit(1)

    # Class methods end

    # Context Manager
    def __enter__(self) -> Self:
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end(deleteManually=False)

    # Context Manager end

    def __del__(self) -> None:
        if self.state is ProgressBarState.BEGAN:
            self.end(deleteManually=True)
        self.delete()

    def _setState(self, state: ProgressBarState) -> None:
        with self._globalUpdateLock:
            with self._lock:
                legal: bool = False
                if self._state is ProgressBarState.INITIALIZED:
                    legal = state is ProgressBarState.BEGAN
                elif self._state is ProgressBarState.BEGAN:
                    legal = state is ProgressBarState.ENDED or state is ProgressBarState.DELETED
                elif self._state is ProgressBarState.ENDED:
                    legal = state is ProgressBarState.DELETED
                if not legal:
                    raise ValueError(f"Illegal state transition from {self._state} to {state}")

                self._state = state

        if state is ProgressBarState.BEGAN:
            isTTY: bool = sys.stdout.isatty()
            if isTTY:
                # Make space for the new progress bar
                print(LF, end="")
                if self.title is not None:
                    print(LF, end="")
        elif state is ProgressBarState.ENDED:
            self._unregisterProgressBar(self)

    def delete(self) -> None:
        with self._lock:
            if self._state is ProgressBarState.DELETED:
                # raise RuntimeError("Cannot ProgressBar.delete() when it has already been deleted")
                return
            if self._state is not ProgressBarState.ENDED:
                raise RuntimeError("Cannot ProgressBar.delete() when it hasn't yet ended")

        self._setState(ProgressBarState.DELETED)

    def begin(self) -> None:
        if self.state is not ProgressBarState.INITIALIZED:
            raise RuntimeError("Cannot ProgressBar.begin() when it has already begun")

        self._setState(ProgressBarState.BEGAN)

        with self._lock:
            self._progress = 0

        self._wakeupProgressUpdaterThread()  # Schedule a render

    def end(self, *, deleteManually=False) -> None:
        if self.state is not ProgressBarState.BEGAN:
            raise RuntimeError("Cannot ProgressBar.end() when it isn't being shown")

        with self._lock:
            self._singleRenderOnEnd = True
        self._wakeupProgressUpdaterThread()  # Schedule a render

        self._setState(ProgressBarState.ENDED)

        if not deleteManually:
            self.delete()

    def update(self, delta: int) -> None:
        with self._globalUpdateLock:
            with self._lock:
                if self._state is not ProgressBarState.BEGAN:
                    raise RuntimeError("Cannot ProgressBar.update() when it isn't being shown")
                self._progress = clamp(self._progress + delta, 0, self._maxProgress)
        self._wakeupProgressUpdaterThread()  # Schedule a render

    def setProgress(self, newProgress: int) -> None:
        self.update(newProgress - self.progress)

    def resetProgress(self) -> None:
        self.update(-self.progress)

    def maxOutProgress(self) -> None:
        self.update(self.maxProgress - self.progress)

    def _render(self, *, isTTY: bool = True) -> None:
        with self._lock:
            if self._state is ProgressBarState.INITIALIZED:
                raise RuntimeError("Cannot ProgressBar._render() when it hasn't started yet")
            elif self._state is not ProgressBarState.BEGAN:
                if self._deleteBarOnEnded:
                    raise RuntimeError("Cannot ProgressBar._render() when the bar "
                                       "is supposed to be deleted from the console")
                elif not self._singleRenderOnEnd:
                    raise RuntimeError("Cannot ProgressBar._render() after the single-use "
                                       "self._singleRenderOnEnd ticket has been used")

            # Title line
            if self._title is not None:
                if isTTY:
                    print(clear_line(), CR, self._title, Cursor.DOWN(1), end="", sep="")
                else:
                    print(self._title, end=LF)

            # Progress line
            parts: list[str] = []

            renderPrefix: bool = self._state is ProgressBarState.BEGAN
            if renderPrefix:
                self._prefix += 1
                self._prefix %= len(ProgressBar.PREFIX_CHARACTERS)
                parts.append(ProgressBar.PREFIX_CHARACTERS[self._prefix])
            else:
                assert self._singleRenderOnEnd
                self._singleRenderOnEnd = False

            if self._showPercentage:
                percentage = self._progress * 100 / self._maxProgress
                parts.append(f"{percentage:6.2f}%")

            if self._showProgressCount:
                if self._showPercentage:
                    parts.append("-")  # Split it with a dash
                progressStr = str(self._progress).rjust(self._maxProgressCountWidth(), ' ')
                parts.append(f"{progressStr}/{self._maxProgress}")

            parts.append(self._renderLinearPart(self._progress, self._maxProgress, self._width))

            if isTTY:
                print(clear_line(), CR, " ".join(parts), Cursor.DOWN(1), end="", sep="")
            else:
                print(" ".join(parts), end=LF)

    @classmethod
    def _renderLinearPart(cls, progress: int, maxProgress: int, width: int) -> str:
        chars = cls.PROGRESS_BAR_CHARACTERS
        # Progress in progressPart/len(chars) of progress chars e.g., progress * self._width * 8
        progressPart = round(progress * width * len(chars) / maxProgress)
        progressFullPart = floor(progressPart / len(chars))
        progressFractionPart = progressPart % len(chars)
        progressStart = progressFullPart * chars[-1]
        if progressFractionPart != 0:
            progressMiddle = chars[progressFractionPart - 1]
        else:
            progressMiddle = ""
        progressEnd = (width - len(progressStart) - len(progressMiddle)) * " "
        return f"[{progressStart}{progressMiddle}{progressEnd}]"

    def _maxProgressCountWidth(self) -> int:
        """Must be called from withing self._lock!!!"""

        return len(str(self._maxProgress))

    def _maxWidth(self):
        """Must be called from withing self._lock!!!"""

        maxWidth = 2  # 2 for the prefix character ("⠧ ")
        if self._showPercentage:
            maxWidth += 8  # 8 for "100.00% "
        if self._showProgressCount:
            if self._showPercentage:
                maxWidth += 2  # 2 for "- "
            maxWidth += self._maxProgressCountWidth() + 1  # 1 for the trailing space (" ")
        maxWidth += self._width
        return maxWidth

    @property
    def maxWidth(self) -> int:
        with self._lock:
            return self._maxWidth()

    def _assertEditable(self) -> Never | None:
        """
        Checks whether the ProgressBar can be edited.
        If not, raises a RuntimeError.

        Must be called from withing self._lock!!!
        :return: When the ProgressBar can be edited
        :raises RuntimeError: When the ProgressBar cannot be edited
        """
        if self._state is not ProgressBarState.INITIALIZED:
            raise RuntimeError("Cannot edit a ProgressBar after calling begin()")

    # Boilerplate getters
    @property
    def state(self) -> ProgressBarState:
        with self._lock:
            return self._state

    @property
    def progress(self) -> int:
        with self._lock:
            return self._progress

    @property
    def maxProgress(self) -> int:
        with self._lock:
            return self._maxProgress

    @property
    def width(self) -> int:
        with self._lock:
            return self._width

    @property
    def showPercentage(self) -> bool:
        with self._lock:
            return self._showPercentage

    @property
    def showProgressCount(self) -> bool:
        with self._lock:
            return self._showProgressCount

    @property
    def title(self) -> Optional[str]:
        with self._lock:
            return self._title

    @property
    def deleteBarOnEnded(self) -> bool:
        with self._lock:
            return self._deleteBarOnEnded

    # Boilerplate getters end

    # Boilerplate setters
    @progress.setter
    def progress(self, newProgress: int) -> None:
        with self._lock:
            self._assertEditable()
            self._progress = newProgress

    @maxProgress.setter
    def maxProgress(self, newMaxProgress: int) -> None:
        with self._lock:
            self._assertEditable()
            self._maxProgress = newMaxProgress

    @width.setter
    def width(self, newWidth: int) -> None:
        with self._lock:
            self._assertEditable()
            self._width = newWidth

    @showPercentage.setter
    def showPercentage(self, newShowPercentage: bool) -> None:
        with self._lock:
            self._assertEditable()
            self._showPercentage = newShowPercentage

    @showProgressCount.setter
    def showProgressCount(self, newShowProgressCount: bool) -> None:
        with self._lock:
            self._assertEditable()
            self._showProgressCount = newShowProgressCount

    @title.setter
    def title(self, newTitle: Optional[str]) -> None:
        with self._lock:
            self._assertEditable()
            self._title = newTitle

    @deleteBarOnEnded.setter
    def deleteBarOnEnded(self, newDeleteBarOnEnded: bool) -> None:
        with self._lock:
            self._assertEditable()
            self._deleteBarOnEnded = newDeleteBarOnEnded

    # Boilerplate setters end

    def __repr__(self):
        return f"ProgressBar(progress={self._progress}/{self._maxProgress})"


type ProgressBarFactory[T:ProgressBar] = Callable[Any, T]


def progressFactory(*, maxProgress: Optional[int] = None, title: Optional[str] = None,
                    width: Optional[int] = None, showPercentage: Optional[bool] = None,
                    showProgressCount: Optional[bool] = None,
                    deleteBarOnEnded: Optional[bool] = None) -> ProgressBarFactory[ProgressBar]:
    def factory(*args, **kwargs) -> ProgressBar:
        maxProgressFactory = args[0] if len(args) > 0 else kwargs.get("maxProgress") or maxProgress
        titleFactory = args[0] if len(args) > 0 else kwargs.get("title") or title
        if maxProgressFactory is None or titleFactory is None:
            raise ValueError("progressFactory - nether maxProgress or title can be None")
        kwargsFactory = {
            "maxProgress": maxProgressFactory,
            "title": titleFactory,
            "width": width,
            "showPercentage": showPercentage,
            "showProgressCount": showProgressCount,
            "deleteBarOnEnded": deleteBarOnEnded,
            **kwargs
        }
        finalKWArgs = {}
        for key, val in kwargsFactory.items():
            if val is not None:
                finalKWArgs[key] = val
        return ProgressBar(**finalKWArgs)

    return factory


__all__ = ["ProgressBar", "ProgressBarState", "ProgressBarFactory", "progressFactory"]


def main() -> None:
    from threading import Thread
    from time import sleep

    def job1() -> None:
        with ProgressBar(100, "Job 1", width=20, deleteBarOnEnded=False) as bar:
            for _ in range(100):
                bar.update(1)
                sleep(.05)

    def job2() -> None:
        with ProgressBar(100, "Job 2", width=50, showProgressCount=True) as bar:
            for _ in range(100):
                bar.update(1)
                sleep(.015)

    def job3() -> None:
        with ProgressBar(100, "Job 3", width=40, showProgressCount=True) as bar:
            for _ in range(100):
                bar.update(1)
                sleep(.05)

    def job4() -> None:
        with ProgressBar(100, None, width=30, deleteBarOnEnded=False) as bar:
            for _ in range(100):
                bar.update(1)
                sleep(.03)

    print("Starting jobs...")
    Thread(target=job1).start()
    sleep(3)
    Thread(target=job2).start()
    sleep(1)
    Thread(target=job3).start()
    sleep(2)
    Thread(target=job4).start()


def main2() -> None:
    from time import sleep

    factory = progressFactory(maxProgress=100, width=20, deleteBarOnEnded=False)

    def job(bar: ProgressBar) -> None:
        with bar:
            for _ in range(100):
                bar.update(1)
                sleep(.05)

    def bigJob() -> None:
        with ProgressBar(1000, "Big job", width=20, deleteBarOnEnded=False) as bar:
            for _ in range(1000):
                bar.update(1)
                sleep(.04)

    Thread(target=bigJob).start()
    for i in range(10):
        Thread(target=job, args=(factory(title=f"Job {i + 1}"),)).start()
        sleep(3)


"""
def main_test() -> None:
    from time import sleep

    print("PyCharm:", 'PYCHARM_HOSTED' in os.environ)
    print("TTY:", sys.stdout.isatty())

    print("Line 1")
    print("Line 2")
    print("Line 3")

    sleep(1)
    print(Cursor.UP(3), end="", sep="")
    print(clear_line(), CR, "XXX", Cursor.DOWN(1), end="", sep="")
    print(clear_line(), CR, "YYY", Cursor.DOWN(1), end="", sep="")
    print(clear_line(), CR, "ZZZ", Cursor.DOWN(1), end="", sep="")
"""

if __name__ == '__main__':
    # main()
    main2()
    # main_test()
