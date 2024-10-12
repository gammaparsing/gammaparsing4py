from collections import deque
from io import StringIO
import itertools
from typing import Callable, Iterator, Generic, TypeVar

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.core.token import Token
from gammaparsing4py.tokenizer.regex import (
    Regex,
    RegexChoice,
    RegexClass,
    RegexQuantified,
    RegexRange,
    RegexSequence,
    getRegexChildren,
    parseRegex,
)
from gammaparsing4py.utils import unfoldPostfix

T = TypeVar("T")


class AVLTreeNode(Generic[T]):

    def __init__(self, key: RegexRange, value: T):
        self.key: RegexRange = key
        self.value: T = value

        self.left: AVLTreeNode = None
        self.right: AVLTreeNode = None

        self.height: int = -1

    def getChildren(self):
        if self.left is None and self.right is None:
            return []

        if self.left is None:
            return [self.right]

        if self.right is None:
            return [self.left]

        return [self.left, self.right]

    def __repr__(self) -> str:
        return "AVLTreeNode(key={}, value={})".format(self.key, self.value)


def iteratorAVLTreeNode(node: AVLTreeNode[T]):
    if node is None:
        return
    stack: deque[AVLTreeNode[T]] = deque()
    stack.append(node)

    while stack:
        current = stack.pop()
        yield current

        stack.extend(reversed(current.getChildren()))


class AVLTree(Generic[T]):

    def __init__(self):
        self.root: AVLTreeNode[T] = None

    def _height(node: AVLTreeNode[T]):
        return node.height if node is not None else -1

    def _updateHeigh(node: AVLTreeNode[T]):
        node.height = 1 + max(AVLTree._height(node.left), AVLTree._height(node.right))

    def _balance(node: AVLTreeNode[T]):
        return (
            AVLTree._height(node.right) - AVLTree._height(node.left)
            if node is not None
            else 0
        )

    def __iter__(self):
        return iteratorAVLTreeNode(self.root)

    def _rotateRight(node: AVLTreeNode[T]):
        x = node.left

        node.left = x.right
        x.right = node

        AVLTree._updateHeigh(node)
        AVLTree._updateHeigh(x)

        return x

    def _rotateLeft(node: AVLTreeNode[T]):
        x = node.right

        node.right = x.left
        x.left = node

        AVLTree._updateHeigh(node)
        AVLTree._updateHeigh(x)

        return x

    def _rebalance(node: AVLTreeNode[T]):
        AVLTree._updateHeigh(node)
        factor = AVLTree._balance(node)

        if factor > 1:
            if AVLTree._balance(node.right) < 0:
                node.right = AVLTree._rotateRight(node.right)

            return AVLTree._rotateLeft(node)
        elif factor < -1:
            if AVLTree._balance(node.left) > 0:
                node.left = AVLTree._rotateLeft(node.left)

            return AVLTree._rotateRight(node)

        return node

    def _insert(node: AVLTreeNode[T], key: RegexRange, value: T):
        if node is None:
            return AVLTreeNode(key, value)

        if key.start > node.key.end:
            node.right = AVLTree._insert(node.right, key, value)
        elif key.end < node.key.start:
            node.left = AVLTree._insert(node.left, key, value)

        return AVLTree._rebalance(node)

    def insert(self, key: RegexRange, value: T):
        self.root = AVLTree._insert(self.root, key, value)

    def find(self, target: int, default: T = None):
        current = self.root

        while current is not None:
            if current.key.start > target:
                current = current.left
                continue
            if current.key.end < target:
                current = current.right
                continue

            return current.value

        return default


class TokenizerNode(Generic[T]):

    def __init__(self, id: int):
        self.id: int = id
        self.entry: tuple[T, bool] = None
        self.tree: AVLTree[TokenizerNode[T]] = AVLTree()

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, value: object) -> bool:
        return isinstance(value, TokenizerNode) and self.id == value.id

    def graphviz(self, prefix: str = ""):
        return "\n".join(
            itertools.chain(
                (
                    '{}{} -> {}{} [label="{}"]'.format(
                        prefix, self.id, prefix, node.value.id, node.key
                    )
                    for node in self.tree
                ),
                (
                    ['{}{} [label="{}"]'.format(prefix, self.id, self.entry)]
                    if self.entry is not None
                    else []
                ),
            )
        )


