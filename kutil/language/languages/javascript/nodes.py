#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import json
from abc import abstractmethod, ABC
from typing import Literal as TypingLiteral, Any, Self

from kutil import NL
from .character import TABULATOR
from .syntax import JSNode
from .JSLexer import RegExp
from kutil.language.AST import ASTNode, AST


class Node(ASTNode):  # A JS Node class
    @abstractmethod
    def clone(self) -> Self:
        raise NotImplementedError(f"{type(self).__name__} cannot be cloned")

    @abstractmethod
    def toJson(self, ast: AST) -> dict:
        raise NotImplementedError(f"{type(self).__name__} cannot be converted to JSON")

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        """
        Converts the node to a string
        :param ast: AST to be used
        :param offset: (optional) the offset the node is placed at
        :param startOffset: (optional) if the offset should be used for the first line
        :return: The string representation of the node
        """
        try:
            return json.dumps(self.toJson(ast))
        except NotImplementedError as e:
            raise ExceptionGroup(f"{type(self).__name__} cannot be converted to string",
                                 [e, RuntimeError("To JSON used, but failed")])


class StaticNode(Node):
    """
    This is a wrapper class for a static node whose value can be determined
    at parse time (right now), e.g. it does not contain any variable getter,
     function call etc.
    """

    def toData(self, ast: AST) -> Any:
        if not self.isStatic(ast):
            raise ValueError(f"{type(self).__name__} static value cannot be determined")
        return self.toDataInner(ast)

    def toDataStr(self, ast: AST) -> str:
        if not self.isStatic(ast):
            raise ValueError(f"{type(self).__name__} static value cannot be determined")
        return self.toDataStrInner(ast)

    def toDataOrString(self, ast: AST, offset: str = "", startOffset: bool = True) -> Any:
        if not self.isStatic(ast):
            return self.toString(ast, offset, startOffset)
        return self.toDataInner(ast)

    @abstractmethod
    def toDataInner(self, ast: AST) -> Any:
        raise NotImplementedError(f"{type(self).__name__} cannot be converted to data")

    @abstractmethod
    def toDataStrInner(self, ast: AST) -> str:
        raise NotImplementedError(f"{type(self).__name__} cannot be converted to data")

    # @abstractmethod - not necessary
    def isStatic(self, ast: AST) -> bool:
        return True


def getAstNode(ast: AST, nodeI: int) -> Node:
    node = ast.getNode(nodeI)
    assert isinstance(node, Node)
    return node


def getAstNodeStrings(ast: AST, nodeIs: list[int], offset: str = "",
                      startOffset: bool = True) -> list[str]:
    return list(map(lambda x: getAstNode(ast, x).toString(ast, offset, startOffset), nodeIs))


class ArrayExpression(StaticNode):
    elements: list

    def __init__(self, elements):
        super().__init__(JSNode.ArrayExpression, elements)
        self.elements = elements

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        if len(self.elements) == 0:
            return offset + "[]" if startOffset else "[]"

        if startOffset:
            result: str = f"{offset}[{NL}"
        else:
            result: str = "[" + NL

        for i, elemI in enumerate(self.elements):
            elem = ast.getNode(elemI)
            assert isinstance(elem, Node)

            result += elem.toString(ast, offset + TABULATOR, True)

            if i != len(self.elements) - 1:
                result += ","
            result += NL
        result += f"{offset}]"
        return result

    def isStatic(self, ast: AST) -> bool:
        for elemI in self.elements:
            elem = getAstNode(ast, elemI)
            if (not isinstance(elem, StaticNode) or
                    not elem.isStatic(ast)):
                return False
        return True

    def toDataInner(self, ast: AST) -> list[Any]:
        result: list[Any] = []
        for elemI in self.elements:
            elem = getAstNode(ast, elemI)
            assert isinstance(elem, StaticNode)
            result.append(elem.toData(ast))
        return result


class ArrayPattern(ArrayExpression):
    def __init__(self, elements):
        super().__init__(elements)
        self.type = JSNode.ArrayPattern


