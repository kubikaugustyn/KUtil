#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Callable, Any, overload

from kutil.language.languages.javascript.JSLexer import JSLexer, RawToken, SourceLocation, \
    Position, RegExp
from kutil.language.languages.javascript.JSOptions import JSOptions
from kutil.language.languages.javascript.error_handler import ErrorHandler
from kutil.language.languages.javascript.messages import Messages
from kutil.language.languages.javascript.syntax import JSNode, JSToken, TokenName
import kutil.language.languages.javascript.nodes as nodes
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
                 tolerant=False, classProperties=True, **options):
        self.range = range
        self.loc = loc
        self.source = source
        self.tokens = tokens
        self.comment = comment
        self.tolerant = tolerant
        self.classProperties = classProperties
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


class TokenEntry(ASTNode):
    def __init__(self, type: JSNode, value: Any, regex=None, range=None, loc=None):
        super().__init__(type, value)
        self.regex = regex
        self.range = range
        self.loc = loc


type DelegateType = Callable[[nodes.Node, SourceLocation], nodes.Node | None]
type GrammarParseFunctionReturn = Any
type GrammarParseFunction = Callable[[], GrammarParseFunctionReturn]


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
        '??': 1,
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
    assignOperators: set[str] = {'=', '*=', '**=', '/=', '%=', '+=', '-=', '<<=', '>>=', '>>>=',
                                 '&=', '^=', '|=', '&&=', '||=', '??='}

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
        # print("Prepared")
        programI = self.parseModule() if options.module else self.parseScript()
        # print("Parsed program")
        self.ast.addRootNode(programI)
        return self.ast

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

    def unexpectedTokenError(self, token: RawToken, message: str | None = None):
        msg = message or Messages.UnexpectedToken
        if token:
            if not message:
                typ = token.kind
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
                    if self.scanner.isFutureReservedWord(token.content):
                        msg = Messages.UnexpectedReserved
                    elif self.context.strict and self.scanner.isStrictModeReservedWord(
                            token.content):
                        msg = Messages.StrictReservedWord
                else:
                    msg = Messages.UnexpectedToken
            value = token.content
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

    def throwUnexpectedToken(self, token: RawToken | None = None, message: str | None = None):
        """
        Always throws an exception.
        :param token: The token that caused the error
        :param message: The message with further information
        :raise JSParserError: Always
        :return:
        """
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
                        node = nodes.BlockComment(self.scanner.source[e.slice[0]:e.slice[1]])
                    else:
                        node = nodes.LineComment(self.scanner.source[e.slice[0]:e.slice[1]])
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

        # if token.lineNumber % 100 == 0:
        #     print(f"Line: {token.lineNumber}")

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

    def finalize[T:nodes.Node](self, marker: Marker, node: T) -> T:
        if self.config.range:
            node.range = [marker.index, self.lastMarker.index]

        if self.config.loc:
            node.loc = SourceLocation(
                start=Position(
                    line=marker.line,
                    column=marker.column,
                ),
                end=Position(
                    line=self.lastMarker.line,
                    column=self.lastMarker.column,
                ),
            )
            if self.config.source:
                node.loc.source = self.config.source

        if self.delegate:
            metadata = SourceLocation(
                start=Position(
                    line=marker.line,
                    column=marker.column,
                    offset=marker.index,
                ),
                end=Position(
                    line=self.lastMarker.line,
                    column=self.lastMarker.column,
                    offset=self.lastMarker.index,
                )
            )
            new_node = self.delegate(node, metadata)
            if new_node is not None:
                node = new_node
        assert isinstance(node, nodes.Node), "Bad stuff happened"
        return node

    # Expect the next token to match the specified punctuator.
    # If not, an exception will be thrown.

    def expect(self, value: Any):
        token = self.nextToken()
        if token.kind is not JSToken.Punctuator or token.content != value:
            self.throwUnexpectedToken(token)

    # Quietly expect a comma when in tolerant mode, otherwise delegates to expect().

    def expectCommaSeparator(self):
        if self.config.tolerant:
            token = self.lookahead
            if token.kind is JSToken.Punctuator and token.content == ',':
                self.nextToken()
            elif token.kind is JSToken.Punctuator and token.content == ';':
                self.nextToken()
                self.tolerateUnexpectedToken(token)
            else:
                self.tolerateUnexpectedToken(token, Messages.UnexpectedToken)
        else:
            self.expect(',')

    # Expect the next token to match the specified keyword.
    # If not, an exception will be thrown.

    def expectKeyword(self, keyword):
        token = self.nextToken()
        if token.kind is not JSToken.Keyword or token.content != keyword:
            self.throwUnexpectedToken(token)

    # Return true if the next token matches the specified punctuator.

    def match(self, *value):
        return self.lookahead.kind is JSToken.Punctuator and self.lookahead.content in value

    # Return true if the next token matches the specified keyword

    def matchKeyword(self, *keyword):
        return self.lookahead.kind is JSToken.Keyword and self.lookahead.content in keyword

    # Return true if the next token matches the specified contextual keyword
    # (where an identifier is sometimes a keyword depending on the context)

    def matchContextualKeyword(self, *keyword):
        return self.lookahead.kind is JSToken.Identifier and self.lookahead.content in keyword

    # Return true if the next token is an assignment operator

    def matchAssign(self):
        if self.lookahead.kind is not JSToken.Punctuator:
            return False

        op = self.lookahead.content
        return op in self.assignOperators

    # Cover grammar support.
    #
    # When an assignment expression position starts with a left parenthesis, the determination of
    # the type of the syntax is to be deferred arbitrarily long until the end of the parentheses
    # pair (plus a lookahead) or the first comma. This situation also defers the determination of
    # all the expressions nested in the pair.
    #
    # There are three productions that can be parsed in a parentheses pair that needs to be
    # determined after the outermost pair is closed. They are:
    #
    #   1. AssignmentExpression
    #   2. BindingElements
    #   3. AssignmentTargets
    #
    # In order to avoid exponential backtracking, we use two flags to denote if the production can
    # be binding element or assignment target.
    #
    # The three productions have the relationship:
    #
    #   BindingElements ⊆ AssignmentTargets ⊆ AssignmentExpression
    #
    # with a single exception that CoverInitializedName when used directly in an Expression,
    # generates an early error. Therefore, we need the third state, firstCoverInitializedNameError,
    # to track the first usage of CoverInitializedName and report it when we reached the end of the
    # parentheses pair.
    #
    # isolateCoverGrammar function runs the given parser function with a new cover grammar context,
    # and it does not affect the current flags. This means the production the parser parses is only
    # used as an expression. Therefore, the CoverInitializedName check is conducted.
    #
    # inheritCoverGrammar function runs the given parse function with a new cover grammar context,
    # and it propagates the flags outside the parser. This means the production the parser parses
    # is used as a part of a potential pattern. The CoverInitializedName check is deferred.

    def isolateCoverGrammar(self, parseFunction: GrammarParseFunction) \
            -> GrammarParseFunctionReturn:
        previousIsBindingElement = self.context.isBindingElement
        previousIsAssignmentTarget = self.context.isAssignmentTarget
        previousFirstCoverInitializedNameError = self.context.firstCoverInitializedNameError

        self.context.isBindingElement = True
        self.context.isAssignmentTarget = True
        self.context.firstCoverInitializedNameError = None

        result = parseFunction()
        if self.context.firstCoverInitializedNameError is not None:
            self.throwUnexpectedToken(self.context.firstCoverInitializedNameError)

        self.context.isBindingElement = previousIsBindingElement
        self.context.isAssignmentTarget = previousIsAssignmentTarget
        self.context.firstCoverInitializedNameError = previousFirstCoverInitializedNameError

        return result

    def inheritCoverGrammar(self, parseFunction: GrammarParseFunction) \
            -> GrammarParseFunctionReturn:
        previousIsBindingElement = self.context.isBindingElement
        previousIsAssignmentTarget = self.context.isAssignmentTarget
        previousFirstCoverInitializedNameError = self.context.firstCoverInitializedNameError

        self.context.isBindingElement = True
        self.context.isAssignmentTarget = True
        self.context.firstCoverInitializedNameError = None

        result = parseFunction()

        self.context.isBindingElement = self.context.isBindingElement and previousIsBindingElement
        self.context.isAssignmentTarget = self.context.isAssignmentTarget and previousIsAssignmentTarget
        self.context.firstCoverInitializedNameError = previousFirstCoverInitializedNameError or self.context.firstCoverInitializedNameError

        return result

    def consumeSemicolon(self):
        if self.match(';'):
            self.nextToken()
        elif not self.hasLineTerminator:
            if self.lookahead.kind is not JSToken.EOF and not self.match('}'):
                self.throwUnexpectedToken(self.lookahead)
            self.lastMarker.index = self.startMarker.index
            self.lastMarker.line = self.startMarker.line
            self.lastMarker.column = self.startMarker.column

    # https://tc39.github.io/ecma262/#sec-primary-expression

    def parsePrimaryExpression(self) -> (nodes.Identifier |
                                         nodes.Literal |
                                         nodes.RegexLiteral |
                                         nodes.ThisExpression):
        node = self.createNode()

        typ = self.lookahead.kind
        if typ is JSToken.Identifier:
            if ((self.context.isModule or self.context.allowAwait) and
                    self.lookahead.content == 'await'):
                self.tolerateUnexpectedToken(self.lookahead)
            if self.matchAsyncFunction():
                expr = self.parseFunctionExpression()
            else:
                expr = self.finalize(node, nodes.Identifier(self.nextToken().content))

        elif typ in (
                JSToken.NumericLiteral,
                JSToken.StringLiteral,
        ):
            if self.context.strict and self.lookahead.octal:
                self.tolerateUnexpectedToken(self.lookahead, Messages.StrictOctalLiteral)
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False
            token = self.nextToken()
            raw = self.getTokenRaw(token)
            expr = self.finalize(node, nodes.Literal(token.content, raw))

        elif typ is JSToken.BooleanLiteral:
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False
            token = self.nextToken()
            raw = self.getTokenRaw(token)
            expr = self.finalize(node, nodes.Literal(token.content == 'true', raw))

        elif typ is JSToken.NullLiteral:
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False
            token = self.nextToken()
            raw = self.getTokenRaw(token)
            expr = self.finalize(node, nodes.Literal(None, raw))

        elif typ is JSToken.Template:
            expr = self.parseTemplateLiteral()

        elif typ is JSToken.Punctuator:
            value = self.lookahead.content
            if value == '(':
                self.context.isBindingElement = False
                expr = self.inheritCoverGrammar(self.parseGroupExpression)
            elif value == '[':
                expr = self.inheritCoverGrammar(self.parseArrayInitializer)
            elif value == '{':
                expr = self.inheritCoverGrammar(self.parseObjectInitializer)
            elif value in ('/', '/='):
                self.context.isAssignmentTarget = False
                self.context.isBindingElement = False
                self.scanner.index = self.startMarker.index
                token = self.nextRegexToken()
                raw = self.getTokenRaw(token)
                expr = self.finalize(node, nodes.RegexLiteral(token.regex, raw, token.pattern,
                                                              token.flags))
            else:
                expr = self.throwUnexpectedToken(self.nextToken())

        elif typ is JSToken.Keyword:
            if not self.context.strict and self.context.allowYield and self.matchKeyword('yield'):
                expr = self.parseIdentifierName()
            elif not self.context.strict and self.matchKeyword('let'):
                expr = self.finalize(node, nodes.Identifier(self.nextToken().content))
            else:
                self.context.isAssignmentTarget = False
                self.context.isBindingElement = False
                if self.matchKeyword('function'):
                    expr = self.parseFunctionExpression()
                elif self.matchKeyword('this'):
                    self.nextToken()
                    expr = self.finalize(node, nodes.ThisExpression())
                elif self.matchKeyword('class'):
                    expr = self.parseClassExpression()
                elif self.matchImportCall():
                    expr = self.parseImportCall()
                else:
                    expr = self.throwUnexpectedToken(self.nextToken())

        else:
            expr = self.throwUnexpectedToken(self.nextToken())

        return expr

    # https://tc39.github.io/ecma262/#sec-array-initializer

    def parseSpreadElement(self):
        node = self.createNode()
        self.expect('...')
        arg: nodes.Node = self.inheritCoverGrammar(self.parseAssignmentExpression)
        return self.finalize(node, nodes.SpreadElement(self.ast.addNode(arg)))

    def parseArrayInitializer(self):
        node = self.createNode()
        elements: list[int | None] = []

        self.expect('[')
        while not self.match(']'):
            if self.match(','):
                self.nextToken()
                elements.append(None)
            elif self.match('...'):
                element = self.parseSpreadElement()
                if not self.match(']'):
                    self.context.isAssignmentTarget = False
                    self.context.isBindingElement = False
                    self.expect(',')
                elements.append(self.ast.addNode(element))
            else:
                elements.append(
                    self.ast.addNode(self.inheritCoverGrammar(self.parseAssignmentExpression)))
                if not self.match(']'):
                    self.expect(',')
        self.expect(']')

        return self.finalize(node, nodes.ArrayExpression(elements))

    # https://tc39.github.io/ecma262/#sec-object-initializer

    def parsePropertyMethod(self, params: Params):
        self.context.isAssignmentTarget = False
        self.context.isBindingElement = False

        previousStrict = self.context.strict
        previousAllowStrictDirective = self.context.allowStrictDirective
        self.context.allowStrictDirective = params.simple
        body = self.isolateCoverGrammar(self.parseFunctionSourceElements)
        if self.context.strict and params.firstRestricted:
            self.tolerateUnexpectedToken(params.firstRestricted, params.message)
        if self.context.strict and params.stricted:
            self.tolerateUnexpectedToken(params.stricted, params.message)
        self.context.strict = previousStrict
        self.context.allowStrictDirective = previousAllowStrictDirective

        return body

    def parsePropertyMethodFunction(self) -> nodes.FunctionExpression:
        isGenerator = False
        node = self.createNode()

        previousAllowYield = self.context.allowYield
        self.context.allowYield = True
        params: Params = self.parseFormalParameters()
        paramIndexes: list[int] = self.ast.addNodes(params.params)
        methodI = self.ast.addNode(self.parsePropertyMethod(params))
        self.context.allowYield = previousAllowYield

        return self.finalize(node,
                             nodes.FunctionExpression(None, paramIndexes, methodI, isGenerator))

    def parsePropertyMethodAsyncFunction(self) -> nodes.AsyncFunctionExpression:
        node = self.createNode()

        previousAllowYield = self.context.allowYield
        previousAwait = self.context.allowAwait
        self.context.allowYield = False
        self.context.allowAwait = True
        params: Params = self.parseFormalParameters()
        paramIndexes: list[int] = self.ast.addNodes(params.params)
        methodI = self.ast.addNode(self.parsePropertyMethod(params))
        self.context.allowYield = previousAllowYield
        self.context.allowAwait = previousAwait

        return self.finalize(node, nodes.AsyncFunctionExpression(None, paramIndexes, methodI))

    def parseObjectPropertyKey(self) -> nodes.Identifier:
        node = self.createNode()
        token = self.nextToken()

        typ = token.kind
        if typ in (
                JSToken.StringLiteral,
                JSToken.NumericLiteral,
        ):
            if self.context.strict and token.octal:
                self.tolerateUnexpectedToken(token, Messages.StrictOctalLiteral)
            raw = self.getTokenRaw(token)
            key = self.finalize(node, nodes.Literal(token.content, raw))

        elif typ in (
                JSToken.Identifier,
                JSToken.BooleanLiteral,
                JSToken.NullLiteral,
                JSToken.Keyword,
        ):
            key = self.finalize(node, nodes.Identifier(token.content))

        elif typ is JSToken.Punctuator:
            if token.content == '[':
                key = self.isolateCoverGrammar(self.parseAssignmentExpression)
                self.expect(']')
            else:
                key = self.throwUnexpectedToken(token)

        else:
            key = self.throwUnexpectedToken(token)

        return key

    @staticmethod
    def isPropertyKey(key: nodes.Node, value: str) -> bool:
        if key.type is JSNode.Identifier:
            assert isinstance(key, nodes.Identifier)
            return key.name == value
        elif key.type is JSNode.Literal:
            assert isinstance(key, nodes.Literal)
            return key.value == value
        return False

    def parseObjectProperty(self, hasProto) -> nodes.Property:
        node: Marker = self.createNode()
        token: RawToken = self.lookahead

        key = None
        value = None

        computed = False
        method = False
        shorthand = False
        isAsync = False

        if token.kind is JSToken.Identifier:
            identifier = token.content
            self.nextToken()
            computed = self.match('[')
            isAsync = not self.hasLineTerminator and (identifier == 'async') and not (
                self.match(':', '(', '*', ','))
            if isAsync:
                key = self.parseObjectPropertyKey()
            else:
                key = self.finalize(node, nodes.Identifier(identifier))
        elif self.match('*'):
            self.nextToken()
        else:
            computed = self.match('[')
            key = self.parseObjectPropertyKey()

        lookaheadPropertyKey: bool = self.qualifiedPropertyName(self.lookahead)
        if (token.kind is JSToken.Identifier and not isAsync and token.content == 'get' and
                lookaheadPropertyKey):
            kind = 'get'
            computed = self.match('[')
            key = self.parseObjectPropertyKey()
            self.context.allowYield = False
            value = self.ast.addNode(self.parseGetterMethod())

        elif (token.kind is JSToken.Identifier and not isAsync and token.content == 'set' and
              lookaheadPropertyKey):
            kind = 'set'
            computed = self.match('[')
            key = self.parseObjectPropertyKey()
            value = self.ast.addNode(self.parseSetterMethod())

        elif (token.kind is JSToken.Punctuator and token.content == '*' and
              lookaheadPropertyKey):
            kind = 'init'
            computed = self.match('[')
            key = self.parseObjectPropertyKey()
            value = self.ast.addNode(self.parseGeneratorMethod())
            method = True

        else:
            if not key:
                self.throwUnexpectedToken(self.lookahead)

            kind = 'init'
            if self.match(':') and not isAsync:
                if not computed and self.isPropertyKey(key, '__proto__'):
                    if hasProto.value:
                        self.tolerateError(Messages.DuplicateProtoProperty)
                    hasProto.value = True
                self.nextToken()
                value = self.ast.addNode(self.inheritCoverGrammar(self.parseAssignmentExpression))

            elif self.match('('):
                if isAsync:
                    value = self.ast.addNode(self.parsePropertyMethodAsyncFunction())
                else:
                    value = self.ast.addNode(self.parsePropertyMethodFunction())
                method = True

            elif token.kind is JSToken.Identifier:
                identifier = self.ast.addNode(self.finalize(node, nodes.Identifier(token.content)))
                if self.match('='):
                    self.context.firstCoverInitializedNameError = self.lookahead
                    self.nextToken()
                    shorthand = True
                    init = self.ast.addNode(
                        self.isolateCoverGrammar(self.parseAssignmentExpression))
                    value = self.ast.addNode(
                        self.finalize(node, nodes.AssignmentPattern(identifier, init)))
                else:
                    shorthand = True
                    value = identifier
            else:
                self.throwUnexpectedToken(self.nextToken())

        return self.finalize(node,
                             nodes.Property(kind, self.ast.addNode(key), computed, value, method,
                                            shorthand))

    def parseObjectInitializer(self) -> nodes.ObjectExpression:
        node = self.createNode()

        self.expect('{')
        properties: list[nodes.Node] = []
        hasProto = Value(False)
        while not self.match('}'):
            if self.match('...'):
                properties.append(self.parseSpreadElement())
            else:
                properties.append(self.parseObjectProperty(hasProto))
            if not self.match('}'):
                self.expectCommaSeparator()
        self.expect('}')

        return self.finalize(node, nodes.ObjectExpression(self.ast.addNodes(properties)))

    # https://tc39.github.io/ecma262/#sec-template-literals

    def parseTemplateHead(self) -> nodes.TemplateElement:
        assert self.lookahead.head, 'Template literal must start with a template head'

        node = self.createNode()
        token = self.nextToken()
        raw = token.content
        cooked = token.cooked

        return self.finalize(node, nodes.TemplateElement(raw, cooked, token.tail))

    def parseTemplateElement(self) -> nodes.TemplateElement:
        if self.lookahead.kind is not JSToken.Template:
            self.throwUnexpectedToken()

        node = self.createNode()
        token = self.nextToken()
        raw = token.content
        cooked = token.cooked

        return self.finalize(node, nodes.TemplateElement(raw, cooked, token.tail))

    def parseTemplateLiteral(self) -> nodes.Node:
        node = self.createNode()

        # `Quasi ${expression} quasi ${expression} quasi`
        expressions: list[nodes.SequenceExpression] = []
        quasis: list[nodes.TemplateElement] = []

        quasi: nodes.TemplateElement = self.parseTemplateHead()
        quasis.append(quasi)
        while not quasi.tail:
            expressions.append(self.parseExpression())
            quasi = self.parseTemplateElement()
            quasis.append(quasi)

        return self.finalize(node, nodes.TemplateLiteral(self.ast.addNodes(quasis),
                                                         self.ast.addNodes(expressions)))

    # https://tc39.github.io/ecma262/#sec-grouping-operator

    def reinterpretExpressionAsPattern(self, expr: (nodes.SpreadElement |
                                                    nodes.ArrayExpression |
                                                    nodes.ObjectExpression |
                                                    nodes.AssignmentExpression |
                                                    nodes.Node)):
        typ = expr.type
        if typ in (
                JSNode.Identifier,
                JSNode.MemberExpression,
                JSNode.RestElement,
                JSNode.AssignmentPattern,
        ):
            pass
        elif typ is JSNode.SpreadElement:
            expr.type = JSNode.RestElement
            self.reinterpretExpressionAsPattern(self.ast.getNode(expr.argument))
        elif typ is JSNode.ArrayExpression:
            expr.type = JSNode.ArrayPattern
            for elemI in expr.elements:
                if elemI is not None:
                    self.reinterpretExpressionAsPattern(self.ast.getNode(elemI))
        elif typ is JSNode.ObjectExpression:
            expr.type = JSNode.ObjectPattern
            for prop in self.ast.getNodes(expr.properties):
                if prop.type is JSNode.SpreadElement:
                    self.reinterpretExpressionAsPattern(prop)
                else:
                    self.reinterpretExpressionAsPattern(self.ast.getNode(prop.value))
        elif typ is JSNode.AssignmentExpression:
            expr.type = JSNode.AssignmentPattern
            del expr.operator
            self.reinterpretExpressionAsPattern(self.ast.getNode(expr.left))
        else:
            # Allow other node type for tolerant parsing.
            pass

    def parseGroupExpression(self):
        self.expect('(')
        if self.match(')'):
            self.nextToken()
            if not self.match('=>'):
                self.expect('=>')
            expr = nodes.ArrowParameterPlaceHolder([])
        else:
            startToken = self.lookahead
            params = []
            if self.match('...'):
                expr = self.parseRestElement(params)
                self.expect(')')
                if not self.match('=>'):
                    self.expect('=>')
                expr = nodes.ArrowParameterPlaceHolder([self.ast.addNode(expr)])
            else:
                arrow = False
                self.context.isBindingElement = True
                expr = self.inheritCoverGrammar(self.parseAssignmentExpression)

                if self.match(','):
                    expressions: list[nodes.Node] = []

                    self.context.isAssignmentTarget = False
                    expressions.append(expr)
                    while self.lookahead.kind is not JSToken.EOF:
                        if not self.match(','):
                            break
                        self.nextToken()
                        if self.match(')'):
                            self.nextToken()
                            for expression in expressions:
                                self.reinterpretExpressionAsPattern(expression)
                            arrow = True
                            expr = nodes.ArrowParameterPlaceHolder(self.ast.addNodes(expressions))
                        elif self.match('...'):
                            if not self.context.isBindingElement:
                                self.throwUnexpectedToken(self.lookahead)
                            expressions.append(self.parseRestElement(params))
                            self.expect(')')
                            if not self.match('=>'):
                                self.expect('=>')
                            self.context.isBindingElement = False
                            for expression in expressions:
                                self.reinterpretExpressionAsPattern(expression)
                            arrow = True
                            expr = nodes.ArrowParameterPlaceHolder(self.ast.addNodes(expressions))
                        else:
                            expressions.append(
                                self.inheritCoverGrammar(self.parseAssignmentExpression))
                        if arrow:
                            break
                    if not arrow:
                        expr = self.finalize(self.startNode(startToken),
                                             nodes.SequenceExpression(
                                                 self.ast.addNodes(expressions)))

                if not arrow:
                    self.expect(')')
                    if self.match('=>'):
                        if expr.type is JSNode.Identifier and expr.name == 'yield':
                            arrow = True
                            expr = nodes.ArrowParameterPlaceHolder([self.ast.addNode(expr)])
                        if not arrow:
                            if not self.context.isBindingElement:
                                self.throwUnexpectedToken(self.lookahead)

                            if expr.type is JSNode.SequenceExpression:
                                for expression in self.ast.getNodes(expr.expressions):
                                    self.reinterpretExpressionAsPattern(expression)
                            else:
                                self.reinterpretExpressionAsPattern(expr)

                            if expr.type is JSNode.SequenceExpression:
                                parameters = expr.expressions
                            else:
                                parameters = [self.ast.addNode(expr)]
                            expr = nodes.ArrowParameterPlaceHolder(parameters)
                    self.context.isBindingElement = False

        return expr

    # https://tc39.github.io/ecma262/#sec-left-hand-side-expressions

    def parseArguments(self) -> list[nodes.Node]:
        self.expect('(')
        args = []
        if not self.match(')'):
            while True:
                if self.match('...'):
                    expr = self.parseSpreadElement()
                else:
                    # 4 times skip
                    expr = self.isolateCoverGrammar(self.parseAssignmentExpression)
                args.append(expr)
                if self.match(')'):
                    break
                self.expectCommaSeparator()
                if self.match(')'):
                    break
        self.expect(')')

        return args

    @staticmethod
    def isIdentifierName(token: RawToken) -> bool:
        return (
                token.kind is JSToken.Identifier or
                token.kind is JSToken.Keyword or
                token.kind is JSToken.BooleanLiteral or
                token.kind is JSToken.NullLiteral
        )

    def parseIdentifierName(self):
        node = self.createNode()
        token = self.nextToken()
        if not self.isIdentifierName(token):
            self.throwUnexpectedToken(token)
        return self.finalize(node, nodes.Identifier(token.content))

    def parseNewExpression(self) -> nodes.NewExpression | nodes.MetaProperty:
        node = self.createNode()

        identifier = self.parseIdentifierName()
        assert identifier.name == 'new', 'New expression must start with `new`'

        if self.match('.'):  # TODO Maybe ?.
            self.nextToken()
            if (self.lookahead.kind is JSToken.Identifier and
                    self.context.inFunctionBody and
                    self.lookahead.content == 'target'):
                prop = self.parseIdentifierName()
                expr = nodes.MetaProperty(self.ast.addNode(identifier), self.ast.addNode(prop))
            else:
                self.throwUnexpectedToken(self.lookahead)
                raise NotImplementedError  # Never occurs
        elif self.matchKeyword('import'):
            self.throwUnexpectedToken(self.lookahead)
            raise NotImplementedError  # Never occurs
        else:
            callee = self.ast.addNode(self.isolateCoverGrammar(self.parseLeftHandSideExpression))
            args = self.ast.addNodes(self.parseArguments() if self.match('(') else [])
            expr = nodes.NewExpression(callee, args)
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False

        return self.finalize(node, expr)

    def parseAsyncArgument(self) -> nodes.AssignmentExpression:
        arg = self.parseAssignmentExpression()
        self.context.firstCoverInitializedNameError = None
        return arg

    def parseAsyncArguments(self) -> list[nodes.Node]:
        self.expect('(')
        args = []
        if not self.match(')'):
            while True:
                if self.match('...'):
                    expr = self.parseSpreadElement()
                else:
                    expr = self.isolateCoverGrammar(self.parseAsyncArgument)
                args.append(expr)
                if self.match(')'):
                    break
                self.expectCommaSeparator()
                if self.match(')'):
                    break
        self.expect(')')

        return args

    def matchImportCall(self) -> bool:
        match = self.matchKeyword('import')
        if match:
            state = self.scanner.saveState()
            self.scanner.scanComments()
            nextToken = self.scanner.lex()
            self.scanner.restoreState(state)
            match = (nextToken.kind is JSToken.Punctuator) and (nextToken.content == '(')

        return match

    def parseImportCall(self) -> nodes.Import:
        node = self.createNode()
        self.expectKeyword('import')
        return self.finalize(node, nodes.Import())

    def parseLeftHandSideExpressionAllowCall(self) -> nodes.Node:
        startToken = self.lookahead
        maybeAsync = self.matchContextualKeyword('async')

        previousAllowIn = self.context.allowIn
        self.context.allowIn = True

        if self.matchKeyword('super') and self.context.inFunctionBody:
            expr = self.createNode()
            self.nextToken()
            expr = self.finalize(expr, nodes.Super())
            if not self.match('(') and not self.match('.') and not self.match('['):  # TODO Maybe ?.
                self.throwUnexpectedToken(self.lookahead)
        else:
            expr = self.inheritCoverGrammar(self.parseNewExpression if self.matchKeyword(
                'new') else self.parsePrimaryExpression)

        while True:
            optionalChain: bool = self.match('?.')
            if self.match('.') or optionalChain:
                self.context.isBindingElement = False
                self.context.isAssignmentTarget = True
                self.expect('?.' if optionalChain else '.')
                prop = self.ast.addNode(self.parseIdentifierName())
                expr = self.finalize(self.startNode(startToken),
                                     nodes.StaticMemberExpression(self.ast.addNode(expr), prop,
                                                                  optionalChain))

            elif self.match('('):
                asyncArrow = maybeAsync and (startToken.lineNumber == self.lookahead.lineNumber)
                self.context.isBindingElement = False
                self.context.isAssignmentTarget = False
                if asyncArrow:
                    args = self.parseAsyncArguments()
                else:
                    args = self.parseArguments()
                if expr.type is JSNode.Import and len(args) != 1:
                    self.tolerateError(Messages.BadImportCallArity)
                expr = self.finalize(self.startNode(startToken),
                                     nodes.CallExpression(self.ast.addNode(expr),
                                                          self.ast.addNodes(args)))
                if asyncArrow and self.match('=>'):
                    for arg in args:
                        self.reinterpretExpressionAsPattern(arg)
                    expr = nodes.AsyncArrowParameterPlaceHolder(self.ast.addNodes(args))
            elif self.match('['):
                self.context.isBindingElement = False
                self.context.isAssignmentTarget = True
                self.expect('[')
                prop = self.ast.addNode(self.isolateCoverGrammar(self.parseExpression))
                self.expect(']')
                expr = self.finalize(self.startNode(startToken),
                                     nodes.ComputedMemberExpression(self.ast.addNode(expr), prop))

            elif self.lookahead.kind is JSToken.Template and self.lookahead.head:
                quasi = self.ast.addNode(self.parseTemplateLiteral())
                expr = self.finalize(self.startNode(startToken),
                                     nodes.TaggedTemplateExpression(self.ast.addNode(expr), quasi))

            else:
                break

        self.context.allowIn = previousAllowIn

        return expr

    def parseSuper(self) -> nodes.Super:
        node = self.createNode()

        self.expectKeyword('super')
        if not self.match('[') and not self.match('.'):  # TODO Maybe ?.
            self.throwUnexpectedToken(self.lookahead)

        return self.finalize(node, nodes.Super())

    def parseLeftHandSideExpression(self) -> nodes.Node:
        assert self.context.allowIn, 'callee of new expression always allow in keyword.'

        node = self.startNode(self.lookahead)
        if self.matchKeyword('super') and self.context.inFunctionBody:
            expr = self.parseSuper()
        else:
            expr = self.inheritCoverGrammar(self.parseNewExpression if self.matchKeyword(
                'new') else self.parsePrimaryExpression)

        while True:
            optionalChain: bool = self.match('?.')
            if self.match('['):
                self.context.isBindingElement = False
                self.context.isAssignmentTarget = True
                self.expect('[')
                property = self.ast.addNode(self.isolateCoverGrammar(self.parseExpression))
                self.expect(']')
                expr = self.finalize(node, nodes.ComputedMemberExpression(self.ast.addNode(expr),
                                                                          property))

            elif self.match('.') or optionalChain:
                self.context.isBindingElement = False
                self.context.isAssignmentTarget = True
                self.expect('?.' if optionalChain else '.')
                property = self.ast.addNode(self.parseIdentifierName())
                expr = self.finalize(node,
                                     nodes.StaticMemberExpression(self.ast.addNode(expr), property,
                                                                  optionalChain))

            elif self.lookahead.kind is JSToken.Template and self.lookahead.head:
                quasi = self.ast.addNode(self.parseTemplateLiteral())
                expr = self.finalize(node,
                                     nodes.TaggedTemplateExpression(self.ast.addNode(expr), quasi))

            else:
                break

        return expr

    # https://tc39.github.io/ecma262/#sec-update-expressions

    def parseUpdateExpression(self) -> nodes.UpdateExpression:
        startToken = self.lookahead

        if self.match('++', '--'):
            node = self.startNode(startToken)
            token = self.nextToken()
            expr = self.inheritCoverGrammar(self.parseUnaryExpression)
            if self.context.strict and expr.type is JSNode.Identifier and self.scanner.isRestrictedWord(
                    expr.name):
                self.tolerateError(Messages.StrictLHSPrefix)
            if not self.context.isAssignmentTarget:
                self.tolerateError(Messages.InvalidLHSInAssignment)
            prefix = True
            expr = self.finalize(node, nodes.UpdateExpression(token.content, self.ast.addNode(expr),
                                                              prefix))
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False
        else:
            expr = self.inheritCoverGrammar(self.parseLeftHandSideExpressionAllowCall)
            if not self.hasLineTerminator and self.lookahead.kind is JSToken.Punctuator:
                if self.match('++', '--'):
                    if self.context.strict and expr.type is JSNode.Identifier and self.scanner.isRestrictedWord(
                            expr.name):
                        self.tolerateError(Messages.StrictLHSPostfix)
                    if not self.context.isAssignmentTarget:
                        self.tolerateError(Messages.InvalidLHSInAssignment)
                    self.context.isAssignmentTarget = False
                    self.context.isBindingElement = False
                    operator = self.nextToken().content
                    prefix = False
                    expr = self.finalize(self.startNode(startToken),
                                         nodes.UpdateExpression(operator, self.ast.addNode(expr),
                                                                prefix))

        return expr

    # https://tc39.github.io/ecma262/#sec-unary-operators

    def parseAwaitExpression(self) -> nodes.AwaitExpression:
        node = self.createNode()
        self.nextToken()
        argument = self.ast.addNode(self.parseUnaryExpression())
        return self.finalize(node, nodes.AwaitExpression(argument))

    def parseUnaryExpression(self) -> nodes.UnaryExpression:
        if (
                self.match('+', '-', '~', '!') or
                self.matchKeyword('delete', 'void', 'typeof')
        ):
            node = self.startNode(self.lookahead)
            token = self.nextToken()
            expr = self.inheritCoverGrammar(self.parseUnaryExpression)
            expr = self.finalize(node, nodes.UnaryExpression(token.content, self.ast.addNode(expr)))
            if (self.context.strict and
                    expr.operator == 'delete' and
                    self.ast.getNode(expr.argument).type is JSNode.Identifier):
                self.tolerateError(Messages.StrictDelete)
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False
        elif self.context.allowAwait and self.matchContextualKeyword('await'):
            expr = self.parseAwaitExpression()
        else:
            expr = self.parseUpdateExpression()

        return expr

    def parseExponentiationExpression(self) -> nodes.BinaryExpression:
        startToken = self.lookahead

        expr = self.inheritCoverGrammar(self.parseUnaryExpression)
        if expr.type is not JSNode.UnaryExpression and self.match('**'):
            self.nextToken()
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False
            left = self.ast.addNode(expr)
            right = self.ast.addNode(self.isolateCoverGrammar(self.parseExponentiationExpression))
            expr = self.finalize(self.startNode(startToken),
                                 nodes.BinaryExpression('**', left, right))

        return expr

    # https://tc39.github.io/ecma262/#sec-exp-operator
    # https://tc39.github.io/ecma262/#sec-multiplicative-operators
    # https://tc39.github.io/ecma262/#sec-additive-operators
    # https://tc39.github.io/ecma262/#sec-bitwise-shift-operators
    # https://tc39.github.io/ecma262/#sec-relational-operators
    # https://tc39.github.io/ecma262/#sec-equality-operators
    # https://tc39.github.io/ecma262/#sec-binary-bitwise-operators
    # https://tc39.github.io/ecma262/#sec-binary-logical-operators

    def binaryPrecedence(self, token: RawToken) -> int:
        op = token.content
        if token.kind is JSToken.Punctuator:
            precedence = self.operatorPrecedence.get(op, 0)
        elif token.kind is JSToken.Keyword:
            precedence = 7 if (op == 'instanceof' or (self.context.allowIn and op == 'in')) else 0
        else:
            precedence = 0
        return precedence

    def parseBinaryExpression(self) -> nodes.BinaryExpression:
        startToken = self.lookahead

        expr = self.inheritCoverGrammar(self.parseExponentiationExpression)

        token = self.lookahead
        precedence = self.binaryPrecedence(token)
        if precedence > 0:
            self.nextToken()

            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False

            markers = [startToken, self.lookahead]
            left = expr
            right = self.isolateCoverGrammar(self.parseExponentiationExpression)

            stack = [left, token.content, right]
            precedences = [precedence]
            while True:
                precedence = self.binaryPrecedence(self.lookahead)
                if precedence <= 0:
                    break

                # Reduce: make a binary expression from the three topmost entries.
                while len(stack) > 2 and precedence <= precedences[-1]:
                    right = self.ast.addNode(stack.pop())
                    operator = stack.pop()
                    precedences.pop()
                    left = self.ast.addNode(stack.pop())
                    markers.pop()
                    node = self.startNode(markers[-1])
                    stack.append(self.finalize(node, nodes.BinaryExpression(operator, left, right)))

                # Shift.
                stack.append(self.nextToken().content)
                precedences.append(precedence)
                markers.append(self.lookahead)
                stack.append(self.isolateCoverGrammar(self.parseExponentiationExpression))

            # Final reduce to clean up the stack.
            i = len(stack) - 1
            expr = stack[i]

            lastMarker = markers.pop()
            while i > 1:
                marker = markers.pop()
                lastLineStart = lastMarker.lineStart if lastMarker else 0
                node = self.startNode(marker, lastLineStart)
                operator = stack[i - 1]
                expr = self.finalize(node, nodes.BinaryExpression(operator,
                                                                  self.ast.addNode(stack[i - 2]),
                                                                  self.ast.addNode(expr)))
                i -= 2
                lastMarker = marker

        return expr

    # https://tc39.github.io/ecma262/#sec-conditional-operator

    def parseConditionalExpression(self) -> nodes.ConditionalExpression | nodes.BinaryExpression:
        startToken = self.lookahead

        expr: nodes.BinaryExpression = self.inheritCoverGrammar(self.parseBinaryExpression)
        if self.match('?'):
            self.nextToken()

            previousAllowIn = self.context.allowIn
            self.context.allowIn = True
            consequent = self.ast.addNode(self.isolateCoverGrammar(self.parseAssignmentExpression))
            self.context.allowIn = previousAllowIn

            self.expect(':')
            alternate = self.ast.addNode(self.isolateCoverGrammar(self.parseAssignmentExpression))

            node = nodes.ConditionalExpression(self.ast.addNode(expr), consequent, alternate)
            expr: nodes.ConditionalExpression = self.finalize(self.startNode(startToken), node)
            self.context.isAssignmentTarget = False
            self.context.isBindingElement = False

        return expr

    # https://tc39.github.io/ecma262/#sec-assignment-operators

    def checkPatternParam(self, options, param: (nodes.Identifier |
                                                 nodes.RestElement |
                                                 nodes.AssignmentPattern |
                                                 nodes.ArrayPattern |
                                                 nodes.ObjectPattern)):
        typ = param.type
        if typ is JSNode.Identifier:
            self.validateParam(options, param, param.name)
        elif typ is JSNode.RestElement:
            self.checkPatternParam(options, self.ast.getNode(param.argument))
        elif typ is JSNode.AssignmentPattern:
            self.checkPatternParam(options, self.ast.getNode(param.left))
        elif typ is JSNode.ArrayPattern:
            for element in param.elements:
                if element is not None:
                    self.checkPatternParam(options, self.ast.getNode(element))
        elif typ is JSNode.ObjectPattern:
            for prop in self.ast.getNodes(param.properties):
                self.checkPatternParam(options,
                                       prop if prop.type is JSNode.RestElement else self.ast.getNode(
                                           prop.value))

        options.simple = options.simple and isinstance(param, nodes.Identifier)

    def reinterpretAsCoverFormalsList(self, expr: (nodes.Identifier |
                                                   nodes.ArrowParameterPlaceHolder |
                                                   nodes.Node)) -> Params | None:
        params = [expr]

        asyncArrow = False
        typ = expr.type
        if typ is JSNode.Identifier:
            pass
        elif typ is JSNode.ArrowParameterPlaceHolder:
            params = self.ast.getNodes(expr.params)
            asyncArrow = expr.isAsync
        else:
            return None

        options = Params(
            simple=True,
            paramSet={},
        )

        for param in params:
            if param.type is JSNode.AssignmentPattern:
                rightParam = self.ast.getNode(param.right)
                if rightParam.type is JSNode.YieldExpression:
                    if rightParam.argument:
                        self.throwUnexpectedToken(self.lookahead)
                    rightParam.type = JSNode.Identifier
                    rightParam.name = 'yield'
                    del rightParam.argument
                    del rightParam.delegate
            elif asyncArrow and param.type is JSNode.Identifier and param.name == 'await':
                self.throwUnexpectedToken(self.lookahead)
            self.checkPatternParam(options, param)

        if self.context.strict or not self.context.allowYield:
            for param in params:
                if param.type is JSNode.YieldExpression:
                    self.throwUnexpectedToken(self.lookahead)

        if options.message is Messages.StrictParamDupe:
            token = options.stricted if self.context.strict else options.firstRestricted
            self.throwUnexpectedToken(token, options.message)

        return Params(
            simple=options.simple,
            params=params,
            stricted=options.stricted,
            firstRestricted=options.firstRestricted,
            message=options.message
        )

    def parseAssignmentExpression(self) -> (nodes.AssignmentExpression |
                                            nodes.AsyncArrowFunctionExpression |
                                            nodes.ArrowFunctionExpression):
        # let a = <9>
        if not self.context.allowYield and self.matchKeyword('yield'):
            expr = self.parseYieldExpression()
        else:
            startToken = self.lookahead
            token = startToken
            expr = self.parseConditionalExpression()

            if token.kind is JSToken.Identifier and (
                    token.lineNumber == self.lookahead.lineNumber) and token.content == 'async':
                if self.lookahead.kind is JSToken.Identifier or self.matchKeyword('yield'):
                    arg = self.parsePrimaryExpression()
                    self.reinterpretExpressionAsPattern(arg)
                    expr = nodes.AsyncArrowParameterPlaceHolder([self.ast.addNode(arg)])

            if expr.type is JSNode.ArrowParameterPlaceHolder or self.match('=>'):

                # https://tc39.github.io/ecma262/#sec-arrow-function-definitions
                self.context.isAssignmentTarget = False
                self.context.isBindingElement = False
                if expr.type is JSNode.ArrowParameterPlaceHolder:
                    # I added this check - it was crashing (self.match passed, but expr was
                    # Identifier that doesn't contain isAsync)
                    isAsync = expr.isAsync
                else:
                    isAsync = False
                list = self.reinterpretAsCoverFormalsList(expr)

                if list:
                    if self.hasLineTerminator:
                        self.tolerateUnexpectedToken(self.lookahead)
                    self.context.firstCoverInitializedNameError = None

                    previousStrict = self.context.strict
                    previousAllowStrictDirective = self.context.allowStrictDirective
                    self.context.allowStrictDirective = list.simple

                    previousAllowYield = self.context.allowYield
                    previousAwait = self.context.allowAwait
                    self.context.allowYield = True
                    self.context.allowAwait = isAsync

                    node = self.startNode(startToken)
                    self.expect('=>')
                    if self.match('{'):
                        previousAllowIn = self.context.allowIn
                        self.context.allowIn = True
                        body = self.parseFunctionSourceElements()
                        self.context.allowIn = previousAllowIn
                    else:
                        body = self.isolateCoverGrammar(self.parseAssignmentExpression)
                    expression = body.type is not JSNode.BlockStatement

                    if self.context.strict and list.firstRestricted:
                        self.throwUnexpectedToken(list.firstRestricted, list.message)
                    if self.context.strict and list.stricted:
                        self.tolerateUnexpectedToken(list.stricted, list.message)
                    if isAsync:
                        expr = self.finalize(node,
                                             nodes.AsyncArrowFunctionExpression(
                                                 self.ast.addNodes(list.params),
                                                 self.ast.addNode(body),
                                                 expression))
                    else:
                        expr = self.finalize(node, nodes.ArrowFunctionExpression(
                            self.ast.addNodes(list.params), self.ast.addNode(body),
                            expression))

                    self.context.strict = previousStrict
                    self.context.allowStrictDirective = previousAllowStrictDirective
                    self.context.allowYield = previousAllowYield
                    self.context.allowAwait = previousAwait
            else:
                if self.matchAssign():
                    if not self.context.isAssignmentTarget:
                        self.tolerateError(Messages.InvalidLHSInAssignment)

                    if self.context.strict and expr.type is JSNode.Identifier:
                        assert isinstance(expr, nodes.Identifier)
                        identifier: nodes.Identifier = expr
                        if self.scanner.isRestrictedWord(identifier.name):
                            self.tolerateUnexpectedToken(token, Messages.StrictLHSAssignment)
                        if self.scanner.isStrictModeReservedWord(identifier.name):
                            self.tolerateUnexpectedToken(token, Messages.StrictReservedWord)

                    if not self.match('='):
                        self.context.isAssignmentTarget = False
                        self.context.isBindingElement = False
                    else:
                        self.reinterpretExpressionAsPattern(expr)

                    token = self.nextToken()
                    operator = token.content
                    right = self.ast.addNode(
                        self.isolateCoverGrammar(self.parseAssignmentExpression))
                    expr = self.finalize(self.startNode(startToken),
                                         nodes.AssignmentExpression(operator,
                                                                    self.ast.addNode(expr), right))
                    self.context.firstCoverInitializedNameError = None

        return expr

    # https://tc39.github.io/ecma262/#sec-comma-operator

    def parseExpression(self) -> nodes.SequenceExpression:
        startToken = self.lookahead
        expr = self.isolateCoverGrammar(self.parseAssignmentExpression)

        if self.match(','):
            expressions: list[int] = [self.ast.addNode(expr)]
            while self.lookahead.kind is not JSToken.EOF:
                if not self.match(','):
                    break
                self.nextToken()
                expressions.append(
                    self.ast.addNode(self.isolateCoverGrammar(self.parseAssignmentExpression)))

            expr = self.finalize(self.startNode(startToken), nodes.SequenceExpression(expressions))

        return expr

    # https://tc39.github.io/ecma262/#sec-block

    def parseStatementListItem(self):
        self.context.isAssignmentTarget = True
        self.context.isBindingElement = True
        if self.lookahead.kind is JSToken.Keyword:
            value = self.lookahead.content
            if value == 'export':
                if not self.context.isModule:
                    self.tolerateUnexpectedToken(self.lookahead, Messages.IllegalExportDeclaration)
                statement = self.parseExportDeclaration()
            elif value == 'import':
                if self.matchImportCall():
                    statement = self.parseExpressionStatement()
                else:
                    if not self.context.isModule:
                        self.tolerateUnexpectedToken(self.lookahead,
                                                     Messages.IllegalImportDeclaration)
                    statement = self.parseImportDeclaration()
            elif value == 'const':
                statement = self.parseLexicalDeclaration(Params(inFor=False))
            elif value == 'function':
                statement = self.parseFunctionDeclaration()
            elif value == 'class':
                statement = self.parseClassDeclaration()
            elif value == 'let':
                statement = self.parseLexicalDeclaration(
                    Params(inFor=False)) if self.isLexicalDeclaration() else self.parseStatement()
            else:
                statement = self.parseStatement()
        else:
            statement = self.parseStatement()

        return statement

    def parseBlock(self) -> nodes.BlockStatement:
        node = self.createNode()

        self.expect('{')
        block: list[int] = []
        while True:
            if self.match('}'):
                break
            block.append(self.ast.addNode(self.parseStatementListItem()))
        self.expect('}')

        return self.finalize(node, nodes.BlockStatement(block))

    # https://tc39.github.io/ecma262/#sec-let-and-const-declarations

    def parseLexicalBinding(self, kind: str, options: Params) -> nodes.VariableDeclarator:
        # let <A = 9>, b, c = 6
        node = self.createNode()
        params = []
        id = self.parsePattern(params, kind)

        if self.context.strict and id.type is JSNode.Identifier:
            if self.scanner.isRestrictedWord(id.name):
                self.tolerateError(Messages.StrictVarName)

        init = None
        if kind == 'const':
            if not self.matchKeyword('in') and not self.matchContextualKeyword('of'):
                if self.match('='):
                    self.nextToken()
                    init = self.ast.addNode(
                        self.isolateCoverGrammar(self.parseAssignmentExpression))
                else:
                    self.throwError(Messages.DeclarationMissingInitializer, 'const')
        elif (not options.inFor and id.type is not JSNode.Identifier) or self.match('='):
            self.expect('=')
            init = self.ast.addNode(self.isolateCoverGrammar(self.parseAssignmentExpression))

        return self.finalize(node, nodes.VariableDeclarator(self.ast.addNode(id), init))

    def parseBindingList(self, kind: str, options: Params) -> list[nodes.VariableDeclarator]:
        # let <A = 9, B, C = 6>
        lst = [self.parseLexicalBinding(kind, options)]

        while self.match(','):
            self.nextToken()
            lst.append(self.parseLexicalBinding(kind, options))

        return lst

    def isLexicalDeclaration(self) -> bool:
        state = self.scanner.saveState()
        self.scanner.scanComments()
        nextToken = self.scanner.lex()
        self.scanner.restoreState(state)

        return (
                (nextToken.kind is JSToken.Identifier) or
                (nextToken.kind is JSToken.Punctuator and nextToken.content == '[') or
                (nextToken.kind is JSToken.Punctuator and nextToken.content == '{') or
                (nextToken.kind is JSToken.Keyword and nextToken.content == 'let') or
                (nextToken.kind is JSToken.Keyword and nextToken.content == 'yield')
        )

    def parseLexicalDeclaration(self, options: Params) -> nodes.VariableDeclaration:
        # <LET A = 9, B, C = 6>
        node = self.createNode()
        kind = self.nextToken().content
        assert kind == 'let' or kind == 'const', 'Lexical declaration must be either or const'

        declarations = self.ast.addNodes(self.parseBindingList(kind, options))
        self.consumeSemicolon()

        return self.finalize(node, nodes.VariableDeclaration(declarations, kind))

    # https://tc39.github.io/ecma262/#sec-destructuring-binding-patterns

    def parseBindingRestElement(self, params, kind=None) -> nodes.RestElement:
        node = self.createNode()

        self.expect('...')
        arg = self.ast.addNode(self.parsePattern(params, kind))

        return self.finalize(node, nodes.RestElement(arg))

    def parseArrayPattern(self, params, kind=None) -> nodes.ArrayPattern:
        node = self.createNode()

        self.expect('[')
        elements: list[int | None] = []
        while not self.match(']'):
            if self.match(','):
                self.nextToken()
                elements.append(None)
            else:
                if self.match('...'):
                    elements.append(self.ast.addNode(self.parseBindingRestElement(params, kind)))
                    break
                else:
                    elements.append(self.ast.addNode(self.parsePatternWithDefault(params, kind)))
                if not self.match(']'):
                    self.expect(',')
        self.expect(']')

        return self.finalize(node, nodes.ArrayPattern(elements))

    def parsePropertyPattern(self, params, kind=None) -> nodes.Property:
        node = self.createNode()

        computed = False
        shorthand = False
        method = False

        key = None

        if self.lookahead.kind is JSToken.Identifier:
            keyToken = self.lookahead
            key = self.ast.addNode(self.parseVariableIdentifier())
            init = self.ast.addNode(self.finalize(node, nodes.Identifier(keyToken.content)))
            if self.match('='):
                params.append(keyToken)
                shorthand = True
                self.nextToken()
                expr = self.ast.addNode(self.parseAssignmentExpression())
                value = self.ast.addNode(
                    self.finalize(self.startNode(keyToken), nodes.AssignmentPattern(init, expr)))
            elif not self.match(':'):
                params.append(keyToken)
                shorthand = True
                value = init
            else:
                self.expect(':')
                value = self.ast.addNode(self.parsePatternWithDefault(params, kind))
        else:
            computed = self.match('[')
            key = self.ast.addNode(self.parseObjectPropertyKey())
            self.expect(':')
            value = self.ast.addNode(self.parsePatternWithDefault(params, kind))

        return self.finalize(node, nodes.Property('init', key, computed, value, method, shorthand))

    def parseRestProperty(self, params, kind) -> nodes.RestElement:
        node = self.createNode()
        self.expect('...')
        arg = self.ast.addNode(self.parsePattern(params))
        if self.match('='):
            self.throwError(Messages.DefaultRestProperty)
        if not self.match('}'):
            self.throwError(Messages.PropertyAfterRestProperty)
        return self.finalize(node, nodes.RestElement(arg))

    def parseObjectPattern(self, params, kind=None) -> nodes.ObjectPattern:
        node = self.createNode()
        properties: list[int] = []

        self.expect('{')
        while not self.match('}'):
            properties.append(self.ast.addNode(self.parseRestProperty(params, kind) if self.match(
                '...') else self.parsePropertyPattern(params, kind)))
            if not self.match('}'):
                self.expect(',')
        self.expect('}')

        return self.finalize(node, nodes.ObjectPattern(properties))

    def parsePattern(self, params,
                     kind=None) -> nodes.ArrayPattern | nodes.ObjectPattern | nodes.Identifier:
        if self.match('['):
            pattern = self.parseArrayPattern(params, kind)
        elif self.match('{'):
            pattern = self.parseObjectPattern(params, kind)
        else:
            if self.matchKeyword('let') and (kind in ('const', 'let')):
                self.tolerateUnexpectedToken(self.lookahead, Messages.LetInLexicalBinding)
            params.append(self.lookahead)
            pattern = self.parseVariableIdentifier(kind)

        return pattern

    def parsePatternWithDefault(self, params,
                                kind=None) -> nodes.ArrayPattern | nodes.ObjectPattern | nodes.Identifier | nodes.AssignmentPattern:
        startToken = self.lookahead

        pattern = self.parsePattern(params, kind)
        if self.match('='):
            self.nextToken()
            previousAllowYield = self.context.allowYield
            self.context.allowYield = True
            right = self.ast.addNode(self.isolateCoverGrammar(self.parseAssignmentExpression))
            self.context.allowYield = previousAllowYield
            pattern = self.finalize(self.startNode(startToken),
                                    nodes.AssignmentPattern(self.ast.addNode(pattern), right))

        return pattern

    # https://tc39.github.io/ecma262/#sec-variable-statement

    def parseVariableIdentifier(self, kind=None) -> nodes.Identifier:
        node = self.createNode()

        token = self.nextToken()
        if token.kind is JSToken.Keyword and token.content == 'yield':
            if self.context.strict:
                self.tolerateUnexpectedToken(token, Messages.StrictReservedWord)
            elif not self.context.allowYield:
                self.throwUnexpectedToken(token)
        elif token.kind is not JSToken.Identifier:
            if (self.context.strict and
                    token.kind is JSToken.Keyword and
                    self.scanner.isStrictModeReservedWord(token.content)):
                self.tolerateUnexpectedToken(token, Messages.StrictReservedWord)
            else:
                if self.context.strict or token.content != 'let' or kind != 'var':
                    self.throwUnexpectedToken(token)
        elif ((self.context.isModule or self.context.allowAwait) and
              token.kind is JSToken.Identifier and
              token.content == 'await'):
            self.tolerateUnexpectedToken(token)

        return self.finalize(node, nodes.Identifier(token.content))

    def parseVariableDeclaration(self, options) -> nodes.VariableDeclarator:
        node = self.createNode()

        params = []
        identifier = self.parsePattern(params, 'var')

        if self.context.strict and identifier.type is JSNode.Identifier:
            if self.scanner.isRestrictedWord(identifier.name):
                self.tolerateError(Messages.StrictVarName)

        init = None
        if self.match('='):
            self.nextToken()
            init = self.ast.addNode(self.isolateCoverGrammar(self.parseAssignmentExpression))
        elif identifier.type is not JSNode.Identifier and not options.inFor:
            self.expect('=')

        return self.finalize(node, nodes.VariableDeclarator(self.ast.addNode(identifier), init))

    def parseVariableDeclarationList(self, options) -> list[nodes.VariableDeclarator]:
        opt = Params(inFor=options.inFor)

        lst = []
        lst.append(self.parseVariableDeclaration(opt))
        while self.match(','):
            self.nextToken()
            lst.append(self.parseVariableDeclaration(opt))

        return lst

    def parseVariableStatement(self) -> nodes.VariableDeclaration:
        node = self.createNode()
        self.expectKeyword('var')
        declarations = self.ast.addNodes(self.parseVariableDeclarationList(Params(inFor=False)))
        self.consumeSemicolon()

        return self.finalize(node, nodes.VariableDeclaration(declarations, 'var'))

    # https://tc39.github.io/ecma262/#sec-empty-statement

    def parseEmptyStatement(self) -> nodes.EmptyStatement:
        node = self.createNode()
        self.expect(';')
        return self.finalize(node, nodes.EmptyStatement())

    # https://tc39.github.io/ecma262/#sec-expression-statement

    def parseExpressionStatement(self) -> nodes.ExpressionStatement:
        node = self.createNode()
        expr = self.ast.addNode(self.parseExpression())
        self.consumeSemicolon()
        return self.finalize(node, nodes.ExpressionStatement(expr))

    # https://tc39.github.io/ecma262/#sec-if-statement

    def parseIfClause(self) -> nodes.Node:
        if self.context.strict and self.matchKeyword('function'):
            self.tolerateError(Messages.StrictFunction)
        return self.parseStatement()

    def parseIfStatement(self) -> nodes.IfStatement:
        node = self.createNode()
        alternate = None

        self.expectKeyword('if')
        self.expect('(')
        test = self.ast.addNode(self.parseExpression())

        if not self.match(')') and self.config.tolerant:
            self.tolerateUnexpectedToken(self.nextToken())
            consequent = self.ast.addNode(self.finalize(self.createNode(), nodes.EmptyStatement()))
        else:
            self.expect(')')
            consequent = self.ast.addNode(self.parseIfClause())
            if self.matchKeyword('else'):
                self.nextToken()
                alternate = self.ast.addNode(self.parseIfClause())

        return self.finalize(node, nodes.IfStatement(test, consequent, alternate))

    # https://tc39.github.io/ecma262/#sec-do-while-statement

    def parseDoWhileStatement(self) -> nodes.DoWhileStatement:
        node = self.createNode()
        self.expectKeyword('do')

        previousInIteration = self.context.inIteration
        self.context.inIteration = True
        body = self.ast.addNode(self.parseStatement())
        self.context.inIteration = previousInIteration

        self.expectKeyword('while')
        self.expect('(')
        test = self.ast.addNode(self.parseExpression())

        if not self.match(')') and self.config.tolerant:
            self.tolerateUnexpectedToken(self.nextToken())
        else:
            self.expect(')')
            if self.match(';'):
                self.nextToken()

        return self.finalize(node, nodes.DoWhileStatement(body, test))

    # https://tc39.github.io/ecma262/#sec-while-statement

    def parseWhileStatement(self) -> nodes.WhileStatement:
        node = self.createNode()

        self.expectKeyword('while')
        self.expect('(')
        test = self.ast.addNode(self.parseExpression())

        if not self.match(')') and self.config.tolerant:
            self.tolerateUnexpectedToken(self.nextToken())
            body = self.ast.addNode(self.finalize(self.createNode(), nodes.EmptyStatement()))
        else:
            self.expect(')')

            previousInIteration = self.context.inIteration
            self.context.inIteration = True
            body = self.ast.addNode(self.parseStatement())
            self.context.inIteration = previousInIteration

        return self.finalize(node, nodes.WhileStatement(test, body))

    # https://tc39.github.io/ecma262/#sec-for-statement
    # https://tc39.github.io/ecma262/#sec-for-in-and-for-of-statements

    def parseForStatement(self) -> nodes.ForStatement | nodes.ForInStatement | nodes.ForOfStatement:
        init = None
        test = None
        update = None
        forIn = True
        left = None
        right = None

        node = self.createNode()
        self.expectKeyword('for')
        self.expect('(')

        if self.match(';'):
            self.nextToken()
        else:
            if self.matchKeyword('var'):
                init: Marker | nodes.Node | None = self.createNode()
                self.nextToken()

                previousAllowIn = self.context.allowIn
                self.context.allowIn = False
                declarations = self.parseVariableDeclarationList(Params(inFor=True))
                self.context.allowIn = previousAllowIn

                if len(declarations) == 1 and self.matchKeyword('in'):
                    decl = declarations[0]
                    if decl.init and (
                            decl.id.type is JSNode.ArrayPattern or decl.id.type is JSNode.ObjectPattern or self.context.strict):
                        self.tolerateError(Messages.ForInOfLoopInitializer, 'for-in')
                    init = self.finalize(init,
                                         nodes.VariableDeclaration(self.ast.addNodes(declarations),
                                                                   'var'))
                    self.nextToken()
                    left = init
                    right = self.parseExpression()
                    init = None
                elif (len(declarations) == 1 and
                      declarations[0].init is None and
                      self.matchContextualKeyword('of')):
                    assert isinstance(init, Marker)
                    init = self.finalize(init,
                                         nodes.VariableDeclaration(self.ast.addNodes(declarations),
                                                                   'var'))
                    self.nextToken()
                    left = init
                    right = self.parseAssignmentExpression()
                    init = None
                    forIn = False
                else:
                    init = self.finalize(init,
                                         nodes.VariableDeclaration(self.ast.addNodes(declarations),
                                                                   'var'))
                    self.expect(';')
            elif self.matchKeyword('const', 'let'):
                init = self.createNode()
                kind = self.nextToken().content

                if not self.context.strict and self.lookahead.content == 'in':
                    init = self.finalize(init, nodes.Identifier(kind))
                    self.nextToken()
                    left = init
                    right = self.parseExpression()
                    init = None
                else:
                    previousAllowIn = self.context.allowIn
                    self.context.allowIn = False
                    declarations: list[nodes.VariableDeclarator] = self.parseBindingList(kind,
                                                                                         Params(
                                                                                             inFor=True))
                    self.context.allowIn = previousAllowIn

                    if (len(declarations) == 1 and
                            declarations[0].init is None and
                            self.matchKeyword('in')):
                        assert isinstance(init, Marker)
                        init = self.finalize(init, nodes.VariableDeclaration(
                            self.ast.addNodes(declarations), kind))
                        self.nextToken()
                        left = init
                        right = self.parseExpression()
                        init = None
                    elif (len(declarations) == 1 and
                          declarations[0].init is None and
                          self.matchContextualKeyword('of')):
                        assert isinstance(init, Marker)
                        init = self.finalize(init, nodes.VariableDeclaration(
                            self.ast.addNodes(declarations), kind))
                        self.nextToken()
                        left = init
                        right = self.parseAssignmentExpression()
                        init = None
                        forIn = False
                    else:
                        self.consumeSemicolon()
                        init = self.finalize(init, nodes.VariableDeclaration(
                            self.ast.addNodes(declarations), kind))
            else:
                initStartToken = self.lookahead
                previousAllowIn = self.context.allowIn
                self.context.allowIn = False
                init = self.inheritCoverGrammar(self.parseAssignmentExpression)
                self.context.allowIn = previousAllowIn

                if self.matchKeyword('in'):
                    if not self.context.isAssignmentTarget or init.type is JSNode.AssignmentExpression:
                        self.tolerateError(Messages.InvalidLHSInForIn)

                    self.nextToken()
                    self.reinterpretExpressionAsPattern(init)
                    left = init
                    right = self.parseExpression()
                    init = None
                elif self.matchContextualKeyword('of'):
                    if not self.context.isAssignmentTarget or init.type is JSNode.AssignmentExpression:
                        self.tolerateError(Messages.InvalidLHSInForLoop)

                    self.nextToken()
                    self.reinterpretExpressionAsPattern(init)
                    left = init
                    right = self.parseAssignmentExpression()
                    init = None
                    forIn = False
                else:
                    if self.match(','):
                        initSeq: list[int] = [self.ast.addNode(init)]
                        while self.match(','):
                            self.nextToken()
                            initSeq.append(self.ast.addNode(
                                self.isolateCoverGrammar(self.parseAssignmentExpression)))
                        init = self.finalize(self.startNode(initStartToken),
                                             nodes.SequenceExpression(initSeq))
                    self.expect(';')

        if left is None:
            if not self.match(';'):
                test = self.parseExpression()
            self.expect(';')
            if not self.match(')'):
                update = self.parseExpression()

        if not self.match(')') and self.config.tolerant:
            self.tolerateUnexpectedToken(self.nextToken())
            body = self.finalize(self.createNode(), nodes.EmptyStatement())
        else:
            self.expect(')')

            previousInIteration = self.context.inIteration
            self.context.inIteration = True
            body = self.isolateCoverGrammar(self.parseStatement)
            self.context.inIteration = previousInIteration

        initI = self.ast.addNode(init) if init else None
        testI = self.ast.addNode(test) if test else None
        updateI = self.ast.addNode(update) if update else None
        bodyI = self.ast.addNode(body) if body else None
        leftI = self.ast.addNode(left) if left else None
        rightI = self.ast.addNode(right) if right else None

        if left is None:
            return self.finalize(node,
                                 nodes.ForStatement(initI, testI, updateI, bodyI))

        if forIn:
            return self.finalize(node, nodes.ForInStatement(leftI, rightI, bodyI))

        return self.finalize(node,
                             nodes.ForOfStatement(leftI, rightI, bodyI))

    # https://tc39.github.io/ecma262/#sec-continue-statement

    def parseContinueStatement(self) -> nodes.ContinueStatement:
        node = self.createNode()
        self.expectKeyword('continue')

        label = None
        if self.lookahead.kind is JSToken.Identifier and not self.hasLineTerminator:
            id = self.parseVariableIdentifier()
            label = self.ast.addNode(id)

            key = '$' + id.name
            if key not in self.context.labelSet:
                self.throwError(Messages.UnknownLabel, id.name)

        self.consumeSemicolon()
        if label is None and not self.context.inIteration:
            self.throwError(Messages.IllegalContinue)

        return self.finalize(node, nodes.ContinueStatement(label))

    # https://tc39.github.io/ecma262/#sec-break-statement

    def parseBreakStatement(self) -> nodes.BreakStatement:
        node = self.createNode()
        self.expectKeyword('break')

        label = None
        if self.lookahead.kind is JSToken.Identifier and not self.hasLineTerminator:
            id = self.parseVariableIdentifier()

            key = '$' + id.name
            if key not in self.context.labelSet:
                self.throwError(Messages.UnknownLabel, id.name)
            label = self.ast.addNode(id)

        self.consumeSemicolon()
        if label is None and not self.context.inIteration and not self.context.inSwitch:
            self.throwError(Messages.IllegalBreak)

        return self.finalize(node, nodes.BreakStatement(label))

    # https://tc39.github.io/ecma262/#sec-return-statement

    def parseReturnStatement(self) -> nodes.ReturnStatement:
        if not self.context.inFunctionBody:
            self.tolerateError(Messages.IllegalReturn)

        node = self.createNode()
        self.expectKeyword('return')

        hasArgument = (
                (
                        not self.match(';') and not self.match('}') and
                        not self.hasLineTerminator and self.lookahead.kind is not JSToken.EOF
                ) or
                self.lookahead.kind is JSToken.StringLiteral or
                self.lookahead.kind is JSToken.Template
        )
        argument = self.ast.addNode(self.parseExpression()) if hasArgument else None
        self.consumeSemicolon()

        return self.finalize(node, nodes.ReturnStatement(argument))

    # https://tc39.github.io/ecma262/#sec-with-statement

    def parseWithStatement(self) -> nodes.WithStatement:
        if self.context.strict:
            self.tolerateError(Messages.StrictModeWith)

        node = self.createNode()

        self.expectKeyword('with')
        self.expect('(')
        object = self.ast.addNode(self.parseExpression())

        if not self.match(')') and self.config.tolerant:
            self.tolerateUnexpectedToken(self.nextToken())
            body = self.ast.addNode(self.finalize(self.createNode(), nodes.EmptyStatement()))
        else:
            self.expect(')')
            body = self.ast.addNode(self.parseStatement())

        return self.finalize(node, nodes.WithStatement(object, body))

    # https://tc39.github.io/ecma262/#sec-switch-statement

    def parseSwitchCase(self) -> nodes.SwitchCase:
        node = self.createNode()

        if self.matchKeyword('default'):
            self.nextToken()
            test = None
        else:
            self.expectKeyword('case')
            test = self.ast.addNode(self.parseExpression())
        self.expect(':')

        consequent: list[int] = []
        while True:
            if self.match('}') or self.matchKeyword('default', 'case'):
                break
            consequent.append(self.ast.addNode(self.parseStatementListItem()))

        return self.finalize(node, nodes.SwitchCase(test, consequent))

    def parseSwitchStatement(self) -> nodes.SwitchStatement:
        node = self.createNode()
        self.expectKeyword('switch')

        self.expect('(')
        discriminant = self.ast.addNode(self.parseExpression())
        self.expect(')')

        previousInSwitch = self.context.inSwitch
        self.context.inSwitch = True

        cases: list[int] = []
        defaultFound = False
        self.expect('{')
        while True:
            if self.match('}'):
                break
            clause = self.parseSwitchCase()
            if clause.test is None:
                if defaultFound:
                    self.throwError(Messages.MultipleDefaultsInSwitch)
                defaultFound = True
            cases.append(self.ast.addNode(clause))
        self.expect('}')

        self.context.inSwitch = previousInSwitch

        return self.finalize(node, nodes.SwitchStatement(discriminant, cases))

    # https://tc39.github.io/ecma262/#sec-labelled-statements

    def parseLabelledStatement(self) -> nodes.LabeledStatement | nodes.ExpressionStatement:
        node = self.createNode()
        expr = self.parseExpression()

        if expr.type is JSNode.Identifier and self.match(':'):
            self.nextToken()

            assert isinstance(expr, nodes.Identifier)
            identifier = expr
            key = '$' + identifier.name
            if key in self.context.labelSet:
                self.throwError(Messages.Redeclaration, 'Label', identifier.name)

            self.context.labelSet[key] = True
            if self.matchKeyword('class'):
                self.tolerateUnexpectedToken(self.lookahead)
                body = self.parseClassDeclaration()
            elif self.matchKeyword('function'):
                token = self.lookahead
                declaration = self.parseFunctionDeclaration()
                if self.context.strict:
                    self.tolerateUnexpectedToken(token, Messages.StrictFunction)
                elif declaration.generator:
                    self.tolerateUnexpectedToken(token, Messages.GeneratorInLegacyContext)
                body = declaration
            else:
                body = self.parseStatement()
            del self.context.labelSet[key]

            statement = nodes.LabeledStatement(self.ast.addNode(identifier), self.ast.addNode(body))
        else:
            self.consumeSemicolon()
            statement = nodes.ExpressionStatement(self.ast.addNode(expr))

        return self.finalize(node, statement)

    # https://tc39.github.io/ecma262/#sec-throw-statement

    def parseThrowStatement(self) -> nodes.ThrowStatement:
        node = self.createNode()
        self.expectKeyword('throw')

        if self.hasLineTerminator:
            self.throwError(Messages.NewlineAfterThrow)

        argument = self.ast.addNode(self.parseExpression())
        self.consumeSemicolon()

        return self.finalize(node, nodes.ThrowStatement(argument))

    # https://tc39.github.io/ecma262/#sec-try-statement

    def parseCatchClause(self) -> nodes.CatchClause:
        node = self.createNode()

        self.expectKeyword('catch')

        if self.match("("):  # If we provide the caught var name
            # catch (e) {...}
            self.expect('(')
            if self.match(')'):
                self.throwUnexpectedToken(self.lookahead)

            params: list[RawToken] = []
            param = self.parsePattern(params)
            paramI = self.ast.addNode(param)
            paramMap = {}
            for p in params:
                key = '$' + p.content
                if key in paramMap:
                    self.tolerateError(Messages.DuplicateBinding, p.content)
                paramMap[key] = True

            if self.context.strict and param.type is JSNode.Identifier:
                if self.scanner.isRestrictedWord(param.name):
                    self.tolerateError(Messages.StrictCatchVariable)

            self.expect(')')
        else:
            # catch {...}
            # param = None
            paramI = None
        body = self.ast.addNode(self.parseBlock())

        return self.finalize(node, nodes.CatchClause(paramI, body))

    def parseFinallyClause(self) -> nodes.BlockStatement:
        self.expectKeyword('finally')
        return self.parseBlock()

    def parseTryStatement(self) -> nodes.TryStatement:
        node = self.createNode()
        self.expectKeyword('try')

        block = self.ast.addNode(self.parseBlock())
        handler = self.ast.addNode(self.parseCatchClause()) if self.matchKeyword('catch') else None
        finalizer = self.ast.addNode(self.parseFinallyClause()) if self.matchKeyword(
            'finally') else None

        if not handler and not finalizer:
            self.throwError(Messages.NoCatchOrFinally)

        return self.finalize(node, nodes.TryStatement(block, handler, finalizer))

    # https://tc39.github.io/ecma262/#sec-debugger-statement

    def parseDebuggerStatement(self) -> nodes.DebuggerStatement:
        node = self.createNode()
        self.expectKeyword('debugger')
        self.consumeSemicolon()
        return self.finalize(node, nodes.DebuggerStatement())

    # https://tc39.github.io/ecma262/#sec-ecmascript-language-statements-and-declarations

    def parseStatement(self) -> (nodes.IfStatement |
                                 nodes.SwitchStatement |
                                 nodes.TryStatement |
                                 nodes.ThrowStatement |
                                 nodes.DebuggerStatement |
                                 nodes.BlockStatement |
                                 nodes.ExpressionStatement |
                                 nodes.LabeledStatement |
                                 nodes.WithStatement |
                                 nodes.ReturnStatement |
                                 nodes.BreakStatement |
                                 nodes.ContinueStatement |
                                 nodes.ForOfStatement |
                                 nodes.ForInStatement |
                                 nodes.ForStatement |
                                 nodes.WhileStatement |
                                 nodes.DoWhileStatement |
                                 nodes.EmptyStatement |
                                 nodes.FunctionDeclaration |
                                 nodes.AsyncFunctionDeclaration):
        typ = self.lookahead.kind
        if typ in (
                JSToken.BooleanLiteral,
                JSToken.NullLiteral,
                JSToken.NumericLiteral,
                JSToken.StringLiteral,
                JSToken.Template,
                JSToken.RegularExpression,
        ):
            statement = self.parseExpressionStatement()

        elif typ is JSToken.Punctuator:
            value = self.lookahead.content
            if value == '{':
                statement = self.parseBlock()
            elif value == '(':
                statement = self.parseExpressionStatement()
            elif value == ';':
                statement = self.parseEmptyStatement()
            else:
                statement = self.parseExpressionStatement()

        elif typ is JSToken.Identifier:
            if self.matchAsyncFunction():
                statement = self.parseFunctionDeclaration()
            else:
                statement = self.parseLabelledStatement()

        elif typ is JSToken.Keyword:
            value = self.lookahead.content
            if value == 'break':
                statement = self.parseBreakStatement()
            elif value == 'continue':
                statement = self.parseContinueStatement()
            elif value == 'debugger':
                statement = self.parseDebuggerStatement()
            elif value == 'do':
                statement = self.parseDoWhileStatement()
            elif value == 'for':
                statement = self.parseForStatement()
            elif value == 'function':
                statement = self.parseFunctionDeclaration()
            elif value == 'if':
                statement = self.parseIfStatement()
            elif value == 'return':
                statement = self.parseReturnStatement()
            elif value == 'switch':
                statement = self.parseSwitchStatement()
            elif value == 'throw':
                statement = self.parseThrowStatement()
            elif value == 'try':
                statement = self.parseTryStatement()
            elif value == 'var':
                statement = self.parseVariableStatement()
            elif value == 'while':
                statement = self.parseWhileStatement()
            elif value == 'with':
                statement = self.parseWithStatement()
            else:
                statement = self.parseExpressionStatement()

        else:
            statement = self.throwUnexpectedToken(self.lookahead)

        return statement

    # https://tc39.github.io/ecma262/#sec-function-definitions

    def parseFunctionSourceElements(self) -> nodes.BlockStatement:
        node = self.createNode()

        self.expect('{')
        body = self.parseDirectivePrologues()

        previousLabelSet = self.context.labelSet
        previousInIteration = self.context.inIteration
        previousInSwitch = self.context.inSwitch
        previousInFunctionBody = self.context.inFunctionBody

        self.context.labelSet = {}
        self.context.inIteration = False
        self.context.inSwitch = False
        self.context.inFunctionBody = True

        while self.lookahead.kind is not JSToken.EOF:
            if self.match('}'):
                break
            body.append(self.parseStatementListItem())

        self.expect('}')

        self.context.labelSet = previousLabelSet
        self.context.inIteration = previousInIteration
        self.context.inSwitch = previousInSwitch
        self.context.inFunctionBody = previousInFunctionBody

        return self.finalize(node, nodes.BlockStatement(self.ast.addNodes(body)))

    def validateParam(self, options: Params, param: nodes.Node | RawToken, name: str):
        # TODO Explore the param argument - node or token?
        key = '$' + name
        if self.context.strict:
            if self.scanner.isRestrictedWord(name):
                options.stricted = param
                options.message = Messages.StrictParamName
            if key in options.paramSet:
                options.stricted = param
                options.message = Messages.StrictParamDupe
        elif not options.firstRestricted:
            if self.scanner.isRestrictedWord(name):
                options.firstRestricted = param
                options.message = Messages.StrictParamName
            elif self.scanner.isStrictModeReservedWord(name):
                options.firstRestricted = param
                options.message = Messages.StrictReservedWord
            elif key in options.paramSet:
                options.stricted = param
                options.message = Messages.StrictParamDupe

        options.paramSet[key] = True

    def parseRestElement(self, params) -> nodes.RestElement:
        node = self.createNode()

        self.expect('...')
        arg = self.ast.addNode(self.parsePattern(params))
        if self.match('='):
            self.throwError(Messages.DefaultRestParameter)
        if not self.match(')'):
            self.throwError(Messages.ParameterAfterRestParameter)

        return self.finalize(node, nodes.RestElement(arg))

    def parseFormalParameter(self, options: Params):
        params: list[RawToken] = []
        param = self.parseRestElement(params) if self.match(
            '...') else self.parsePatternWithDefault(params)
        for p in params:
            self.validateParam(options, p, p.content)
        options.simple = options.simple and isinstance(param, nodes.Identifier)
        options.params.append(param)

    def parseFormalParameters(self, firstRestricted=None) -> Params:
        options = Params(
            simple=True,
            params=[],
            firstRestricted=firstRestricted
        )

        self.expect('(')
        if not self.match(')'):
            options.paramSet = {}
            while self.lookahead.kind is not JSToken.EOF:
                self.parseFormalParameter(options)
                if self.match(')'):
                    break
                self.expect(',')
                if self.match(')'):
                    break
        self.expect(')')

        return Params(
            simple=options.simple,
            params=options.params,
            stricted=options.stricted,
            firstRestricted=options.firstRestricted,
            message=options.message
        )

    def matchAsyncFunction(self) -> bool:
        match = self.matchContextualKeyword('async')
        if match:
            state = self.scanner.saveState()
            self.scanner.scanComments()
            next = self.scanner.lex()
            self.scanner.restoreState(state)

            match = ((state.lineNumber == next.lineNumber) and
                     (next.kind is JSToken.Keyword) and
                     (next.content == 'function'))

        return match

    def parseFunctionDeclaration(self, identifierIsOptional=False) \
            -> nodes.FunctionDeclaration | nodes.AsyncFunctionDeclaration:
        node = self.createNode()

        isAsync = self.matchContextualKeyword('async')
        if isAsync:
            self.nextToken()

        self.expectKeyword('function')

        isGenerator = False if isAsync else self.match('*')
        if isGenerator:
            self.nextToken()

        id = None
        firstRestricted = None

        message = None  # I added that

        if not identifierIsOptional or not self.match('('):
            token = self.lookahead
            id = self.parseVariableIdentifier()
            if self.context.strict:
                if self.scanner.isRestrictedWord(token.content):
                    self.tolerateUnexpectedToken(token, Messages.StrictFunctionName)
            else:
                if self.scanner.isRestrictedWord(token.content):
                    firstRestricted = token
                    message = Messages.StrictFunctionName
                elif self.scanner.isStrictModeReservedWord(token.content):
                    firstRestricted = token
                    message = Messages.StrictReservedWord

        previousAllowAwait = self.context.allowAwait
        previousAllowYield = self.context.allowYield
        self.context.allowAwait = isAsync
        self.context.allowYield = not isGenerator

        formalParameters = self.parseFormalParameters(firstRestricted)
        params = self.ast.addNodes(formalParameters.params)
        stricted = formalParameters.stricted
        firstRestricted = formalParameters.firstRestricted
        if formalParameters.message:
            message = formalParameters.message

        previousStrict = self.context.strict
        previousAllowStrictDirective = self.context.allowStrictDirective
        self.context.allowStrictDirective = formalParameters.simple
        body = self.ast.addNode(self.parseFunctionSourceElements())
        if self.context.strict and firstRestricted:
            self.throwUnexpectedToken(firstRestricted, message)
        if self.context.strict and stricted:
            self.tolerateUnexpectedToken(stricted, message)

        self.context.strict = previousStrict
        self.context.allowStrictDirective = previousAllowStrictDirective
        self.context.allowAwait = previousAllowAwait
        self.context.allowYield = previousAllowYield

        idI = self.ast.addNode(id) if id else None

        if isAsync:
            return self.finalize(node, nodes.AsyncFunctionDeclaration(idI, params, body))

        return self.finalize(node, nodes.FunctionDeclaration(idI, params, body, isGenerator))

    def parseFunctionExpression(self) -> nodes.FunctionExpression | nodes.AsyncFunctionExpression:
        node = self.createNode()

        isAsync = self.matchContextualKeyword('async')
        if isAsync:
            self.nextToken()

        self.expectKeyword('function')

        isGenerator = False if isAsync else self.match('*')
        if isGenerator:
            self.nextToken()

        id = None
        firstRestricted = None

        previousAllowAwait = self.context.allowAwait
        previousAllowYield = self.context.allowYield
        self.context.allowAwait = isAsync
        self.context.allowYield = not isGenerator

        message = None  # I added that

        if not self.match('('):
            token = self.lookahead
            id = self.ast.addNode(
                self.parseIdentifierName() if not self.context.strict and not isGenerator and self.matchKeyword(
                    'yield') else self.parseVariableIdentifier())
            if self.context.strict:
                if self.scanner.isRestrictedWord(token.content):
                    self.tolerateUnexpectedToken(token, Messages.StrictFunctionName)
            else:
                if self.scanner.isRestrictedWord(token.content):
                    firstRestricted = token
                    message = Messages.StrictFunctionName
                elif self.scanner.isStrictModeReservedWord(token.content):
                    firstRestricted = token
                    message = Messages.StrictReservedWord

        formalParameters = self.parseFormalParameters(firstRestricted)
        paramIndexes = self.ast.addNodes(formalParameters.params)
        stricted = formalParameters.stricted
        firstRestricted = formalParameters.firstRestricted
        if formalParameters.message:
            message = formalParameters.message

        previousStrict = self.context.strict
        previousAllowStrictDirective = self.context.allowStrictDirective
        self.context.allowStrictDirective = formalParameters.simple
        bodyIndex = self.ast.addNode(self.parseFunctionSourceElements())
        if self.context.strict and firstRestricted:
            self.throwUnexpectedToken(firstRestricted, message)
        if self.context.strict and stricted:
            self.tolerateUnexpectedToken(stricted, message)
        self.context.strict = previousStrict
        self.context.allowStrictDirective = previousAllowStrictDirective
        self.context.allowAwait = previousAllowAwait
        self.context.allowYield = previousAllowYield

        if isAsync:
            return self.finalize(node, nodes.AsyncFunctionExpression(id, paramIndexes, bodyIndex))

        return self.finalize(node,
                             nodes.FunctionExpression(id, paramIndexes, bodyIndex, isGenerator))

    # https://tc39.github.io/ecma262/#sec-directive-prologues-and-the-use-strict-directive

    def parseDirective(self) -> nodes.Directive | nodes.ExpressionStatement:
        token = self.lookahead

        node = self.createNode()
        expr = self.parseExpression()
        directive = self.getTokenRaw(token)[1:-1] if expr.type is JSNode.Literal else None
        self.consumeSemicolon()

        if directive:
            return self.finalize(node, nodes.Directive(self.ast.addNode(expr), directive))

        return self.finalize(node, nodes.ExpressionStatement(self.ast.addNode(expr)))

    def parseDirectivePrologues(self) -> list[nodes.Directive | nodes.ExpressionStatement]:
        firstRestricted = None

        body = []
        while True:
            token = self.lookahead
            if token.kind is not JSToken.StringLiteral:
                break

            statement = self.parseDirective()
            body.append(statement)
            directive = statement.directive if isinstance(statement, nodes.Directive) else None
            if not isinstance(directive, str):
                break

            if directive == 'use strict':
                self.context.strict = True
                if firstRestricted:
                    self.tolerateUnexpectedToken(firstRestricted, Messages.StrictOctalLiteral)
                if not self.context.allowStrictDirective:
                    self.tolerateUnexpectedToken(token, Messages.IllegalLanguageModeDirective)
            else:
                if not firstRestricted and token.octal:
                    firstRestricted = token

        return body

    # https://tc39.github.io/ecma262/#sec-method-definitions

    def qualifiedPropertyName(self, token: RawToken) -> bool:
        typ = token.kind
        if typ in (
                JSToken.Identifier,
                JSToken.StringLiteral,
                JSToken.BooleanLiteral,
                JSToken.NullLiteral,
                JSToken.NumericLiteral,
                JSToken.Keyword,
        ):
            return True
        elif typ is JSToken.Punctuator:
            return token.content == '['
        return False

    def parseGetterMethod(self) -> nodes.FunctionExpression:
        node = self.createNode()

        isGenerator = False
        previousAllowYield = self.context.allowYield
        self.context.allowYield = not isGenerator
        formalParameters = self.parseFormalParameters()
        if len(formalParameters.params) > 0:
            self.tolerateError(Messages.BadGetterArity)
        method = self.ast.addNode(self.parsePropertyMethod(formalParameters))
        self.context.allowYield = previousAllowYield

        return self.finalize(node, nodes.FunctionExpression(None, self.ast.addNodes(
            formalParameters.params), method,
                                                            isGenerator))

    def parseSetterMethod(self) -> nodes.FunctionExpression:
        node = self.createNode()

        isGenerator = False
        previousAllowYield = self.context.allowYield
        self.context.allowYield = not isGenerator
        formalParameters = self.parseFormalParameters()
        if len(formalParameters.params) != 1:
            self.tolerateError(Messages.BadSetterArity)
        elif isinstance(formalParameters.params[0], nodes.RestElement):
            self.tolerateError(Messages.BadSetterRestParameter)
        method = self.ast.addNode(self.parsePropertyMethod(formalParameters))
        self.context.allowYield = previousAllowYield

        return self.finalize(node, nodes.FunctionExpression(None, self.ast.addNodes(
            formalParameters.params), method,
                                                            isGenerator))

    def parseGeneratorMethod(self) -> nodes.FunctionExpression:
        node = self.createNode()

        isGenerator = True
        previousAllowYield = self.context.allowYield

        self.context.allowYield = True
        params = self.parseFormalParameters()
        self.context.allowYield = False
        method = self.ast.addNode(self.parsePropertyMethod(params))
        self.context.allowYield = previousAllowYield

        return self.finalize(node,
                             nodes.FunctionExpression(None, self.ast.addNodes(params.params),
                                                      method, isGenerator))

    # https://tc39.github.io/ecma262/#sec-generator-function-definitions

    def isStartOfExpression(self) -> bool:
        start = True

        value = self.lookahead.content
        typ = self.lookahead.kind
        if typ is JSToken.Punctuator:
            start = value in ('[', '(', '{', '+', '-', '!', '~', '++', '--', '/',
                              '/=')  # regular expression literal )

        elif typ is JSToken.Keyword:
            start = value in ('class', 'delete', 'function', 'let', 'new',
                              'super', 'this', 'typeof', 'void', 'yield')

        return start

    def parseYieldExpression(self) -> nodes.YieldExpression:
        node = self.createNode()
        self.expectKeyword('yield')

        argument = None
        delegate = False
        if not self.hasLineTerminator:
            previousAllowYield = self.context.allowYield
            self.context.allowYield = False
            delegate = self.match('*')
            if delegate:
                self.nextToken()
                argument = self.ast.addNode(self.parseAssignmentExpression())
            elif self.isStartOfExpression():
                argument = self.ast.addNode(self.parseAssignmentExpression())
            self.context.allowYield = previousAllowYield

        return self.finalize(node, nodes.YieldExpression(argument, delegate))

    # https://tc39.github.io/ecma262/#sec-class-definitions

    def parseClassElement(self, hasConstructor) -> nodes.MethodDefinition | nodes.FieldDefinition:
        token = self.lookahead
        node = self.createNode()

        kind = ''
        key = None
        value = None
        computed = False
        isStatic = False
        isAsync = False

        if self.match('*'):
            self.nextToken()

        else:
            computed = self.match('[')
            key = self.parseObjectPropertyKey()
            id = key
            if id.name == 'static' and (
                    self.qualifiedPropertyName(self.lookahead) or self.match('*')):
                token = self.lookahead
                isStatic = True
                computed = self.match('[')
                if self.match('*'):
                    self.nextToken()
                else:
                    key = self.parseObjectPropertyKey()
            if token.kind is JSToken.Identifier and not self.hasLineTerminator and token.content == 'async':
                punctuator = self.lookahead.content
                if punctuator != ':' and punctuator != '(' and punctuator != '*':
                    isAsync = True
                    token = self.lookahead
                    key = self.parseObjectPropertyKey()
                    if token.kind is JSToken.Identifier and token.content == 'constructor':
                        self.tolerateUnexpectedToken(token, Messages.ConstructorIsAsync)

        lookaheadPropertyKey = self.qualifiedPropertyName(self.lookahead)
        if token.kind is JSToken.Identifier:
            if token.content == 'get' and lookaheadPropertyKey:
                kind = 'get'
                computed = self.match('[')
                key = self.parseObjectPropertyKey()
                self.context.allowYield = False
                value = self.parseGetterMethod()
            elif token.content == 'set' and lookaheadPropertyKey:
                kind = 'set'
                computed = self.match('[')
                key = self.parseObjectPropertyKey()
                value = self.parseSetterMethod()
            elif self.config.classProperties and not self.match('('):
                kind = 'init'
                # id = self.finalize(node, nodes.Identifier(token.content)) Unused lol
                if self.match('='):
                    self.nextToken()
                    value = self.parseAssignmentExpression()

        elif token.kind is JSToken.Punctuator and token.content == '*' and lookaheadPropertyKey:
            kind = 'method'
            computed = self.match('[')
            key = self.parseObjectPropertyKey()
            value = self.parseGeneratorMethod()

        if not kind and key and self.match('('):
            kind = 'method'
            value = self.parsePropertyMethodAsyncFunction() if isAsync else self.parsePropertyMethodFunction()

        if not kind:
            self.throwUnexpectedToken(self.lookahead)

        if not computed:
            if isStatic and self.isPropertyKey(key, 'prototype'):
                self.throwUnexpectedToken(token, Messages.StaticPrototype)
            if not isStatic and self.isPropertyKey(key, 'constructor'):
                if kind != 'method' or (value and value.generator):
                    self.throwUnexpectedToken(token, Messages.ConstructorSpecialMethod)
                if hasConstructor.value:
                    self.throwUnexpectedToken(token, Messages.DuplicateConstructor)
                else:
                    hasConstructor.value = True
                kind = 'constructor'

        keyI = self.ast.addNode(key) if key else None
        valueI = self.ast.addNode(value) if value else None

        if kind in ('constructor', 'method', 'get', 'set'):
            return self.finalize(node,
                                 nodes.MethodDefinition(keyI, computed, valueI, kind, isStatic))

        else:
            return self.finalize(node,
                                 nodes.FieldDefinition(keyI, computed, valueI, kind, isStatic))

    def parseClassElementList(self) -> list[nodes.MethodDefinition | nodes.FieldDefinition]:
        body = []
        hasConstructor = Value(False)

        self.expect('{')
        while not self.match('}'):
            if self.match(';'):
                self.nextToken()
            else:
                body.append(self.parseClassElement(hasConstructor))
        self.expect('}')

        return body

    def parseClassBody(self) -> nodes.ClassBody:
        node = self.createNode()
        elementList = self.ast.addNodes(self.parseClassElementList())

        return self.finalize(node, nodes.ClassBody(elementList))

    def parseClassDeclaration(self, identifierIsOptional=False) -> nodes.ClassDeclaration:
        node = self.createNode()

        previousStrict = self.context.strict
        self.context.strict = True
        self.expectKeyword('class')

        if identifierIsOptional and self.lookahead.kind is not JSToken.Identifier:
            id = None
        else:
            id = self.ast.addNode(self.parseVariableIdentifier())
        superClass = None
        if self.matchKeyword('extends'):
            self.nextToken()
            superClass = self.ast.addNode(
                self.isolateCoverGrammar(self.parseLeftHandSideExpressionAllowCall))
        classBody = self.ast.addNode(self.parseClassBody())
        self.context.strict = previousStrict

        return self.finalize(node, nodes.ClassDeclaration(id, superClass, classBody))

    def parseClassExpression(self) -> nodes.ClassExpression:
        node = self.createNode()

        previousStrict = self.context.strict
        self.context.strict = True
        self.expectKeyword('class')
        id = self.ast.addNode(
            self.parseVariableIdentifier()) if self.lookahead.kind is JSToken.Identifier else None
        superClass = None
        if self.matchKeyword('extends'):
            self.nextToken()
            superClass = self.ast.addNode(
                self.isolateCoverGrammar(self.parseLeftHandSideExpressionAllowCall))
        classBody = self.ast.addNode(self.parseClassBody())
        self.context.strict = previousStrict

        return self.finalize(node, nodes.ClassExpression(id, superClass, classBody))

    # https://tc39.github.io/ecma262/#sec-scripts
    # https://tc39.github.io/ecma262/#sec-modules

    def parseModule(self) -> int:
        self.context.strict = True
        self.context.isModule = True
        self.scanner.isModule = True
        node = self.createNode()
        body: list[nodes.Node] = self.parseDirectivePrologues()
        while self.lookahead.kind is not JSToken.EOF:
            body.append(self.parseStatementListItem())
            # print(body[-1])
        return self.ast.addNode(self.finalize(node, nodes.Module(self.ast.addNodes(body))))

    def parseScript(self) -> int:
        node = self.createNode()
        body = self.parseDirectivePrologues()
        while self.lookahead.kind is not JSToken.EOF:
            body.append(self.parseStatementListItem())
        return self.ast.addNode(self.finalize(node, nodes.Script(self.ast.addNodes(body))))

    # https://tc39.github.io/ecma262/#sec-imports

    def parseModuleSpecifier(self) -> nodes.Literal:
        node = self.createNode()

        if self.lookahead.kind is not JSToken.StringLiteral:
            self.throwError(Messages.InvalidModuleSpecifier)

        token = self.nextToken()
        raw = self.getTokenRaw(token)
        return self.finalize(node, nodes.Literal(token.content, raw))

    # import {<foo as bar>} ...
    def parseImportSpecifier(self) -> nodes.ImportSpecifier:
        node = self.createNode()

        if self.lookahead.kind is JSToken.Identifier:
            imported = self.ast.addNode(self.parseVariableIdentifier())
            local = imported
            if self.matchContextualKeyword('as'):
                self.nextToken()
                local = self.ast.addNode(self.parseVariableIdentifier())
        else:
            imported = self.ast.addNode(self.parseIdentifierName())
            local = imported
            if self.matchContextualKeyword('as'):
                self.nextToken()
                local = self.ast.addNode(self.parseVariableIdentifier())
            else:
                self.throwUnexpectedToken(self.nextToken())

        return self.finalize(node, nodes.ImportSpecifier(local, imported))

    # {foo, bar as bas
    def parseNamedImports(self) -> list[nodes.ImportSpecifier]:
        self.expect('{')
        specifiers = []
        while not self.match('}'):
            specifiers.append(self.parseImportSpecifier())
            if not self.match('}'):
                self.expect(',')
        self.expect('}')

        return specifiers

    # import <foo> ...
    def parseImportDefaultSpecifier(self) -> nodes.ImportDefaultSpecifier:
        node = self.createNode()
        local = self.ast.addNode(self.parseIdentifierName())
        return self.finalize(node, nodes.ImportDefaultSpecifier(local))

    # import <* as foo> ...
    def parseImportNamespaceSpecifier(self) -> nodes.ImportNamespaceSpecifier:
        node = self.createNode()

        self.expect('*')
        if not self.matchContextualKeyword('as'):
            self.throwError(Messages.NoAsAfterImportNamespace)
        self.nextToken()
        local = self.ast.addNode(self.parseIdentifierName())

        return self.finalize(node, nodes.ImportNamespaceSpecifier(local))

    def parseImportDeclaration(self) -> nodes.ImportDeclaration:
        if self.context.inFunctionBody:
            self.throwError(Messages.IllegalImportDeclaration)

        node = self.createNode()
        self.expectKeyword('import')

        specifiers = []
        if self.lookahead.kind is JSToken.StringLiteral:
            # import 'foo'
            src = self.ast.addNode(self.parseModuleSpecifier())
        else:
            if self.match('{'):
                # import {bar
                specifiers.extend(self.parseNamedImports())
            elif self.match('*'):
                # import * as foo
                specifiers.append(self.parseImportNamespaceSpecifier())
            elif self.isIdentifierName(self.lookahead) and not self.matchKeyword('default'):
                # import foo
                specifiers.append(self.parseImportDefaultSpecifier())
                if self.match(','):
                    self.nextToken()
                    if self.match('*'):
                        # import foo, * as foo
                        specifiers.append(self.parseImportNamespaceSpecifier())
                    elif self.match('{'):
                        # import foo, {bar
                        specifiers.extend(self.parseNamedImports())
                    else:
                        self.throwUnexpectedToken(self.lookahead)
            else:
                self.throwUnexpectedToken(self.nextToken())

            if not self.matchContextualKeyword('from'):
                message = Messages.UnexpectedToken if self.lookahead.content else Messages.MissingFromClause
                self.throwError(message, self.lookahead.content)
            self.nextToken()
            src = self.ast.addNode(self.parseModuleSpecifier())
        self.consumeSemicolon()

        return self.finalize(node, nodes.ImportDeclaration(self.ast.addNodes(specifiers), src))

    # https://tc39.github.io/ecma262/#sec-exports

    def parseExportSpecifier(self) -> nodes.ExportSpecifier:
        node = self.createNode()

        local = self.ast.addNode(self.parseIdentifierName())
        exported = local
        if self.matchContextualKeyword('as'):
            self.nextToken()
            exported = self.ast.addNode(self.parseIdentifierName())

        return self.finalize(node, nodes.ExportSpecifier(local, exported))

    def parseExportDefaultSpecifier(self) -> nodes.ExportDefaultSpecifier:
        node = self.createNode()
        local = self.ast.addNode(self.parseIdentifierName())
        return self.finalize(node, nodes.ExportDefaultSpecifier(local))

    def parseExportDeclaration(self) \
            -> nodes.ExportDefaultDeclaration | nodes.ExportNamedDeclaration:
        if self.context.inFunctionBody:
            self.throwError(Messages.IllegalExportDeclaration)

        node = self.createNode()
        self.expectKeyword('export')

        if self.matchKeyword('default'):
            # export default ...
            self.nextToken()
            if self.matchKeyword('function'):
                # export default function foo (:
                # export default function (:
                declaration = self.ast.addNode(self.parseFunctionDeclaration(True))
                exportDeclaration = self.finalize(node, nodes.ExportDefaultDeclaration(declaration))
            elif self.matchKeyword('class'):
                # export default class foo {
                declaration = self.ast.addNode(self.parseClassDeclaration(True))
                exportDeclaration = self.finalize(node, nodes.ExportDefaultDeclaration(declaration))
            elif self.matchContextualKeyword('async'):
                # export default async function f (:
                # export default async function (:
                # export default async x => x
                declaration = self.ast.addNode(self.parseFunctionDeclaration(
                    True) if self.matchAsyncFunction() else self.parseAssignmentExpression())
                exportDeclaration = self.finalize(node, nodes.ExportDefaultDeclaration(declaration))
            else:
                if self.matchContextualKeyword('from'):
                    self.throwError(Messages.UnexpectedToken, self.lookahead.content)
                # export default {}
                # export default []
                # export default (1 + 2)
                if self.match('{'):
                    declaration = self.parseObjectInitializer()
                elif self.match('['):
                    declaration = self.parseArrayInitializer()
                else:
                    declaration = self.parseAssignmentExpression()
                self.consumeSemicolon()
                exportDeclaration = self.finalize(node, nodes.ExportDefaultDeclaration(
                    self.ast.addNode(declaration)))

        elif self.match('*'):
            # export * from 'foo'
            self.nextToken()
            if not self.matchContextualKeyword('from'):
                message = Messages.UnexpectedToken if self.lookahead.content else Messages.MissingFromClause
                self.throwError(message, self.lookahead.content)
            self.nextToken()
            src = self.ast.addNode(self.parseModuleSpecifier())
            self.consumeSemicolon()
            exportDeclaration = self.finalize(node, nodes.ExportAllDeclaration(src))

        elif self.lookahead.kind is JSToken.Keyword:
            # export var f = 1
            value = self.lookahead.content
            if value in (
                    'let',
                    'const',
            ):
                declaration = self.parseLexicalDeclaration(Params(inFor=False))
            elif value in (
                    'var',
                    'class',
                    'function',
            ):
                declaration = self.parseStatementListItem()
            else:
                self.throwUnexpectedToken(self.lookahead)
                declaration = None  # Never reached
            exportDeclaration = self.finalize(node,
                                              nodes.ExportNamedDeclaration(
                                                  self.ast.addNode(declaration), [], None))

        elif self.matchAsyncFunction():
            declaration = self.parseFunctionDeclaration()
            exportDeclaration = self.finalize(node,
                                              nodes.ExportNamedDeclaration(
                                                  self.ast.addNode(declaration), [], None))

        else:
            specifiers = []
            source = None
            isExportFromIdentifier = False

            expectSpecifiers = True
            if self.lookahead.kind is JSToken.Identifier:
                specifiers.append(self.parseExportDefaultSpecifier())
                if self.match(','):
                    self.nextToken()
                else:
                    expectSpecifiers = False

            if expectSpecifiers:
                self.expect('{')
                while not self.match('}'):
                    isExportFromIdentifier = isExportFromIdentifier or self.matchKeyword('default')
                    specifiers.append(self.parseExportSpecifier())
                    if not self.match('}'):
                        self.expect(',')
                self.expect('}')

            if self.matchContextualKeyword('from'):
                # export {default} from 'foo'
                # export {foo} from 'foo'
                self.nextToken()
                source = self.ast.addNode(self.parseModuleSpecifier())
                self.consumeSemicolon()
            elif isExportFromIdentifier:
                # export {default}; # missing fromClause
                message = Messages.UnexpectedToken if self.lookahead.content else Messages.MissingFromClause
                self.throwError(message, self.lookahead.content)
            else:
                # export {foo}
                self.consumeSemicolon()
            exportDeclaration = self.finalize(node, nodes.ExportNamedDeclaration(None,
                                                                                 self.ast.addNodes(
                                                                                     specifiers),
                                                                                 source))

        return exportDeclaration
