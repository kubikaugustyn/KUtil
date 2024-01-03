#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum

from kutil.language.Error import ParserError

from kutil.language.AST import AST, ASTNode
from kutil.language.Parser import Parser
from kutil.language.Token import TokenOutput
from kutil.language.languages.paint_tryhard.PTLexer import PTToken


class PTNode(Enum):
    CONTRACT = "CONTRACT"
    WORK_KIND = "WORK_KIND"
    NAME = "NAME"
    ARGUMENT = "ARGUMENT"
    VARIABLE = "VARIABLE"
    PROOF_OF_WORK = "PROOF_OF_WORK"
    C_SET_VAR = "C_SET_VAR"
    C_SET_PROOF_OF_WORK = "C_SET_PROOF_OF_WORK"
    C_JOB_METHOD = "C_JOB_METHOD"
    C_JOB_END = "C_JOB_END"


class ContractNode(ASTNode):
    type = PTNode.CONTRACT
    data: list[int]  # List of the contract's nodes

    def __init__(self, subNodes: list[int]):
        super().__init__(self.type, subNodes)


class PTParser(Parser):
    def parseInner(self, tokens: TokenOutput) -> AST:
        ast: AST = AST()
        # for token in tokens:
        #     print(token)
        while True:
            token = tokens.nextTokenDef()
            if token is None:
                break
            if token.kind != PTToken.START_CONTRACT:
                raise ParserError(ValueError(f"Bad token {token} when"
                                             f" {PTToken.START_CONTRACT} was expected"))
            contract: ContractNode = self.parseContract(tokens, ast)
            ast.addRootNode(ast.addNode(contract))
        return ast

    @staticmethod
    def parseContract(tokens: TokenOutput, ast: AST) -> ContractNode:
        nodes: list[int] = []
        while True:
            token = tokens.nextToken()
            if token.kind == PTToken.END_CONTRACT:
                break
            # TODO Continue here
        return ContractNode(nodes)