class ArrowFunctionExpression(Node):
    def __init__(self, params, body, expression):
        super().__init__(JSNode.ArrowFunctionExpression, (params, body, expression))
        self.generator = False
        self.isAsync = False
        self.params = params
        self.body = body
        self.expression = expression

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        paramsMap = map(lambda x: getAstNode(ast, x).toString(ast, offset + TABULATOR, False),
                        self.params)
        params: str = ', '.join(paramsMap)
        body: str = getAstNode(ast, self.body).toString(ast, offset + TABULATOR,
                                                        False) if self.body else ""

        start = f"{offset if startOffset else ''}{'async ' if self.isAsync else ''}({params}) => "
        return start + body


class AssignmentExpression(Node):
    def __init__(self, operator, left, right):
        super().__init__(JSNode.AssignmentExpression, (operator, left, right))
        self.operator = operator
        self.left = left
        self.right = right

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        left = getAstNode(ast, self.left).toString(ast, offset + TABULATOR, False)
        right = getAstNode(ast, self.right).toString(ast, offset + TABULATOR, False)
        return f"{offset if startOffset else ''}{left} {self.operator} {right}"


class AssignmentPattern(Node):
    def __init__(self, left, right):
        super().__init__(JSNode.AssignmentPattern, (left, right))
        self.left = left
        self.right = right


class AsyncArrowFunctionExpression(ArrowFunctionExpression):
    def __init__(self, params, body, expression):
        super().__init__(params, body, expression)
        self.isAsync = True


class FunctionDeclaration(Node):
    def __init__(self, id, params, body, generator: bool):
        super().__init__(JSNode.FunctionDeclaration, (id, params, body, generator))
        self.expression = False
        self.isAsync = False
        self.id = id
        self.params = params
        self.body = body
        self.generator = generator

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        name: str = getAstNode(ast, self.id).toString(ast, offset + TABULATOR,
                                                      False) if self.id else ""
        paramsMap = map(lambda x: getAstNode(ast, x).toString(ast, offset + TABULATOR, False),
                        self.params)
        params: str = ', '.join(paramsMap)
        body: str = getAstNode(ast, self.body).toString(ast, offset, False) if self.body else ""
        startLine = f"{offset if startOffset else ''}{'async ' if self.isAsync else ''}function {name}({params}) "
        return startLine + body


class FunctionExpression(FunctionDeclaration):
    def __init__(self, id, params, body, generator: bool):
        if len(params) > 0 and not isinstance(params[0], int):
            raise NotImplementedError
        super().__init__(id, params, body, generator)
        self.type = JSNode.FunctionExpression  # Overwrite it


class AsyncFunctionDeclaration(FunctionDeclaration):
    def __init__(self, id, params, body):
        super().__init__(id, params, body, False)
        self.isAsync = True


class AsyncFunctionExpression(AsyncFunctionDeclaration):
    def __init__(self, id, params, body):
        super().__init__(id, params, body)
        self.type = JSNode.FunctionExpression


class AwaitExpression(Node):
    def __init__(self, argument):
        super().__init__(JSNode.AwaitExpression, argument)
        self.argument = argument

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        argument = getAstNode(ast, self.argument).toString(ast, offset + TABULATOR, False)
        return f"{offset if startOffset else ''}await {argument}"


class BinaryExpression(Node):
    operator: str
    left: int
    right: int

    def __init__(self, operator, left, right):
        kind = JSNode.LogicalExpression if operator in ('||', '&&') else JSNode.BinaryExpression
        super().__init__(kind, (left, right))
        self.operator = operator
        self.left = left
        self.right = right

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        left: str = getAstNode(ast, self.left).toString(ast, offset, False)
        right: str = getAstNode(ast, self.right).toString(ast, offset, False)
        # TODO Surrounding with () is optional
        return f"{offset if startOffset else ''}({left}) {self.operator} ({right})"


class BlockStatement(Node):
    body: list[int]

    def __init__(self, body):
        super().__init__(JSNode.BlockStatement, body)
        self.body = body

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        # assert startOffset, "Cannot have a block statement on one line"
        content = offset if startOffset else ""
        content += "{" + NL
        for child in ast.getNodes(self.body):
            assert isinstance(child, Node)
            content += child.toString(ast, offset + TABULATOR, True) + NL
        content += f"{offset}}}"

        return content


class BreakStatement(Node):
    def __init__(self, label):
        super().__init__(JSNode.BreakStatement, label)
        self.label = label

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        if self.label is None:
            return f"{offset if startOffset else ''}break"
        labelStr = getAstNode(ast, self.label).toString(ast, offset + TABULATOR, True)
        return f"{offset if startOffset else ''}break {labelStr}"


