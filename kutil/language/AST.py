#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum
from typing import Any, Iterator
from kutil.typing_help import FrozenList


class ASTNode:
    type: Enum
    data: Any

    def __init__(self, type: Enum, data: Any):
        self.type = type
        self.data = data

    def reprInfo(self) -> str | None:
        return None

    def __repr__(self):
        selfType = type(self)
        if selfType == ASTNode:  # If this is not a subclass
            return f"<ASTNode {self.type.name} node at {hex(id(self))}>"
            # return f"<kutil.language.AST.ASTNode {self.type.name} node at {hex(id(self))}>"
        reprInfo = self.reprInfo()
        if reprInfo:
            return f"<{selfType.__name__} node ({reprInfo}) at {hex(id(self))}>"
        return f"<{selfType.__name__} node at {hex(id(self))}>"
        # return super().__repr__()


class AST:
    _nodes: list[ASTNode]  # List of nodes
    _containedNodes: set[int]  # Set of node IDs for fast lookup (check if node is present)
    _root: list[int]  # The tree is linked by the node indices

    def __init__(self):
        self._nodes = []
        self._containedNodes = set()
        self._root = []

    def addNode(self, node: ASTNode) -> int:
        if not isinstance(node, ASTNode):
            raise TypeError(f"Bad node type: {type(node)}")

        if id(node) in self._containedNodes:
            return self._nodes.index(node)

        self._nodes.append(node)
        self._containedNodes.add(id(node))
        return len(self._nodes) - 1

    def addNodes(self, nodes: list[ASTNode]) -> list[int]:
        if not isinstance(nodes, list):
            raise TypeError(f"Bad nodes type: {type(nodes)}")
        if not all(map(lambda x: isinstance(x, ASTNode), nodes)):
            raise TypeError(f"Bad node type of one of the nodes")

        if any(map(lambda x: id(x) in self._containedNodes, nodes)):
            # Do it the "good" way if some of the nodes is already present
            return list(map(self.addNode, nodes))

        startI = len(self._nodes)
        endI = startI + len(nodes)
        self._nodes.extend(nodes)
        self._containedNodes.update(map(lambda x: id(x), nodes))
        return list(range(startI, endI))

    def addRootNode(self, nodeI: int):
        if not isinstance(nodeI, int):
            raise TypeError("Node index should be int")
        self._root.append(nodeI)

    def getNode(self, nodeI: int) -> ASTNode:
        if not isinstance(nodeI, int):
            raise TypeError(f"Node index should be int, not {type(nodeI).__name__}")
        return self._nodes[nodeI]

    def getNodes(self, nodeIs: list[int]) -> list[ASTNode]:
        return list(map(self.getNode, nodeIs))

    def rootNodes(self) -> Iterator[ASTNode]:
        for nodeI in self._root:
            yield self.getNode(nodeI)

    def getAllNodes(self) -> FrozenList:
        """
        Returns all nodes in the AST.

        Does not return a mutable list for AST integrity reasons.

        Sadly, FrozenList doesn't support item type annotation.
        """
        nodes: FrozenList = FrozenList(self._nodes)
        nodes.freeze()
        return nodes

    def replaceNode(self, src: ASTNode, target: ASTNode):
        if id(src) not in self._containedNodes:
            raise ValueError("Node to be replaced is not in the AST")
        if id(target) in self._containedNodes:
            raise ValueError("Node to be replaced with is already in the AST")
        self._containedNodes.remove(id(src))
        self._containedNodes.add(id(target))
        self._nodes[self._nodes.index(src)] = target


if __name__ == '__main__':
    # A stress test for checking that the implementation is fast enough
    import time, enum, random


    class Kind(enum.Enum):
        A = enum.auto()
        B = enum.auto()
        C = enum.auto()


    ast = AST()

    sTime = time.time()

    sTimeAST = time.time()

    for i in range(10_000_000):
        node = ASTNode(random.choice(list(Kind)), i)

        ast.addNode(node)

        if i % 100_000 == 0:  # and i > 10_000:
            eTimeAST = time.time()
            print(f"{i} - elapsed time: {eTimeAST - sTimeAST:.2f} seconds")
            sTimeAST = time.time()

    eTime = time.time()
    print(f"Elapsed time: {eTime - sTime:.2f} seconds")

    # On my machine, the indexed times are about .3 seconds and the whole thing took ~30 seconds.
