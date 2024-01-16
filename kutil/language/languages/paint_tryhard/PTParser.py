#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Any, Optional

from kutil.language.Error import ParserError

from kutil.language.AST import AST, ASTNode
from kutil.language.Options import CompiledLanguageOptions
from kutil.language.Parser import Parser
from kutil.language.Token import TokenOutput, Token
from kutil.language.languages.paint_tryhard.PTLexer import PTToken, WorkKind


@unique
class PTNode(Enum):
    CONTRACT = "CONTRACT"
    WORK_KIND = "WORK_KIND"
    NAME = "NAME"
    EMPLOYEES = "EMPLOYEES"
    ARGUMENT = "ARGUMENT"
    VARIABLE = "VARIABLE"
    PROOF_OF_WORK = "PROOF_OF_WORK"
    CONTRACT_CODE = "CONTRACT_CODE"
    C_SET_VAR = "C_SET_VAR"
    C_GET_PROOF_OF_WORK = "C_GET_PROOF_OF_WORK"
    C_JOB_METHOD = "C_JOB_METHOD"
    C_JOB_END = "C_JOB_END"


class ContractNode(ASTNode):
    type = PTNode.CONTRACT
    data: list[int]  # List of the contract's nodes

    def __init__(self, subNodes: list[int]):
        super().__init__(self.type, subNodes)


class ContractCodeNode(ASTNode):
    type = PTNode.CONTRACT_CODE
    data: list[int]  # List of the contract's code instructions

    def __init__(self, instructions: list[int]):
        super().__init__(self.type, instructions)


class ContractEmployeesNode(ASTNode):
    type = PTNode.EMPLOYEES
    data: list[str]  # List of the employee names

    def __init__(self, employees: list[str]):
        super().__init__(self.type, employees)


class PTParser(Parser):
    def parseInner(self, tokens: TokenOutput, options: CompiledLanguageOptions) -> AST:
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

        hasWorkKind = False
        hasName = False
        hasCode = False
        hasEmployees = False

        variables: dict[str, Any] = {}  # Includes name of PoW
        employees: list[str] = []  # List of employee names

        def addNode(node: ASTNode) -> int:
            i = ast.addNode(node)
            nodes.append(i)
            return i

        while True:
            token: Token = tokens.nextToken()

            # Contract end
            if token.kind == PTToken.END_CONTRACT:
                if not hasWorkKind or not hasName or not hasCode:
                    raise ParserError(ValueError(f"Bad contract end - not all required tokens were "
                                                 f"provided (work kind, name and code)"))
                break
            # Code is the last thing to be defined
            elif hasCode:
                raise ParserError(ValueError(f"Unexpected token {token} after code definition"))

            # Manage tokens
            if token.kind == PTToken.SET_WORK_KIND:
                if hasWorkKind:
                    raise ParserError(ValueError(f"Bad {token} when work kind is already defined"))
                addNode(ASTNode(PTNode.WORK_KIND, token.content))
                hasWorkKind = True
                hasEmployees = token.content == WorkKind.BOSS or token.content == WorkKind.THE_BOSS
            elif token.kind == PTToken.SET_NAME:
                if hasName:
                    raise ParserError(ValueError(f"Bad {token} when name is already defined"))
                addNode(ASTNode(PTNode.NAME, token.content))
                hasName = True
            elif token.kind == PTToken.SET_ARGUMENT:
                if token.content[0] in variables:
                    raise ParserError(ValueError(f"Bad {token} when argument is already defined"))
                addNode(ASTNode(PTNode.ARGUMENT, token.content))
                variables[token.content[0]] = token.content[1]
            elif token.kind == PTToken.SET_VARIABLE:
                if token.content[0] in variables:
                    raise ParserError(ValueError(f"Bad {token} when variable is already defined"))
                addNode(ASTNode(PTNode.VARIABLE, token.content))
                variables[token.content[0]] = token.content[1]
            elif token.kind == PTToken.SET_PROOF_OF_WORK:
                if token.content[0] in variables:
                    raise ParserError(ValueError(f"Bad {token} with return type already defined"))
                addNode(ASTNode(PTNode.PROOF_OF_WORK, token.content))
                variables[token.content[0]] = token.content[1]
            elif token.kind == PTToken.SET_EMPLOYEE:
                if not hasEmployees:
                    raise ParserError(ValueError(f"Bad {token} when this employee"
                                                 f" cannot have any employees"))
                employees.append(token.content)
            elif token.kind == PTToken.SET_CODE:
                hasCode = True
                codeNode = PTParser.parseContractCode(tokens, ast, variables)
                addNode(codeNode)
            else:
                print(token)
        if hasEmployees:
            addNode(ContractEmployeesNode(employees))
        return ContractNode(nodes)

    @staticmethod
    def parseContractCode(tokens: TokenOutput, ast: AST, variables: dict) -> ContractCodeNode:
        codeNodes: list[int] = []

        def addNode(node: ASTNode) -> int:
            i = ast.addNode(node)
            codeNodes.append(i)
            return i

        while True:
            token = tokens.nextToken()

            if token.kind == PTToken.C_JOB_END:
                break
            elif token.kind == PTToken.C_SET_VAR:
                if token.content[0] not in variables:
                    raise Exception(f"Variable {token.content[0]} is not defined")
                addNode(ASTNode(PTNode.C_SET_VAR, token.content))
            elif token.kind == PTToken.C_JOB_METHOD:
                addNode(ASTNode(PTNode.C_JOB_METHOD, token.content))
            elif token.kind == PTToken.C_GET_PROOF_OF_WORK:
                addNode(ASTNode(PTNode.C_GET_PROOF_OF_WORK, token.content))
            else:
                print(token)

        return ContractCodeNode(codeNodes)