class CallExpression(Node):
    callee: int
    arguments: list[int]

    def __init__(self, callee, args):
        super().__init__(JSNode.CallExpression, (callee, args))
        self.callee = callee
        self.arguments = args

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        content = offset if startOffset else ""

        calleeNode = getAstNode(ast, self.callee)
        surroundCallee = not isinstance(calleeNode, (StaticMemberExpression, Identifier))

        if surroundCallee:
            content += "("
        content += calleeNode.toString(ast, offset, False)
        if surroundCallee:
            content += ")"
        content += "("
        for i, argI in enumerate(self.arguments):
            arg = getAstNode(ast, argI)

            content += arg.toString(ast, offset, False)

            if i < len(self.arguments) - 1:
                content += ", "
        content += ")"

        return content


class CatchClause(Node):
    def __init__(self, param, body):
        super().__init__(JSNode.CatchClause, (param, body))
        self.param = param
        self.body = body

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        paramStr = getAstNode(ast, self.param).toString(ast, offset, False) if self.param else ""
        bodyStr = getAstNode(ast, self.body).toString(ast, offset, False)
        return f"{offset if startOffset else ''}catch ({paramStr}) {bodyStr}"


class ClassBody(Node):
    def __init__(self, body):
        super().__init__(JSNode.ClassBody, body)
        self.body = body


class ClassDeclaration(Node):
    def __init__(self, id, superClass, body):
        super().__init__(JSNode.ClassDeclaration, (id, superClass, body))
        self.id = id
        self.superClass = superClass
        self.body = body


class ClassExpression(Node):
    def __init__(self, id, superClass, body):
        super().__init__(JSNode.ClassExpression, (id, superClass, body))
        self.id = id
        self.superClass = superClass
        self.body = body


class ComputedMemberExpression(Node):
    # object[property]
    def __init__(self, object, property):
        super().__init__(JSNode.MemberExpression, (object, property))
        self.computed = True
        self.object = object
        self.property = property

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        assert self.computed
        objectStr = getAstNode(ast, self.object).toString(ast, offset, False)
        propertyStr = getAstNode(ast, self.property).toString(ast, offset, False)
        return f"{offset if startOffset else ''}{objectStr}[{propertyStr}]"


class ConditionalExpression(Node):
    # test ? consequent : alternate
    test: int
    consequent: int
    alternate: int

    def __init__(self, test, consequent, alternate):
        super().__init__(JSNode.ConditionalExpression, (test, consequent, alternate))
        self.test = test
        self.consequent = consequent
        self.alternate = alternate

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        testStr = getAstNode(ast, self.test).toString(ast, offset, False)
        consequentStr = getAstNode(ast, self.consequent).toString(ast, offset, False)
        alternateStr = getAstNode(ast, self.alternate).toString(ast, offset, False)
        return f"{offset if startOffset else ''}{testStr} ? {consequentStr} : {alternateStr}"


class ContinueStatement(Node):
    def __init__(self, label):
        super().__init__(JSNode.ContinueStatement, label)
        self.label = label


class DebuggerStatement(Node):
    def __init__(self):
        super().__init__(JSNode.DebuggerStatement, None)


class Directive(Node):
    def __init__(self, expression, directive):
        super().__init__(JSNode.ExpressionStatement, (expression, directive))
        self.expression = expression
        self.directive = directive


class DoWhileStatement(Node):
    def __init__(self, body, test):
        super().__init__(JSNode.DoWhileStatement, (body, test))
        self.body = body
        self.test = test


class EmptyStatement(Node):
    def __init__(self):
        super().__init__(JSNode.EmptyStatement, None)


class ExportAllDeclaration(Node):
    def __init__(self, source):
        super().__init__(JSNode.ExportAllDeclaration, source)
        self.source = source


class ExportDefaultDeclaration(Node):
    def __init__(self, declaration):
        super().__init__(JSNode.ExportDefaultDeclaration, declaration)
        self.declaration = declaration


class ExportNamedDeclaration(Node):
    def __init__(self, declaration, specifiers, source):
        super().__init__(JSNode.ExportNamedDeclaration, (declaration, specifiers, source))
        self.declaration = declaration
        self.specifiers = specifiers
        self.source = source


