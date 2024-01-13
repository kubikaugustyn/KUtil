#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from typing import Iterator, Optional
from colorama import Fore, Style
from kutil.language.Language import GenericLanguage

from kutil.buffer import TextOutput, BidirectionalByteArray

from kutil.language import InterpretedLanguage, Lexer, Parser, Interpreter, InterpreterExitCode, \
    InterpreterError
from kutil.language.AST import AST, ASTNode
from kutil.language.Token import TokenOutput, Token

@unique
class BFToken(Enum):  # Serves both as the token kind and a thing for the lexer
    INC_PTR = ">"  # Move the pointer to the right
    DEC_PTR = "<"  # Move the pointer to the left
    INC_DAT = "+"  # Increment the value under the pointer
    DEC_DAT = "-"  # Decrement the value under the pointer
    OUT_DAT = "."  # Print the value under the pointer as an ASCII value
    ACC_DAT = ","  # Accept one byte and set it as the value under the pointer
    LOOP_START = "["  # See the wiki https://en.wikipedia.org/wiki/Brainfuck#Language_design
    LOOP_END = "]"


class BFLexer(Lexer):
    def tokenizeInner(self, inputCode: str, output: TokenOutput) -> Iterator[Token]:
        for char in inputCode:
            try:
                tokKind: BFToken = BFToken(char)
            except ValueError:
                continue  # Any other character doesn't count
            yield Token(tokKind, char)

@unique
class BFNode(Enum):
    CONTROL = "control"
    LOOP = "loop"


class ControlNode(ASTNode):
    type = BFNode.CONTROL
    data: str

    def __init__(self, val: str):
        super().__init__(self.type, val)


class LoopNode(ASTNode):
    type = BFNode.LOOP
    data: list[int]

    def __init__(self, subNodes: list[int]):
        super().__init__(self.type, subNodes)


class BFParser(Parser):
    def parseInner(self, tokens: TokenOutput) -> AST:
        ast: AST = AST()
        rootNodes: list[int] = self.parseLoop(tokens, ast, True).data
        for nodeI in rootNodes:
            ast.addRootNode(nodeI)
        return ast

    def parseLoop(self, tokens: TokenOutput, ast: AST, root: bool) -> LoopNode:
        """
        Parses a brainfuck loop. If root is set to True, the statement being parsed isn't a loop, but the whole program.
        :param tokens: The token source
        :param ast: The abstract syntax tree to add nodes to
        :param root: Whether the loop is the whole program or a loop
        :return:
        """
        content: list[int] = []
        while True:
            token: Token = tokens.nextTokenDef(None)
            if token is None and root:
                break
            node: ASTNode
            if token.kind == BFToken.LOOP_START:
                node = self.parseLoop(tokens, ast, False)
            elif token.kind == BFToken.LOOP_END:
                break
            else:
                node = ControlNode(token.content)
            content.append(ast.addNode(node))
        return LoopNode(content)


class BFMemory:
    data: BidirectionalByteArray
    pointer: int

    def __init__(self):
        self.data = BidirectionalByteArray()
        self.pointer = 0

    def read(self):
        return self.data.read(self.pointer)

    def write(self, byte: int):
        self.data.writeByte(byte & 0xFF, self.pointer)

    def add(self):
        self.write(self.read() + 1)

    def sub(self):
        self.write(self.read() - 1)

    def left(self):
        self.pointer -= 1

    def right(self):
        self.pointer += 1


class InterpreterRecursionError(InterpreterError):
    msg = "Failed to interpret - recursion error"