class TokenizerBuildNode(Generic[T]):

    def __init__(self, id: int):
        self.id: int = id
        self.entry: tuple[T, bool, set[T]] = None
        self.transitions: list[tuple[RegexRange, TokenizerBuildNode[T]]] = []
        self.epsilonTransitions: set[TokenizerBuildNode[T]] = set()

    def getTransitions(self):
        return self.transitions

    def getWrappedTransitions(self):
        return ((key, set([target])) for key, target in self.transitions)

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, value: object) -> bool:
        return isinstance(value, TokenizerBuildNode) and self.id == value.id

    def graphviz(self, prefix: str = ""):
        return "\n".join(
            itertools.chain(
                (
                    '{}{} -> {}{} [label="{}"]'.format(
                        prefix, self.id, prefix, target.id, range
                    )
                    for range, target in self.transitions
                ),
                (
                    '{}{} -> {}{} [label="epsilon"]'.format(
                        prefix, self.id, prefix, target.id
                    )
                    for target in self.epsilonTransitions
                ),
                (
                    ['{}{} [label="{}"]'.format(prefix, self.id, self.entry)]
                    if self.entry is not None
                    else []
                ),
            )
        )

    def __repr__(self):
        return "TokenizerBuildNode(id={})".format(self.id)


def determinize(
    rootBuildNode: TokenizerBuildNode[T], buildBodes: list[TokenizerBuildNode[T]]
) -> list[TokenizerNode[T]]:

    # Computing epsilon closures
    epsilonClosures: list[set[TokenizerBuildNode[T]]] = [
        set([node]) for node in buildBodes
    ]

    changed = True
    while changed:
        changed = False
        for targetSet in epsilonClosures:
            previousLength = len(targetSet)

            added = set()
            for node in targetSet:
                for accessible in node.epsilonTransitions:
                    added.update(epsilonClosures[accessible.id])

            targetSet.update(added)

            changed |= previousLength != len(targetSet)

    # Preparing the mapping
    nodes: deque[TokenizerNode[T]] = deque()
    nodeMap: dict[frozenset[TokenizerBuildNode[T]], TokenizerNode[T]] = {}
    stack: deque[tuple[frozenset[TokenizerBuildNode[T]], TokenizerNode[T]]] = deque()

    def nodeFactory(targetSet: frozenset[TokenizerBuildNode[T]]) -> TokenizerNode[T]:
        node = TokenizerNode(len(nodes))
        nodes.append(node)
        nodeMap[targetSet] = node
        stack.append((targetSet, node))

        return node

    # Handling the root node
    rootSet = frozenset(epsilonClosures[rootBuildNode.id])
    nodeFactory(rootSet)

    while stack:
        currentSet, currentNode = stack.pop()

        entry: tuple[T, bool, set[T]] = None
        for node in currentSet:
            if node.entry is not None:
                if entry is None:
                    entry = node.entry[0], node.entry[1], set(node.entry[2])
                    continue

                entryKey = entry[0]
                nodeEntryKey = node.entry[0]
                if entryKey == nodeEntryKey:
                    entry[1] |= node.entry[1]
                    entry[2].update(node.entry[2])
                    continue

                if entryKey in node.entry[2]:
                    entry = node.entry[0], node.entry[1], set(node.entry[2])
                    continue

                if nodeEntryKey in entry[2]:
                    continue

                raise Exception(
                    "Unable to choose between {} and {}".format(entryKey, nodeEntryKey)
                )

        if entry is not None:
            currentNode.entry = entry[0], entry[1]

        transitions: list[tuple[RegexRange, TokenizerBuildNode[T]]] = (
            RegexRange.disjointValuedList(
                itertools.chain.from_iterable(
                    map(TokenizerBuildNode.getWrappedTransitions, currentSet)
                )
            )
        )

        for key, targets in transitions:
            closedSet = frozenset(
                itertools.chain.from_iterable(
                    map(lambda node: epsilonClosures[node.id], targets)
                )
            )

            targetNode = nodeMap.get(closedSet)
            if targetNode is None:
                targetNode = nodeFactory(closedSet)

            currentNode.tree.insert(key, targetNode)

    return nodes