class ExportSpecifier(Node):
    def __init__(self, local, exported):
        super().__init__(JSNode.ExportSpecifier, (local, exported))
        self.exported = exported
        self.local = local


class ExportDefaultSpecifier(Node):
    def __init__(self, local):
        super().__init__(JSNode.ExportDefaultSpecifier, local)
        self.local = local


class ExpressionStatement(Node):
    expression: int

    def __init__(self, expression):
        super().__init__(JSNode.ExpressionStatement, expression)
        self.expression = expression

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        expr = getAstNode(ast, self.expression)
        return expr.toString(ast, offset, startOffset)


class ForInStatement(Node):
    def __init__(self, left, right, body):
        super().__init__(JSNode.ForInStatement, (left, right, body))
        self.each = False
        self.left = left
        self.right = right
        self.body = body

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        leftStr = getAstNode(ast, self.left).toString(ast, offset, False)
        rightStr = getAstNode(ast, self.right).toString(ast, offset, False)
        bodyStr = getAstNode(ast, self.body).toString(ast, offset, False)
        return f"{offset if startOffset else ''}for ({leftStr} in {rightStr}) {bodyStr}"


class ForOfStatement(Node):
    def __init__(self, left, right, body):
        super().__init__(JSNode.ForOfStatement, (left, right, body))
        self.left = left
        self.right = right
        self.body = body

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        leftStr = getAstNode(ast, self.left).toString(ast, offset, False)
        rightStr = getAstNode(ast, self.right).toString(ast, offset, False)
        bodyStr = getAstNode(ast, self.body).toString(ast, offset, False)
        return f"{offset if startOffset else ''}for ({leftStr} of {rightStr}) {bodyStr}"


class ForStatement(Node):
    def __init__(self, init, test, update, body):
        super().__init__(JSNode.ForStatement, (init, test, update, body))
        self.init = init
        self.test = test
        self.update = update
        self.body = body

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        initStr = getAstNode(ast, self.init).toString(ast, offset, False)
        testStr = getAstNode(ast, self.test).toString(ast, offset, False)
        updateStr = getAstNode(ast, self.update).toString(ast, offset, False)
        bodyStr = getAstNode(ast, self.body).toString(ast, offset + TABULATOR, False)
        return f"{offset if startOffset else ''}for ({initStr}; {testStr}; {updateStr}) {bodyStr}"


class Identifier(Node):
    name: str

    def __init__(self, name):
        super().__init__(JSNode.Identifier, name)
        self.name = name

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        return (offset if startOffset else '') + self.name

    def reprInfo(self) -> str | None:
        return self.name

    def clone(self) -> Self:
        return Identifier(name=self.name)


class IfStatement(Node):
    def __init__(self, test, consequent, alternate):
        super().__init__(JSNode.IfStatement, (test, consequent, alternate))
        self.test = test
        self.consequent = consequent
        self.alternate = alternate

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        testStr = getAstNode(ast, self.test).toString(ast, offset, False)
        consequentStr = getAstNode(ast, self.consequent).toString(ast, offset, False)
        alternateStr = getAstNode(ast, self.alternate).toString(ast, offset,
                                                                False) if self.alternate else ""
        if not consequentStr.endswith(NL):
            consequentStr += NL
            consequentStr += offset
        if not alternateStr:
            return f"{offset if startOffset else ''}if ({testStr}) {consequentStr}"
        return f"{offset if startOffset else ''}if ({testStr}) {consequentStr}else {alternateStr}"


class Import(Node):
    def __init__(self):
        super().__init__(JSNode.Import, None)


class ImportDeclaration(Node):
    def __init__(self, specifiers, source):
        super().__init__(JSNode.ImportDeclaration, (specifiers, source))
        self.specifiers = specifiers
        self.source = source

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        specifiers = ", ".join(
            map(lambda x: getAstNode(ast, x).toString(ast, offset + TABULATOR, False),
                self.specifiers))
        source = getAstNode(ast, self.source).toString(ast, offset, False)
        return f"{offset if startOffset else ''}import {{{specifiers}}} from {source}"


class ImportDefaultSpecifier(Node):
    def __init__(self, local):
        super().__init__(JSNode.ImportDefaultSpecifier, local)
        self.local = local


class ImportNamespaceSpecifier(Node):
    def __init__(self, local):
        super().__init__(JSNode.ImportNamespaceSpecifier, local)
        self.local = local


