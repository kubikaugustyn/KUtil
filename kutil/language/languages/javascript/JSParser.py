#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Callable

from kutil.language.languages.javascript.JSLexer import JSLexer, RawToken, SourceLocation, Position, \
    RegExp
from kutil.language.languages.javascript.JSOptions import JSOptions
from kutil.language.languages.javascript.error_handler import ErrorHandler
from kutil.language.languages.javascript.messages import Messages
from kutil.language.languages.javascript.syntax import JSNode, JSToken, TokenName

from kutil.language.AST import AST, ASTNode
from kutil.language.Parser import Parser, OneUseParser
from kutil.language.Token import TokenOutput, Token


class Value:
    def __init__(self, value):
        self.value = value


class Params:
    def __init__(self, simple=None, message=None, stricted=None, firstRestricted=None, inFor=None,
                 paramSet=None, params=None, get=None):
        self.simple = simple
        self.message = message
        self.stricted = stricted
        self.firstRestricted = firstRestricted
        self.inFor = inFor
        self.paramSet = paramSet
        self.params = params
        self.get = get


class Config:
    def __init__(self, range=False, loc=False, source=None, tokens=False, comment=False,
                 tolerant=False, **options):
        self.range = range
        self.loc = loc
        self.source = source
        self.tokens = tokens
        self.comment = comment
        self.tolerant = tolerant
        for k, v in options.items():
            setattr(self, k, v)


class Context:
    def __init__(self, isModule=False, allowAwait=False, allowIn=True, allowStrictDirective=True,
                 allowYield=True, firstCoverInitializedNameError=None, isAssignmentTarget=False,
                 isBindingElement=False, inFunctionBody=False, inIteration=False, inSwitch=False,
                 labelSet=None, strict=False):
        self.isModule = isModule
        self.allowAwait = allowAwait
        self.allowIn = allowIn
        self.allowStrictDirective = allowStrictDirective
        self.allowYield = allowYield
        self.firstCoverInitializedNameError = firstCoverInitializedNameError
        self.isAssignmentTarget = isAssignmentTarget
        self.isBindingElement = isBindingElement
        self.inFunctionBody = inFunctionBody
        self.inIteration = inIteration
        self.inSwitch = inSwitch
        self.labelSet = {} if labelSet is None else labelSet
        self.strict = strict


class Marker:
    def __init__(self, index=None, line=None, column=None):
        self.index = index
        self.line = line
        self.column = column


class TokenEntry:
    def __init__(self, type=None, value=None, regex=None, range=None, loc=None):
        self.type = type
        self.value = value
        self.regex = regex
        self.range = range
        self.loc = loc


type DelegateType = Callable[[JSNode, SourceLocation], JSNode | None]


