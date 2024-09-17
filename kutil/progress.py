"""
This is the progress module of KUtil containing functionality for displaying progress using
the native print() method.
"""
#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import Thread
from time import sleep

from kutil.typing_help import Optional, Final, Self, Callable, Any
from kutil.math_help import clamp, floor
from kutil.threads.ThreadWaiter import ThreadWaiter

from kutil.io.file import CR


class ProgressBar:
    # https://stackoverflow.com/a/75051405
    PREFIX_CHARACTERS: Final[str] = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    # https://en.wikipedia.org/wiki/Block_Elements#Character_table
    PROGRESS_BAR_CHARACTERS: Final[str] = '▏▎▍▌▋▊▉█'  # 1/8 up to 8/8
    _updaterThreadWaiter: ThreadWaiter | None = None
    _progressBars: Final[list[Self]] = []

    _progress: int  # How much is progressed
    _maxProgress: int  # Out of the total
    _prefix: int
    _width: int
    _showPercentage: bool  # Show progress percentage
    _showProgressCount: bool  # Show progress like "progress/maxProgress" e.g., "42/100"
    _title: Optional[str]
    _deleteBarOnEnded: bool
    _showing: bool  # Is the progress bar showing progress? (do not print anything else when True)
    _deleted: bool

    def __init__(self,
                 maxProgress: int,
                 title: Optional[str] = None, *,
                 width: int = 10,
                 showPercentage: bool = True,
                 showProgressCount: bool = False,
                 deleteBarOnEnded: bool = True):
        self._progress = 0
        self._maxProgress = maxProgress
        self._prefix = 0
        self._title = title
        self._width = width
        self._showPercentage = showPercentage
        self._showProgressCount = showProgressCount
        self._deleteBarOnEnded = deleteBarOnEnded
        self._showing = False
        self._deleted = False

        ProgressBar._progressBars.append(self)
        ProgressBar.startProgressUpdaterThread()

    # Context Manager
    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end(deleteManually=False)

    # Context Manager end

    def __del__(self):
        if self._showing:
            self.end(deleteManually=True)
        self.delete()

    def delete(self):
        if self._deleted:
            return
        self._deleted = True
        ProgressBar._progressBars.remove(self)
        if ProgressBar._updaterThreadWaiter:  # If the thread hasn't already ended at this point
            ProgressBar.wakeProgressUpdaterThread()

    @staticmethod
    def startProgressUpdaterThread():
        if ProgressBar._updaterThreadWaiter is not None:
            ProgressBar.wakeProgressUpdaterThread()
            return
        t = Thread(target=ProgressBar.progressUpdaterThread)
        t.name = "KUtil.progress.ProgressBar progress updater"
        t.start()

    @staticmethod
    def progressUpdaterThread():
        waiter = ProgressBar._updaterThreadWaiter = ThreadWaiter()
        try:
            while len(ProgressBar._progressBars) > 0:
                waiter.wait()  # Wait for a bar to begin
                if len(ProgressBar._progressBars) == 0:
                    break
                someIsShowing = True
                while someIsShowing:
                    someIsShowing = False
                    for bar in ProgressBar._progressBars:
                        if bar._showing:
                            someIsShowing = True
                            bar.render()
                    sleep(.1)  # That's the delay between renders so the prefix is always changing
                if not someIsShowing:
                    break
        finally:
            ProgressBar._updaterThreadWaiter = None

    @staticmethod
    def wakeProgressUpdaterThread():
        ProgressBar._updaterThreadWaiter.reset()

    def begin(self):
        if self._showing:
            raise RuntimeError("Cannot ProgressBar.begin() when it has already begun")
        self._showing = True
        self._progress = 0
        if self._title is not None:
            print(self._title)
        self.render()
        ProgressBar.startProgressUpdaterThread()

    def end(self, *, deleteManually=False):
        if not self._showing:
            raise RuntimeError("Cannot ProgressBar.end() when it hasn't begun yet")

        if self._deleteBarOnEnded:
            print(f"{CR}{self._maxWidth() * ' '}{CR}", end="")
        else:
            self.render(renderPrefix=False)
            print()

        self._showing = False

        if not deleteManually:
            self.delete()

    def update(self, delta: int):
        if not self._showing:
            raise RuntimeError("Cannot ProgressBar.update() when it hasn't begun yet")
        self._progress = clamp(self._progress + delta, 0, self._maxProgress)
        self.render()

    def render(self, renderPrefix: bool = True):
        if not self._showing:
            raise RuntimeError("Cannot ProgressBar.render() when it hasn't begun yet")

        parts: list[str] = []

        if renderPrefix:
            self._prefix += 1
            self._prefix %= len(ProgressBar.PREFIX_CHARACTERS)
            parts.append(ProgressBar.PREFIX_CHARACTERS[self._prefix])

        if self._showPercentage:
            percentage = self._progress * 100 / self._maxProgress
            parts.append(f"{percentage:6.2f}%")

        if self._showProgressCount:
            if self._showPercentage:
                parts.append("-")  # Split it with a dash
            progressStr = str(self._progress).rjust(self._maxProgressCountWidth(), ' ')
            parts.append(f"{progressStr}/{self._maxProgress}")

        chars = ProgressBar.PROGRESS_BAR_CHARACTERS
        # Progress in progressPart/len(chars) of progress chars e.g., progress * self._width * 8
        progressPart = round(self._progress * self._width * len(chars) / self._maxProgress)
        progressFullPart = floor(progressPart / len(chars))
        progressFractionPart = progressPart % len(chars)
        progressStart = progressFullPart * chars[-1]
        if progressFractionPart != 0:
            progressMiddle = chars[progressFractionPart - 1]
        else:
            progressMiddle = ""
        progressEnd = (self._width - len(progressStart) - len(progressMiddle)) * " "
        parts.append(f"[{progressStart}{progressMiddle}{progressEnd}]")

        print(CR + " ".join(parts), end="")

    def _maxProgressCountWidth(self) -> int:
        return len(str(self._maxProgress))

    def _maxWidth(self):
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
        return self._maxWidth()

    def _assertEditable(self) -> None:
        """
        Checks whether the ProgressBar can be edited. If not, raises a RuntimeError
        :return: When the ProgressBar can be edited
        :raises RuntimeError: When the ProgressBar cannot be edited
        """
        if self._showing:
            raise RuntimeError("Cannot edit a ProgressBar while it's showing")
        if self._deleted:
            raise RuntimeError("Cannot edit a ProgressBar after deletion")

    # Boilerplate getters
    @property
    def progress(self) -> int:
        return self._progress

    @property
    def maxProgress(self) -> int:
        return self._maxProgress

    @property
    def width(self) -> int:
        return self._width

    @property
    def showPercentage(self) -> bool:
        return self._showPercentage

    @property
    def showProgressCount(self) -> bool:
        return self._showProgressCount

    @property
    def title(self) -> Optional[str]:
        return self._title

    @property
    def deleteBarOnEnded(self) -> bool:
        return self._deleteBarOnEnded

    @property
    def showing(self) -> bool:
        return self._showing

    @property
    def deleted(self) -> bool:
        return self._deleted

    # Boilerplate getters end

    # Boilerplate setters
    @progress.setter
    def progress(self, newProgress: int):
        self._assertEditable()
        self._progress = newProgress

    @maxProgress.setter
    def maxProgress(self, newMaxProgress: int):
        self._assertEditable()
        self._maxProgress = newMaxProgress

    @width.setter
    def width(self, newWidth: int):
        self._assertEditable()
        self._width = newWidth

    @showPercentage.setter
    def showPercentage(self, newShowPercentage: bool):
        self._assertEditable()
        self._showPercentage = newShowPercentage

    @showProgressCount.setter
    def showProgressCount(self, newShowProgressCount: bool):
        self._assertEditable()
        self._showProgressCount = newShowProgressCount

    @title.setter
    def title(self, newTitle: Optional[str]):
        self._assertEditable()
        self._title = newTitle

    @deleteBarOnEnded.setter
    def deleteBarOnEnded(self, newDeleteBarOnEnded: bool):
        self._assertEditable()
        self._deleteBarOnEnded = newDeleteBarOnEnded

    @showing.setter
    def showing(self, newShowing: bool):
        self._assertEditable()
        self._showing = newShowing

    @deleted.setter
    def deleted(self, newDeleted: bool):
        self._assertEditable()
        self._deleted = newDeleted

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


__all__ = ["ProgressBar", "ProgressBarFactory", "progressFactory"]