class TokenizerBuilder(Generic[T]):

    def __init__(self):
        self.entries: list[tuple[Regex, T, bool, set[T]]] = []

    def addRawPattern(
        self, pattern: str, value: T, reluctant: bool = False, above: set[T] = set()
    ):
        self.entries.append(
            (parseRegex(CharFlow.fromString(pattern)), value, reluctant, above)
        )

    def build(
        self,
        eof: T = None,
    ):
        buildNodes: deque[TokenizerBuildNode[T]] = deque()

        def buildNodeFactory() -> TokenizerBuildNode[T]:
            node = TokenizerBuildNode(len(buildNodes))
            buildNodes.append(node)
            return node

        rootNode = buildNodeFactory()

        for pattern, value, reluctant, above in self.entries:
            stack: deque[tuple[TokenizerBuildNode[T], TokenizerBuildNode[T]]] = deque()

            for fragment in reversed(unfoldPostfix(pattern, getRegexChildren)):

                if isinstance(fragment, RegexClass):
                    start, end = buildNodeFactory(), buildNodeFactory()

                    for range in fragment.ranges:
                        start.transitions.append((range, end))

                    stack.append((start, end))
                    continue

                if isinstance(fragment, RegexQuantified):
                    start, end = buildNodeFactory(), buildNodeFactory()
                    pstart, pend = stack.pop()

                    start.epsilonTransitions.add(pstart)
                    pend.epsilonTransitions.add(end)

                    if fragment.quantifier == RegexQuantified.STAR:
                        start.epsilonTransitions.add(end)
                        end.epsilonTransitions.add(start)

                    if fragment.quantifier == RegexQuantified.PLUS:
                        end.epsilonTransitions.add(start)

                    if fragment.quantifier == RegexQuantified.INTERROGATION_MARK:
                        start.epsilonTransitions.add(end)

                    stack.append((start, end))
                    continue

                if isinstance(fragment, RegexSequence):
                    start = buildNodeFactory()
                    end = start

                    for _ in fragment.getChildren():
                        itemStart, itemEnd = stack.pop()
                        end.epsilonTransitions.add(itemStart)
                        end = itemEnd

                    stack.append((start, end))
                    continue

                if isinstance(fragment, RegexChoice):
                    start, end = buildNodeFactory(), buildNodeFactory()

                    for _ in fragment.getChildren():
                        itemStart, itemEnd = stack.pop()

                        start.epsilonTransitions.add(itemStart)
                        itemEnd.epsilonTransitions.add(end)

                    stack.append((start, end))

            start, end = stack.pop()
            rootNode.epsilonTransitions.add(start)
            end.entry = value, reluctant, above

        return Tokenizer(determinize(rootNode, buildNodes), eof=eof)


class Tokenizer(Generic[T]):

    def __init__(
        self,
        nodes: list[TokenizerNode[T]],
        eof: T = None,
        skipper: Callable[[Token[T]], bool] = lambda token: False,
    ):
        self.nodes: list[TokenizerNode[T]] = nodes
        self.eof: T = eof
        self.skipper: Callable[[Token[T]], bool] = skipper

    def readToken(self, flow: CharFlow) -> Token[T]:
        if not flow.hasMore():
            return Token(self.eof, None, flow.line, flow.column)

        buffer = StringIO()
        line = flow.line
        column = flow.column

        current = self.nodes[0]

        while flow.hasMore():
            if current.entry is not None and current.entry[1]:
                break

            nextNode = current.tree.find(flow.peek())

            if nextNode is None:
                break

            buffer.write(chr(flow.next()))
            current = nextNode

        if current.entry is not None:
            return Token(current.entry[0], buffer.getvalue(), line, column)

        if len(buffer.getvalue()) == 0 and flow.hasMore():
            buffer.write(chr(flow.peek()))
        raise Exception(
            "Unable to parse '\x1b[1;31m{}\x1b[0m' at line {}, column {}".format(
                buffer.getvalue(), line, column
            )
        )

    def nextToken(self, flow: CharFlow) -> Token[T]:
        result: Token[T] = self.readToken(flow)

        while self.skipper(result):
            result = self.readToken(flow)

        return result

    def iterator(self, flow: CharFlow):
        return TokenizerIterator(self, flow)


class TokenizerIterator(Iterator[Token[T]]):

    def __init__(self, tokenizer: Tokenizer[T], flow: CharFlow):
        self.tokenizer: Tokenizer[T] = tokenizer
        self.flow: CharFlow = flow

        self.hasReachedEOF: bool = False

    def __next__(self):
        if self.hasReachedEOF:
            raise StopIteration()

        token = self.tokenizer.nextToken(self.flow)
        if token.key == self.tokenizer.eof:
            self.hasReachedEOF = True
        return token