class ImportSpecifier(Node):
    local: int
    imported: int

    def __init__(self, local, imported):
        super().__init__(JSNode.ImportSpecifier, (local, imported))
        self.local = local
        self.imported = imported

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        local = getAstNode(ast, self.local).toString(ast, offset, False)
        imported = getAstNode(ast, self.imported).toString(ast, offset, False)
        return f"{offset if startOffset else ''}{imported} as {local}"


class LabeledStatement(Node):
    def __init__(self, label, body):
        super().__init__(JSNode.LabeledStatement, (label, body))
        self.label = label
        self.body = body


class Literal(StaticNode):
    value: str | int | float | bool
    raw: str

    def __init__(self, value, raw):
        super().__init__(JSNode.Literal, (value, raw))
        self.value = value
        self.raw = raw

    def toDataInner(self, ast: AST) -> Any:
        return self.value

    def toDataStrInner(self, ast: AST) -> str:
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        return str(self.value)

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        return (offset if startOffset else '') + self.raw


class MetaProperty(Node):
    def __init__(self, meta, property):
        super().__init__(JSNode.MetaProperty, (meta, property))
        self.meta = meta
        self.property = property


class MethodDefinition(Node):
    def __init__(self, key, computed, value, kind, isStatic):
        super().__init__(JSNode.MethodDefinition, (key, computed, value, kind, isStatic))
        self.key = key
        self.computed = computed
        self.value = value
        self.kind = kind
        self.static = isStatic


class FieldDefinition(Node):
    def __init__(self, key, computed, value, kind, isStatic):
        super().__init__(JSNode.FieldDefinition, (key, computed, value, kind, isStatic))
        self.key = key
        self.computed = computed
        self.value = value
        self.kind = kind
        self.static = isStatic


class Module(Node):
    def __init__(self, body: list[int]):
        super().__init__(JSNode.Program, body)
        self.sourceType = 'module'
        self.body = body


class NewExpression(Node):
    def __init__(self, callee, args):
        super().__init__(JSNode.NewExpression, (callee, args))
        self.callee = callee
        self.arguments = args

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        callee: str = getAstNode(ast, self.callee).toString(ast, offset + TABULATOR,
                                                            False) if self.callee else ""
        paramsMap = map(lambda x: getAstNode(ast, x).toString(ast, offset + TABULATOR, False),
                        self.arguments)
        params: str = ', '.join(paramsMap)
        return f"{offset if startOffset else ''}new {callee}({params}) "


class ObjectExpression(StaticNode):
    properties: list[int]

    def __init__(self, properties: list[int]):
        super().__init__(JSNode.ObjectExpression, properties)
        self.properties = properties

    def toJson(self, ast: AST) -> dict:
        result: dict[str, str] = {}

        for propI in self.properties:
            prop = ast.getNode(propI)

            key, value = self._getPropertyKeyValue(prop, ast)

            result[key.toString(ast)] = value.toString(ast)

        return result

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        if len(self.properties) == 0:
            return offset + "{}" if startOffset else "{}"

        if startOffset:
            result: str = f"{offset}{{{NL}"
        else:
            result: str = "{" + NL

        for i, propI in enumerate(self.properties):
            prop = getAstNode(ast, propI)

            assert isinstance(prop, (Property, SpreadElement))

            result += prop.toString(ast, offset + TABULATOR, True)

            if i != len(self.properties) - 1:
                result += ","
            result += NL
        result += f"{offset}}}"
        return result

    def items(self, ast: AST):
        for propI in self.properties:
            prop = ast.getNode(propI)

            key, value = self._getPropertyKeyValue(prop, ast)
            yield key, value

    @staticmethod
    def _getPropertyKeyValue(prop: ASTNode, ast: AST) -> tuple[Node, Node]:
        assert isinstance(prop, Property)
        return prop.getKeyValue(ast)

    def getByKey(self, keyStr: str, ast: AST) -> Node:
        for propI in self.properties:
            prop = ast.getNode(propI)
            key, value = self._getPropertyKeyValue(prop, ast)
            if key.toString(ast) == keyStr:
                return value
        raise KeyError(f"Key {keyStr} not found")

    def isStatic(self, ast: AST) -> bool:
        for propI in self.properties:
            prop = getAstNode(ast, propI)
            if not isinstance(prop, StaticNode) or not prop.isStatic(ast):
                return False
        return True

    def toDataInner(self, ast: AST) -> dict[Any, Any]:
        data: dict[Any, Any] = {}
        for propI in self.properties:
            prop = getAstNode(ast, propI)
            assert isinstance(prop, Property)
            key, value = prop.toData(ast)
            data[key] = value
        return data