class JSParser(OneUseParser):
    config: Config
    errorHandler: ErrorHandler
    scanner: JSLexer
    lookahead: RawToken
    hasLineTerminator: bool
    context: Context
    ast: AST
    startMarker: Marker
    lastMarker: Marker
    delegate: DelegateType
    tokens: list[TokenEntry]

    operatorPrecedence: dict[str, int] = {
        '||': 1,
        '&&': 2,
        '|': 3,
        '^': 4,
        '&': 5,
        '==': 6,
        '!=': 6,
        '===': 6,
        '!==': 6,
        '<': 7,
        '>': 7,
        '<=': 7,
        '>=': 7,
        'instanceof': 7,
        'in': 7,
        '<<': 8,
        '>>': 8,
        '>>>': 8,
        '+': 9,
        '-': 9,
        '*': 11,
        '/': 11,
        '%': 11,
    }

    def prepare(self, options: JSOptions):
        self.config = Config(**options.toDict())

        self.delegate = options.delegate

        self.errorHandler = options.errorHandlerParser
        self.errorHandler.tolerant = self.config.tolerant
        assert isinstance(options.lexer, JSLexer)
        self.scanner = options.lexer
        self.scanner.trackComment = self.config.comment

        self.lookahead = RawToken(
            kind=JSToken.EOF,
            content='',
            lineNumber=self.scanner.lineNumber,
            lineStart=0,
            start=0,
            end=0
        )

        self.hasLineTerminator = False

        self.context = Context(
            isModule=False,
            allowAwait=False,
            allowIn=True,
            allowStrictDirective=True,
            allowYield=True,
            firstCoverInitializedNameError=None,
            isAssignmentTarget=False,
            isBindingElement=False,
            inFunctionBody=False,
            inIteration=False,
            inSwitch=False,
            labelSet={},
            strict=False
        )
        self.ast = AST()
        self.tokens = []

        self.startMarker = Marker(
            index=0,
            line=self.scanner.lineNumber,
            column=0
        )
        self.lastMarker = Marker(
            index=0,
            line=self.scanner.lineNumber,
            column=0
        )
        self.nextToken()
        self.lastMarker = Marker(
            index=self.scanner.index,
            line=self.scanner.lineNumber,
            column=self.scanner.index - self.scanner.lineStart
        )

    def parseInner(self, tokens: TokenOutput, options: JSOptions) -> AST:
        # Tokens are ignored - token generation is done weirdly here
        self.prepare(options)
        return self.parseScript()

    def throwError(self, messageFormat, *args):
        msg = format(messageFormat, *args)
        index = self.lastMarker.index
        line = self.lastMarker.line
        column = self.lastMarker.column + 1
        raise self.errorHandler.createError(index, line, column, msg)

    def tolerateError(self, messageFormat, *args):
        msg = format(messageFormat, *args)
        index = self.lastMarker.index
        line = self.scanner.lineNumber
        column = self.lastMarker.column + 1
        self.errorHandler.tolerateError(index, line, column, msg)

    # Throw an exception because of the token.

    def unexpectedTokenError(self, token=None, message=None):
        msg = message or Messages.UnexpectedToken
        if token:
            if not message:
                typ = token.type
                if typ is JSToken.EOF:
                    msg = Messages.UnexpectedEOS
                elif typ is JSToken.Identifier:
                    msg = Messages.UnexpectedIdentifier
                elif typ is JSToken.NumericLiteral:
                    msg = Messages.UnexpectedNumber
                elif typ is JSToken.StringLiteral:
                    msg = Messages.UnexpectedString
                elif typ is JSToken.Template:
                    msg = Messages.UnexpectedTemplate
                elif typ is JSToken.Keyword:
                    if self.scanner.isFutureReservedWord(token.value):
                        msg = Messages.UnexpectedReserved
                    elif self.context.strict and self.scanner.isStrictModeReservedWord(token.value):
                        msg = Messages.StrictReservedWord
                else:
                    msg = Messages.UnexpectedToken
            value = token.value
        else:
            value = 'ILLEGAL'

        msg = msg.replace('%0', str(value), 1)

        if token and isinstance(token.lineNumber, int):
            index = token.start
            line = token.lineNumber
            lastMarkerLineStart = self.lastMarker.index - self.lastMarker.column
            column = token.start - lastMarkerLineStart + 1
            return self.errorHandler.createError(index, line, column, msg)
        else:
            index = self.lastMarker.index
            line = self.lastMarker.line
            column = self.lastMarker.column + 1
            return self.errorHandler.createError(index, line, column, msg)

    def throwUnexpectedToken(self, token=None, message=None):
        raise self.unexpectedTokenError(token, message)

    def tolerateUnexpectedToken(self, token=None, message=None):
        self.errorHandler.tolerate(self.unexpectedTokenError(token, message))

    def collectComments(self):
        if not self.config.comment:
            self.scanner.scanComments()
        else:
            comments = self.scanner.scanComments()
            if comments:
                for e in comments:
                    if e.multiLine:
                        node = JSNode.BlockComment(self.scanner.source[e.slice[0]:e.slice[1]])
                    else:
                        node = JSNode.LineComment(self.scanner.source[e.slice[0]:e.slice[1]])
                    if self.config.range:
                        node.range = e.range
                    if self.config.loc:
                        node.loc = e.loc
                    if self.delegate:
                        metadata = SourceLocation(
                            start=Position(
                                line=e.loc.start.line,
                                column=e.loc.start.column,
                                offset=e.range[0],
                            ),
                            end=Position(
                                line=e.loc.end.line,
                                column=e.loc.end.column,
                                offset=e.range[1],
                            )
                        )
                        new_node = self.delegate(node, metadata)
                        if new_node is not None:
                            node = new_node

    # From internal representation to an external structure

    def getTokenRaw(self, token: RawToken) -> str:
        return self.scanner.source[token.start:token.end]

    def convertToken(self, token: RawToken) -> TokenEntry:
        t: TokenEntry = TokenEntry(
            type=TokenName[token.kind],
            value=self.getTokenRaw(token),
        )
        if self.config.range:
            t.range = [token.start, token.end]
        if self.config.loc:
            t.loc = SourceLocation(
                start=Position(
                    line=self.startMarker.line,
                    column=self.startMarker.column,
                ),
                end=Position(
                    line=self.scanner.lineNumber,
                    column=self.scanner.index - self.scanner.lineStart,
                ),
            )
        if token.kind is JSToken.RegularExpression:
            t.regex = RegExp(
                pattern=token.pattern,
                flags=token.flags,
            )

        return t

    def nextToken(self) -> RawToken:
        token: RawToken = self.lookahead

        self.lastMarker.index = self.scanner.index
        self.lastMarker.line = self.scanner.lineNumber
        self.lastMarker.column = self.scanner.index - self.scanner.lineStart

        self.collectComments()

        if self.scanner.index != self.startMarker.index:
            self.startMarker.index = self.scanner.index
            self.startMarker.line = self.scanner.lineNumber
            self.startMarker.column = self.scanner.index - self.scanner.lineStart

        nextTok: RawToken = self.scanner.lex()
        self.hasLineTerminator = token.lineNumber != nextTok.lineNumber

        if nextTok and self.context.strict and nextTok.kind is JSToken.Identifier:
            if self.scanner.isStrictModeReservedWord(nextTok.content):
                nextTok.kind = JSToken.Keyword
        self.lookahead = nextTok

        if self.config.tokens and nextTok.kind is not JSToken.EOF:
            self.tokens.append(self.convertToken(nextTok))

        return token

    def nextRegexToken(self) -> RawToken:
        self.collectComments()

        token = self.scanner.scanRegExp()
        if self.config.tokens:
            # Pop the previous token, '/' or '/='
            # self is added from the lookahead token.
            self.tokens.pop()

            self.tokens.append(self.convertToken(token))

        # Prime the next lookahead.
        self.lookahead = token
        self.nextToken()

        return token

    def createNode(self) -> Marker:
        return Marker(
            index=self.startMarker.index,
            line=self.startMarker.line,
            column=self.startMarker.column,
        )

    def startNode(self, token: RawToken, lastLineStart: int = 0) -> Marker:
        column = token.start - token.lineStart
        line = token.lineNumber
        if column < 0:
            column += lastLineStart
            line -= 1

        return Marker(
            index=token.start,
            line=line,
            column=column,
        )
    # https://github.com/Kronuz/esprima-python/blob/298c7aa160678c867ddf1015574312fab48a33a5/esprima/parser.py#L369C5-L369C9
