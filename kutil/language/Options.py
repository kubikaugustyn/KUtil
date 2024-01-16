#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import ABC, abstractmethod
from typing import Self


class Options[T, U](ABC):
    @abstractmethod
    def getLexerOptions(self) -> T:
        pass

    @abstractmethod
    def getParserOptions(self) -> U:
        pass

    def getOptions(self) -> list[T | U]:
        return [self.getLexerOptions(), self.getParserOptions()]


class CompiledLanguageOptions[T, U, V](Options[T, U]):
    @abstractmethod
    def getCompilerOptions(self) -> V:
        pass

    def getOptions(self) -> list[T | U | V]:
        return [self.getLexerOptions(), self.getParserOptions(), self.getCompilerOptions()]


class InterpretedLanguageOptions[T, U, V](Options[T, U]):
    @abstractmethod
    def getInterpreterOptions(self) -> V:
        pass

    def getOptions(self) -> list[T | U | V]:
        return [self.getLexerOptions(), self.getParserOptions(), self.getInterpreterOptions()]


class UnifiedBaseOptions(Options[Self, Self]):
    def getLexerOptions(self) -> Self:
        return self

    def getParserOptions(self) -> Self:
        return self

    def getOptions(self) -> list[Self]:
        raise TypeError("Unified options doesn't support all options getter")


class UnifiedOptions(InterpretedLanguageOptions[Self, Self, Self],
                     CompiledLanguageOptions[Self, Self, Self]):
    def getLexerOptions(self) -> Self:
        return self

    def getParserOptions(self) -> Self:
        return self

    def getInterpreterOptions(self) -> Self:
        return self

    def getCompilerOptions(self) -> Self:
        return self

    def getOptions(self) -> list[Self]:
        raise TypeError("Unified options doesn't support all options getter")
