from __future__ import annotations
from collections import deque
from io import StringIO
import itertools
from typing import Callable, Iterable

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.parser.symbols import (
    NonTerminal,
    SolidTerminal,
    SpecialTerminal,
    Symbol,
)
from gammaparsing4py.tokenizer.regex import flatten
from gammaparsing4py.utils import unfoldPostfix


class GammaRegex:

    def getChildren(self) -> list[GammaRegex]:
        raise NotImplementedError()

    def getShortName(self) -> str:
        raise NotImplementedError()


def getGammaRegexChildren(target: GammaRegex):
    return target.getChildren()


def getGammaRegexShortName(target: GammaRegex):
    return target.getShortName()


class GammaRegexChoice(GammaRegex):

    def __init__(self, options: list[GammaRegex]):
        self.options: list[GammaRegex] = options

    def getChildren(self) -> list[GammaRegex]:
        return self.options

    def getShortName(self) -> str:
        return "GammaRegexChoice({})".format(len(self.options))

    def isChoice(target: GammaRegex):
        return isinstance(target, GammaRegexChoice)

    def of(options: Iterable[GammaRegex]) -> GammaRegex:
        flat = flatten(options, GammaRegexChoice.isChoice, getGammaRegexChildren)

        if len(flat) == 1:
            return flat.pop()

        return GammaRegexChoice(list(flat))


class GammaRegexSequence(GammaRegex):

    def __init__(self, items: list[GammaRegex]):
        self.items: list[GammaRegex] = items

    def getChildren(self) -> list[GammaRegex]:
        return self.items

    def getShortName(self) -> str:
        return "GammaRegexSequence({})".format(len(self.items))

    def isSequence(target: GammaRegex):
        return isinstance(target, GammaRegexSequence)

    def of(options: Iterable[GammaRegex]) -> GammaRegex:
        flat = flatten(options, GammaRegexSequence.isSequence, getGammaRegexChildren)

        if len(flat) == 1:
            return flat.pop()

        if len(flat) == 0:
            return GammaRegexSymbol(SpecialTerminal(SpecialTerminal.EMPTY))

        return GammaRegexSequence(list(flat))


class GammaRegexQuantified(GammaRegex):

    STAR = 0
    PLUS = 1
    INTERROGATION_MARK = 2

    def __init__(self, quantifier: int, target: GammaRegex):
        self.quantifier: int = quantifier
        self.target: GammaRegex = target

    def getChildren(self) -> list[GammaRegex]:
        return [self.target]

    def getShortName(self) -> str:
        return "GammaRegexQuantified({})".format(self.quantifier)


class GammaRegexSymbol(GammaRegex):

    def __init__(self, symbol: Symbol):
        self.symbol: Symbol = symbol

    def getChildren(self) -> list[GammaRegexSymbol]:
        return []

    def getShortName(self) -> str:
        return "GammaRegexSymbol({})".format(self.symbol)


"""
Grammar for gamma regular expressions:  
E -> T ('|' T)?  
T -> F*  
F -> B ('+'|'*'|'?')*
B -> '(' E ')'
B -> Terminal | NonTerminal
Terminal -> '\'' I '\''
NonTerminal -> I
I -> "[a-zA-Z_][a-zA-Z0-9_]*"
"""


def readGammaRegex(
    flow: CharFlow, solidTerminal=SolidTerminal, nonTerminal=NonTerminal
) -> GammaRegex:
    return _readExpression(flow, solidTerminal, nonTerminal)


@CharFlow.skipBlanksAndCommentsDecorator
def _readExpression(
    flow: CharFlow,
    solidTerminal: Callable[[str], SolidTerminal],
    nonTerminal: Callable[[str], NonTerminal],
) -> GammaRegex:
    acc: deque[GammaRegex] = deque()

    acc.append(_readTerm(flow, solidTerminal, nonTerminal))
    while flow.check(ord("|")):
        acc.append(_readTerm(flow, solidTerminal, nonTerminal))

    return GammaRegexChoice.of(acc)


@CharFlow.skipBlanksAndCommentsDecorator
def _readTerm(
    flow: CharFlow,
    solidTerminal: Callable[[str], SolidTerminal],
    nonTerminal: Callable[[str], NonTerminal],
) -> GammaRegex:
    acc: deque[GammaRegex] = deque()

    while (
        flow.hasMore()
        and flow.peek() != ord("|")
        and flow.peek() != ord(")")
        and flow.peek() != ord(";")
    ):
        acc.append(_readFactor(flow, solidTerminal, nonTerminal))

    return GammaRegexSequence.of(reversed(acc))


