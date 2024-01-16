# -*- coding: utf-8 -*-
# Copyright JS Foundation and other contributors, https://js.foundation/
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# https://github.com/Kronuz/esprima-python/blob/master/esprima/error_handler.py
# Edited by kubik.augustyn@post.cz

class JSError(Exception):
    def __init__(self, message, name=None, index=None, lineNumber=None, column=None,
                 description=None):
        super(JSError, self).__init__(message)
        self.message = message
        self.name = name
        self.index = index
        self.lineNumber = lineNumber
        self.column = column
        # self.description = description

    def toString(self):
        return f'{self.__class__.__name__}: {self}'

    def toDict(self):
        d = dict((str(k), v) for k, v in self.__dict__.items() if v is not None)
        d['message'] = self.toString()
        return d


class JSLexerError(JSError):
    pass


class JSParserError(JSError):
    pass


class ErrorHandler:
    errors: list[JSError]
    tolerant: bool
    isLexer: bool

    def __init__(self, isLexer: bool):
        self.errors = []
        self.tolerant = False
        self.isLexer = isLexer

    def recordError(self, error):
        self.errors.append(error.toDict())

    def tolerate(self, error):
        if self.tolerant:
            self.recordError(error)
        else:
            raise error

    def createError(self, index, line, col, description):
        msg = f'Line {line}: {description}'
        if self.isLexer:
            return JSLexerError(msg, index=index, lineNumber=line, column=col,
                                description=description)
        else:
            return JSParserError(msg, index=index, lineNumber=line, column=col,
                                 description=description)

    def throwError(self, index, line, col, description):
        raise self.createError(index, line, col, description)

    def tolerateError(self, index, line, col, description):
        error = self.createError(index, line, col, description)
        if self.tolerant:
            self.recordError(error)
        else:
            raise error
