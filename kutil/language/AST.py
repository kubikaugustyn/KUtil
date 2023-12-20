#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum
from typing import Any, Iterator


class ASTNode:
    type: Enum
    data: Any

    def __init__(self, type: Enum, data: Any):
        self.type = type
        self.data = data

    def __eq__(self, other) -> bool:
        return False

    def __ne__(self, other) -> bool:
        return True


class AST:
    nodes: list[ASTNode]
    root: list[int]  # The tree is linked by the node indices

    def __init__(self):
        self.nodes = []
        self.root = []

    def addNode(self, node: ASTNode) -> int:
        self.nodes.append(node)
        return len(self.nodes) - 1

    def addRootNode(self, nodeI: int):
        self.root.append(nodeI)

    def getNode(self, nodeI: int) -> ASTNode:
        return self.nodes[nodeI]

    def rootNodes(self) -> Iterator[ASTNode]:
        for nodeI in self.root:
            yield self.getNode(nodeI)
