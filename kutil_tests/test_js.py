#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil.language.languages.javascript import parseScript, nodes
from kutil.language.languages.javascript.JSOptions import JSOptions
from kutil.language.languages.javascript.syntax import JSNode


class TestJavascript(TestCase):
    def test_javascript(self):
        ast, script = parseScript("""
        var a = 8;
        var b = 7 // Comment test
        var c = a + b
        if (c !== 15) throw Error("Bad math")
        """, JSOptions())
        rootNodes = ast.getNodes(script.body)
        self.assertEqual(len(rootNodes), 4)
        # var a = 8;
        self.assertEqual(rootNodes[0].type, JSNode.VariableDeclaration)
        varA = rootNodes[0]
        # Ik, bad, but the typechecker is bad
        assert isinstance(varA, nodes.VariableDeclaration)
        declarator = ast.getNode(varA.declarations[0])
        assert isinstance(declarator, nodes.VariableDeclarator)
        id, init = ast.getNodes([declarator.id, declarator.init])
        assert isinstance(id, nodes.Identifier)
        assert isinstance(init, nodes.Literal)
        self.assertEqual(id.name, "a")
        self.assertEqual(init.value, 8)
        # var b = 7
        self.assertEqual(rootNodes[1].type, JSNode.VariableDeclaration)
        # var c = a + b
        self.assertEqual(rootNodes[2].type, JSNode.VariableDeclaration)
        # if (c !== 15)
        self.assertEqual(rootNodes[3].type, JSNode.IfStatement)
        ifStatement = rootNodes[3]
        assert isinstance(ifStatement, nodes.IfStatement)
        test, consequent = ast.getNodes([ifStatement.test, ifStatement.consequent])
        assert isinstance(test, nodes.BinaryExpression)  # Test
        self.assertEqual(test.operator, "!==")
        a, b = ast.getNodes([test.left, test.right])
        assert isinstance(a, nodes.Identifier)
        assert isinstance(b, nodes.Literal)
        self.assertEqual(a.name, "c")
        self.assertEqual(b.value, 15)
        assert isinstance(consequent, nodes.ThrowStatement)  # if
        self.assertIsNone(ifStatement.alternate)  # else