class ObjectPattern(ObjectExpression):
    def __init__(self, properties):
        super().__init__(properties)
        self.type = JSNode.ObjectPattern


class Property(StaticNode):
    key: int
    computed: bool
    value: int | None
    kind: TypingLiteral["init", "get", "set"]
    method: int | None
    shorthand: int | None

    def __init__(self, kind, key, computed, value, method, shorthand):
        super().__init__(JSNode.Property, (kind, key, computed, value, method, shorthand))
        self.key = key
        self.computed = computed
        self.value = value
        self.kind = kind
        self.method = method
        self.shorthand = shorthand

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        keyNode, valueNode = self.getKeyValue(ast)
        key = keyNode.toString(ast, offset, startOffset)
        value = valueNode.toString(ast, offset, False)

        if self.computed:
            key = f"[{key}]"

        if self.kind != "init":
            key = f"{self.kind} {key}"
            raise NotImplementedError

        if key.strip() == value.strip():
            return key
        return f"{key}: {value}"

    def getKeyValue(self, ast: AST) -> tuple[Node, Node]:
        key = getAstNode(ast, self.key)
        value = getAstNode(ast, self.value)

        return key, value

    def isStatic(self, ast: AST) -> bool:
        key, value = self.getKeyValue(ast)
        return (
                (
                        (isinstance(key, StaticNode) and key.isStatic(ast)) or
                        isinstance(key, Identifier)
                ) and
                isinstance(value, StaticNode) and
                value.isStatic(ast))

    def toDataInner(self, ast: AST) -> tuple[Any, Any]:
        key, value = self.getKeyValue(ast)
        assert isinstance(key, (StaticNode, Identifier))
        assert isinstance(value, StaticNode)
        if isinstance(key, Identifier):
            return key.name, value.toData(ast)
        return key.toData(ast), value.toData(ast)


class RegexLiteral(Node):
    def __init__(self, value, raw, pattern, flags):
        super().__init__(JSNode.Literal, (value, pattern, flags))
        self.value = value
        self.raw = raw
        self.regex = RegExp(
            pattern=pattern,
            flags=flags,
        )

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        return f"{offset if startOffset else ''}{self.raw}"


class RestElement(Node):
    def __init__(self, argument):
        super().__init__(JSNode.RestElement, argument)
        self.argument = argument

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        argument = getAstNode(ast, self.argument).toString(ast, offset + TABULATOR, False)
        return f"{offset if startOffset else ''}...{argument}"


class ReturnStatement(Node):
    argument: int

    def __init__(self, argument):
        super().__init__(JSNode.ReturnStatement, argument)
        self.argument = argument

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        if self.argument is None:
            return f"{offset if startOffset else ''}return"
        argument: str = getAstNode(ast, self.argument).toString(ast, offset, False)
        return f"{offset if startOffset else ''}return {argument}"


class Script(Node):
    def __init__(self, body: list[int]):
        super().__init__(JSNode.Program, body)
        self.sourceType = 'script'
        self.body = body


class SequenceExpression(Node):
    def __init__(self, expressions):
        super().__init__(JSNode.SequenceExpression, expressions)
        self.expressions = expressions

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        expressionStrings = getAstNodeStrings(ast, self.expressions, offset, False)
        if len(expressionStrings) == 1:
            return f"{offset if startOffset else ''}{expressionStrings[0]}"
        return f"{offset if startOffset else ''}({', '.join(expressionStrings)})"


class SpreadElement(Node):
    def __init__(self, argument):
        super().__init__(JSNode.SpreadElement, argument)
        self.argument = argument

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        # return RestElement.toString(self, ast, offset, startOffset)
        argument = getAstNode(ast, self.argument).toString(ast, offset + TABULATOR, False)
        return f"{offset if startOffset else ''}...{argument}"