@CharFlow.skipBlanksAndCommentsDecorator
def _readFactor(
    flow: CharFlow,
    solidTerminal: Callable[[str], SolidTerminal],
    nonTerminal: Callable[[str], NonTerminal],
) -> GammaRegex:
    result: GammaRegex = _readBase(flow, solidTerminal, nonTerminal)

    while flow.hasMore():
        if flow.check(ord("+")):
            result = GammaRegexQuantified(GammaRegexQuantified.PLUS, result)
            continue

        if flow.check(ord("*")):
            result = GammaRegexQuantified(GammaRegexQuantified.STAR, result)
            continue

        if flow.check(ord("?")):
            result = GammaRegexQuantified(
                GammaRegexQuantified.INTERROGATION_MARK, result
            )
            continue
        break
    return result


@CharFlow.skipBlanksAndCommentsDecorator
def _readBase(
    flow: CharFlow,
    solidTerminal: Callable[[str], SolidTerminal],
    nonTerminal: Callable[[str], NonTerminal],
) -> GammaRegex:
    if flow.check(ord("(")):
        result = _readExpression(flow, solidTerminal, nonTerminal)
        flow.read(ord(")"))
        return result

    if flow.check(ord("'")):
        buffer = StringIO()
        while flow.peek() != ord("'"):
            buffer.write(chr(flow.next()))

        flow.read(ord("'"))

        return GammaRegexSymbol(solidTerminal(buffer.getvalue()))

    return GammaRegexSymbol(nonTerminal(_readIdentifier(flow)))


@CharFlow.skipBlanksAndCommentsDecorator
def _readIdentifier(flow: CharFlow) -> str:
    buffer = StringIO()

    first = chr(flow.next())
    if not first.isalpha() and first != "_":
        raise Exception(
            "Unexpected first character '{}' when reading identifier at line {}, column {}".format(
                first, flow.line, flow.column
            )
        )

    buffer.write(first)
    while flow.hasMore() and chr(flow.peek()).isalnum() or flow.peek() == ord("_"):
        buffer.write(chr(flow.next()))

    return buffer.getvalue()


class GammaRegexBuildNode:

    def __init__(self, id: int) -> None:
        self.id: int = id
        self.transitions: list[tuple[Symbol, GammaRegexBuildNode]] = []
        self.epsilonTransitions: set[GammaRegexBuildNode] = set()

        self.isFinal: bool = False

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, value: object) -> bool:
        return isinstance(value, GammaRegexBuildNode) and self.id == value.id

    def __repr__(self) -> str:
        return "GammaRegexBuildNode(id={}, isFinal={})".format(self.id, self.isFinal)

    def graphviz(self, prefix: str = ""):
        return "\n".join(
            itertools.chain(
                (
                    '{}{} -> {}{} [label="{}"]'.format(
                        prefix, self.id, prefix, target.id, symbol
                    )
                    for symbol, target in self.transitions
                ),
                (
                    '{}{} -> {}{} [label="epsilon"]'.format(
                        prefix, self.id, prefix, target.id
                    )
                    for target in self.epsilonTransitions
                ),
                (
                    ["{}{} [peripheries=2]".format(prefix, self.id)]
                    if self.isFinal
                    else []
                ),
            )
        )


class GammaRegexNode:

    def __init__(self, id: int) -> None:
        self.id: int = id
        self.transitions: dict[Symbol, GammaRegexNode] = {}
        self.isFinal: bool = False

    def isNodeFinal(self):
        return self.isFinal

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, value: object) -> bool:
        return isinstance(value, GammaRegexNode) and self.id == value.id

    def graphviz(self, prefix: str = "", selected: int = None):
        return "\n".join(
            itertools.chain(
                (
                    '{}{} -> {}{} [label="{}"]'.format(
                        prefix, self.id, prefix, target.id, symbol
                    )
                    for symbol, target in self.transitions.items()
                ),
                (
                    ["{}{} [peripheries=2]".format(prefix, self.id)]
                    if self.isFinal
                    else []
                ),
                (
                    ['{}{} [color="red"]'.format(prefix, selected)]
                    if selected == self.id
                    else []
                ),
            )
        )