class BFInterpreter(Interpreter):
    def interpret(self, ast: AST, output: TextOutput, memory: BFMemory | None = None) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        if memory is None:
            memory: BFMemory = BFMemory()
        try:
            self.interpretThing(ast, list(ast.rootNodes()), memory, output)
        except RecursionError as e:
            return InterpreterExitCode.WARNING, InterpreterRecursionError(e)
        except Exception as e:
            return InterpreterExitCode.ERROR, InterpreterError(e)
        return InterpreterExitCode.OK, None

    def interpretThing(self, ast: AST, nodes: list[ASTNode], memory: BFMemory, output: TextOutput):
        for node in nodes:
            if node.type == BFNode.LOOP:
                self.interpretLoop(ast, node.data, memory, output)
            elif node.type == BFNode.CONTROL:
                assert isinstance(node, ControlNode)
                self.interpretControlNode(node, memory, output)
            else:
                raise ValueError("Unknown node")

    def interpretLoop(self, ast: AST, loopNodeIndexes: list[int], memory: BFMemory,
                      output: TextOutput):
        loopNodes: list[ASTNode] = list(map(lambda i: ast.getNode(i), loopNodeIndexes))
        amount: int = 0
        while memory.read() > 0:
            self.interpretThing(ast, loopNodes, memory, output)
            amount += 1
            if amount > 10_000:
                raise RecursionError

    @staticmethod
    def interpretControlNode(node: ControlNode, memory: BFMemory, output: TextOutput):
        if node.data == BFToken.INC_PTR.value:
            memory.right()
        elif node.data == BFToken.DEC_PTR.value:
            memory.left()
        elif node.data == BFToken.INC_DAT.value:
            memory.add()
        elif node.data == BFToken.DEC_DAT.value:
            memory.sub()
        elif node.data == BFToken.OUT_DAT.value:
            output.print(chr(memory.read()), newline=False, sep="")
        elif node.data == BFToken.ACC_DAT.value:
            inp: str = input("Enter a character as an input (or a number prefixed with n): ")
            val: int = 0
            if not inp:
                inp = "0"
            if inp.startswith("n"):
                try:
                    val = int(inp)
                except ValueError:
                    pass
            else:
                val = ord(inp[0])
            memory.write(val)


class BrainFuck(InterpretedLanguage):
    def __init__(self):
        super().__init__(BFLexer(), BFParser(), BFInterpreter())

    def run(self, inputCode: str, output: Optional[TextOutput] = None,
            memory: BFMemory | None = None) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        ast: AST = GenericLanguage.run(self, inputCode)
        if output is None:
            output = TextOutput()
        return self.interpretInner(ast, output, memory)

    def interpretInner(self, ast: AST, output: TextOutput, memory: BFMemory | None = None) -> \
            tuple[InterpreterExitCode, InterpreterError | None]:
        assert isinstance(self.interpreter, BFInterpreter)
        return self.interpreter.interpret(ast, output, memory)

    @staticmethod
    def name() -> str:
        return "BrainFuck"

    @staticmethod
    def fuck(inputCode: str, callPrint: bool = True) -> str:
        output: TextOutput = TextOutput(encoding="ascii", callPrint=callPrint)
        language: BrainFuck = BrainFuck()
        exitCode, error = language.run(inputCode, output)
        # Handle errors
        if exitCode != InterpreterExitCode.OK:
            raise error
        return output.export()


# __all__ = ["BrainFuck"] Why?

if __name__ == '__main__':
    test_suite: dict[str, str] = {
        # https://en.wikipedia.org/wiki/Brainfuck#Hello_World!
        "+[-->-[>>+>-----<<]<--<---]>-.>>>+.>>..+++[.>]<<<<.+++.------.<<-.>>>>+.": "Hello, World!",
        # My code
        "+++++[>+++++<-]>[<+++>-]<+.+++.---.": "LOL"
    }
    for bf, res in test_suite.items():
        assert BrainFuck.fuck(bf, False) == res
    print(f"{Fore.GREEN}All tests passed.{Style.RESET_ALL}")

    output: TextOutput = TextOutput(encoding="ascii", callPrint=True)
    language: BrainFuck = BrainFuck()
    while True:
        output.clear()
        code = input("Enter code: ")
        print("=" * 5, "CODE START", "=" * 5)
        memory: BFMemory = BFMemory()
        exitCode, the_error = language.run(code, output, memory)
        print("\n" + "=" * 5, " CODE END ", "=" * 5)
        print(f"Program finished with exit code {exitCode.name}")
        if the_error is not None:
            print(Fore.RED + str(the_error) + Style.RESET_ALL)
        print("Memdump:")
        print(memory.data.export(), end="\n\n")
        print(memory.data.export().decode("utf-8"))
        print(f"Pointer: {memory.pointer}")