class StaticMemberExpression(Node):
    computed: bool
    object: int
    property: int
    optionalChain: bool

    def __init__(self, object, property, optionalChain: bool):
        super().__init__(JSNode.MemberExpression, (object, property, optionalChain))
        self.computed = False
        self.object = object
        self.property = property
        self.optionalChain = optionalChain

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        assert not self.computed
        obj: str = getAstNode(ast, self.object).toString(ast, offset, False)
        prop: str = getAstNode(ast, self.property).toString(ast, offset, False)
        return f"{offset if startOffset else ''}{obj}{'?.' if self.optionalChain else '.'}{prop}"


class Super(Node):
    def __init__(self):
        super().__init__(JSNode.Super, None)


class SwitchCase(Node):
    def __init__(self, test, consequent):
        super().__init__(JSNode.SwitchCase, (test, consequent))
        self.test = test
        self.consequent = consequent

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        consequentStrs = NL.join(
            map(lambda x: getAstNode(ast, x).toString(ast, offset + TABULATOR, True),
                self.consequent))
        if self.test:
            testStr = getAstNode(ast, self.test).toString(ast, offset, False) if self.test else None
            return f"{offset if startOffset else ''}case {testStr}:{NL}{consequentStrs}"
        return f"{offset if startOffset else ''}default:{NL}{consequentStrs}"


class SwitchStatement(Node):
    def __init__(self, discriminant, cases):
        super().__init__(JSNode.SwitchStatement, (discriminant, cases))
        self.discriminant = discriminant
        self.cases = cases

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        discriminantStr = getAstNode(ast, self.discriminant).toString(ast, offset, False)
        caseStrs = NL.join(
            map(lambda x: getAstNode(ast, x).toString(ast, offset + TABULATOR, True), self.cases))
        return f"{offset if startOffset else ''}switch ({discriminantStr}) {{{NL}{caseStrs}{NL}{offset}}}"


class TaggedTemplateExpression(Node):
    def __init__(self, tag, quasi):
        super().__init__(JSNode.TaggedTemplateExpression, (tag, quasi))
        self.tag = tag
        self.quasi = quasi


class TemplateElement(Node):
    class Value:
        def __init__(self, raw, cooked):
            self.raw = raw
            self.cooked = cooked

    def __init__(self, raw, cooked, tail):
        self.value = TemplateElement.Value(raw, cooked)
        super().__init__(JSNode.TemplateElement, (self.value, tail))
        self.tail = tail

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        return self.value.raw


class TemplateLiteral(Node):
    # `Quasi ${expression} quasi ${expression} quasi`
    quasis: list[int]  # TemplateElement(s)
    expressions: list[int]  # Any node(s)

    def __init__(self, quasis, expressions):
        super().__init__(JSNode.TemplateLiteral, (quasis, expressions))
        self.quasis = quasis
        self.expressions = expressions

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        quasiStrs = getAstNodeStrings(ast, self.quasis, offset, False)
        expressionStrs = getAstNodeStrings(ast, self.expressions, offset, False)
        result = f"{offset if startOffset else ''}`{quasiStrs[0]}"
        for expr, quasi in zip(expressionStrs, quasiStrs[1:]):
            result += f"${{{expr}}}{quasi}"
        result += "`"
        return result


class ThisExpression(Node):
    def __init__(self):
        super().__init__(JSNode.ThisExpression, None)

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        return f"{offset if startOffset else ''}this"


class ThrowStatement(Node):
    def __init__(self, argument):
        super().__init__(JSNode.ThrowStatement, argument)
        self.argument = argument

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        argumentStr = getAstNode(ast, self.argument).toString(ast, offset, False)
        return f"{offset if startOffset else ''}{argumentStr}"


class TryStatement(Node):
    def __init__(self, block, handler, finalizer):
        super().__init__(JSNode.TryStatement, (block, handler, finalizer))
        self.block = block
        self.handler = handler
        self.finalizer = finalizer

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        blockStr = getAstNode(ast, self.block).toString(ast, offset, False)
        handlerStr = getAstNode(ast, self.handler).toString(ast, offset,
                                                            False) if self.handler else None
        finalizerStr = getAstNode(ast, self.finalizer).toString(ast, offset,
                                                                False) if self.finalizer else None
        return f"{offset if startOffset else ''}try {blockStr}{f" {handlerStr}" if handlerStr else ''}{f" finally {finalizerStr}" if finalizerStr else ''}"