def buildRuleContent(gammaRegex: GammaRegex):

    buildNodes: deque[GammaRegexBuildNode] = deque()

    def buildNodeFactory() -> GammaRegexBuildNode:
        node = GammaRegexBuildNode(len(buildNodes))
        buildNodes.append(node)
        return node

    stack: deque[tuple[GammaRegexBuildNode, GammaRegexBuildNode]] = deque()
    for fragment in reversed(unfoldPostfix(gammaRegex, getGammaRegexChildren)):

        if isinstance(fragment, GammaRegexSymbol):
            start, end = buildNodeFactory(), buildNodeFactory()

            start.transitions.append((fragment.symbol, end))

            stack.append((start, end))
            continue

        if isinstance(fragment, GammaRegexQuantified):
            pStart, pEnd = stack.pop()

            start, end = buildNodeFactory(), buildNodeFactory()

            start.epsilonTransitions.add(pStart)
            pEnd.epsilonTransitions.add(end)

            if fragment.quantifier == GammaRegexQuantified.STAR:
                start.epsilonTransitions.add(end)
                end.epsilonTransitions.add(start)

            if fragment.quantifier == GammaRegexQuantified.PLUS:
                end.epsilonTransitions.add(start)

            if fragment.quantifier == GammaRegexQuantified.INTERROGATION_MARK:
                start.epsilonTransitions.add(end)

            stack.append((start, end))
            continue

        if isinstance(fragment, GammaRegexSequence):
            start = buildNodeFactory()
            end = start

            for _ in fragment.getChildren():
                pStart, pEnd = stack.pop()
                end.epsilonTransitions.add(pStart)
                end = pEnd

            stack.append((start, end))
            continue

        if isinstance(fragment, GammaRegexChoice):
            start, end = buildNodeFactory(), buildNodeFactory()

            for _ in fragment.getChildren():
                pStart, pEnd = stack.pop()
                start.epsilonTransitions.add(pStart)
                pEnd.epsilonTransitions.add(end)

            stack.append((start, end))
            continue

    start, end = stack.pop()
    end.isFinal = True

    return determinizeRuleContent(start, buildNodes)


def reverseRuleContent(rootNode: GammaRegexNode, nodes: list[GammaRegexNode]):
    buildNodes = [GammaRegexBuildNode(node.id) for node in nodes]

    start = GammaRegexBuildNode(len(buildNodes))
    buildNodes.append(start)

    buildNodes[rootNode.id].isFinal = True

    for node in nodes:
        for symbol, targetNode in node.transitions.items():
            buildNodes[targetNode.id].transitions.append((symbol, buildNodes[node.id]))
        if node.isFinal:
            start.epsilonTransitions.add(buildNodes[node.id])

    return determinizeRuleContent(start, buildNodes)


def determinizeRuleContent(
    rootNode: GammaRegexBuildNode, buildNodes: list[GammaRegexBuildNode]
) -> list[GammaRegexNode]:

    epsilonClosures: list[set[GammaRegexBuildNode]] = [
        set([node]) for node in buildNodes
    ]

    changed = True
    while changed:
        changed = False

        for targetSet in epsilonClosures:
            previousLength: int = len(targetSet)

            added: set[GammaRegexBuildNode] = set()
            for node in targetSet:
                for accessible in node.epsilonTransitions:
                    added.update(epsilonClosures[accessible.id])

            targetSet.update(added)
            changed |= previousLength != len(targetSet)

    nodes: deque[GammaRegexNode] = deque()
    nodeMap: dict[frozenset[GammaRegexBuildNode], GammaRegexNode] = {}
    stack: deque[tuple[frozenset[GammaRegexBuildNode], GammaRegexNode]] = deque()

    def nodeFactory(targetSet: frozenset[GammaRegexBuildNode]):
        node = GammaRegexNode(len(nodes))
        nodes.append(node)
        nodeMap[targetSet] = node
        stack.append((targetSet, node))
        return node

    rootSet = frozenset(epsilonClosures[rootNode.id])
    nodeFactory(rootSet)

    while stack:
        currentSet, currentNode = stack.pop()

        transitions: dict[Symbol, set[GammaRegexBuildNode]] = {}

        for node in currentSet:
            currentNode.isFinal |= node.isFinal

            for symbol, target in node.transitions:
                if symbol not in transitions:
                    transitions[symbol] = set()

                transitions[symbol].add(target)

        for symbol, targets in transitions.items():
            closed: set[GammaRegexBuildNode] = frozenset(
                itertools.chain.from_iterable(
                    map(lambda node: epsilonClosures[node.id], targets)
                )
            )

            targetNode = nodeMap.get(closed, None)
            if targetNode is None:
                targetNode = nodeFactory(closed)

            currentNode.transitions[symbol] = targetNode

    return nodes