class UnaryExpression(StaticNode):
    prefix: bool
    operator: str
    argument: int

    def __init__(self, operator, argument):
        super().__init__(JSNode.UnaryExpression, (operator, argument))
        self.prefix = True
        self.operator = operator
        self.argument = argument

    def toDataInner(self, ast: AST) -> Any:
        assert self.prefix

        valueNode = getAstNode(ast, self.argument)
        assert isinstance(valueNode, StaticNode)
        value = valueNode.toData(ast)
        if self.operator == "!":
            return not value
        elif self.operator == "-":
            if not isinstance(value, (int, float)):
                raise ValueError(
                    "Unary operator negate failed: bad value type " + type(value).__name__)
            return -value
        else:
            raise NotImplementedError("Unknown UnaryExpression operator: " + self.operator)

    def isStatic(self, ast: AST) -> bool:
        arg = getAstNode(ast, self.argument)
        if not isinstance(arg, StaticNode):
            return False
        return arg.isStatic(ast)

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        assert self.prefix
        arg: str = getAstNode(ast, self.argument).toString(ast, offset + TABULATOR, False)

        if self.operator == "!":
            # Code quality
            if arg == "0":  # !0 = true
                return "true"
            elif arg == "1":  # !1 = false
                return "false"
        elif self.operator == "void" and arg == "0":
            # void 0 = undefined
            return "undefined"

        requireSpace = self.operator in {'void'}  # TODO find others that need it

        return f"{offset if startOffset else ''}{self.operator}{' ' if requireSpace else ''}{arg}"


class UpdateExpression(Node):
    operator: str
    argument: int
    prefix: bool

    def __init__(self, operator, argument, prefix):
        super().__init__(JSNode.UpdateExpression, (operator, argument, prefix))
        self.operator = operator
        self.argument = argument
        self.prefix = prefix

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        argumentStr = getAstNode(ast, self.argument).toString(ast, offset, False)
        return f"{offset if startOffset else ''}{self.operator if self.prefix else ''}{argumentStr}{self.operator if not self.prefix else ''}"


class VariableDeclaration(Node):
    declarations: list[int]
    kind: str

    def __init__(self, declarations, kind):
        super().__init__(JSNode.VariableDeclaration, (declarations, kind))
        self.declarations = declarations
        self.kind = kind

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        content = offset if startOffset else ""
        content += self.kind + " "

        for i, declaration in enumerate(ast.getNodes(self.declarations)):
            assert isinstance(declaration, VariableDeclarator)

            content += declaration.toString(ast, offset + TABULATOR, i > 0)

            if i < len(self.declarations) - 1:
                content += "," + NL
            else:
                content += NL

        return content


class VariableDeclarator(Node):
    id: int
    init: int | None

    def __init__(self, id, init):
        super().__init__(JSNode.VariableDeclarator, (id, init))
        self.id = id
        self.init = init

    def toString(self, ast: AST, offset: str = "", startOffset: bool = True) -> str:
        content = offset if startOffset else ""
        content += getAstNode(ast, self.id).toString(ast, offset, False)
        if self.init:
            content += " = "
            content += getAstNode(ast, self.init).toString(ast, offset, False)
        return content


class WhileStatement(Node):
    def __init__(self, test, body):
        super().__init__(JSNode.WhileStatement, (test, body))
        self.test = test
        self.body = body


class WithStatement(Node):
    def __init__(self, object, body):
        super().__init__(JSNode.WithStatement, (object, body))
        self.object = object
        self.body = body


class YieldExpression(Node):
    def __init__(self, argument, delegate):
        super().__init__(JSNode.YieldExpression, (argument, delegate))
        self.argument = argument
        self.delegate = delegate


class ArrowParameterPlaceHolder(Node):
    def __init__(self, params):
        super().__init__(JSNode.ArrowParameterPlaceHolder, params)
        self.params = params
        self.isAsync = False

    def reprInfo(self) -> str:
        return "not async"


class AsyncArrowParameterPlaceHolder(Node):
    def __init__(self, params):
        super().__init__(JSNode.ArrowParameterPlaceHolder, params)
        self.params = params
        self.isAsync = True

    def reprInfo(self) -> str:
        return "async"


class BlockComment(Node):
    def __init__(self, value):
        super().__init__(JSNode.BlockComment, value)
        self.value = value


class LineComment(Node):
    def __init__(self, value):
        super().__init__(JSNode.LineComment, value)
        self.value = value
