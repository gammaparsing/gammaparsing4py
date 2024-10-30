from __future__ import annotations
from collections import deque
from io import StringIO
from typing import Callable, Iterable
from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.parser.gammaregex import (
    GammaRegex,
    GammaRegexNode,
    buildRuleContent,
    readGammaRegex,
    reverseRuleContent,
)
from gammaparsing4py.parser.parser import (
    Parser,
    ParserAcceptAction,
    ParserAction,
    ParserReduceAction,
    ParserShiftAction,
    ParserState,
)
from gammaparsing4py.parser.struct import Rule
from gammaparsing4py.parser.symbols import (
    AbstractTerminal,
    NonTerminal,
    SolidTerminal,
    SpecialTerminal,
    Symbol,
)
from gammaparsing4py.utils import unfoldPostfix


class MarkedRule:

    def __init__(self, rule: Rule, mark: int):
        self.rule: Rule = rule
        self.mark: int = mark

    def __hash__(self) -> int:
        return hash((self.rule, self.mark))

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, MarkedRule)
            and self.rule == value.rule
            and self.mark == value.mark
        )

    def graphviz(self, prefix: str):
        buffer = StringIO()
        for node in self.rule.nodes:
            buffer.write(node.graphviz(prefix, self.mark))

            if node.id < len(self.rule.nodes) - 1:
                buffer.write("\n")

        return buffer.getvalue()


class ConstrainedMarkedRule:

    def __init__(self, markedRule: MarkedRule, lookAheads: frozenset[AbstractTerminal]):
        self.markedRule: MarkedRule = markedRule
        self.lookAheads: frozenset[AbstractTerminal] = lookAheads

        self.followSets: list[set[AbstractTerminal]] = None

    def computeFollowSets(self, firstSets: dict[NonTerminal, set[AbstractTerminal]]):
        if self.followSets is not None:
            return
        self.followSets = [set() for _ in self.markedRule.rule.nodes]

        reversed: list[list[GammaRegexNode]] = [[] for _ in self.markedRule.rule.nodes]
        for node in self.markedRule.rule.nodes:
            for targetNode in node.transitions.values():
                reversed[targetNode.id].append(node)

        nodesToCheck: set[GammaRegexNode] = set(
            filter(GammaRegexNode.isNodeFinal, self.markedRule.rule.nodes)
        )
        while nodesToCheck:
            nextNodes: set[GammaRegexNode] = set()

            for currentNode in nodesToCheck:
                currentSet = self.followSets[currentNode.id]

                previousLength = len(currentSet)

                if currentNode.isFinal and not currentSet:
                    currentSet.update(self.lookAheads)

                for symbol, targetNode in currentNode.transitions.items():
                    if isinstance(symbol, SolidTerminal):
                        currentSet.add(symbol)
                        continue

                    if isinstance(symbol, NonTerminal):
                        targetFirstSet = firstSets[symbol]

                        if SpecialTerminal.EMPTY() in targetFirstSet:
                            trimmed = set(targetFirstSet)
                            trimmed.remove(SpecialTerminal.EMPTY())
                            currentSet.update(trimmed)
                            currentSet.update(self.followSets[targetNode.id])
                        else:
                            currentSet.update(targetFirstSet)
                        continue

                    raise Exception("Unexpected symbol '{}'".format(symbol))

                if previousLength != len(currentSet):
                    nextNodes.update(reversed[currentNode.id])

            nodesToCheck = nextNodes

    def __hash__(self) -> int:
        return hash((self.markedRule, self.lookAheads))

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ConstrainedMarkedRule)
            and self.markedRule == value.markedRule
            and self.lookAheads == value.lookAheads
        )

    def __repr__(self) -> str:
        return "ConstrainedMarkedRule(id={}, mark={}, lookAheads={})".format(
            self.markedRule.rule.id, self.markedRule.mark, self.lookAheads
        )


class ParserBuilderNode:

    def __init__(self, constrainedRules: frozenset[ConstrainedMarkedRule]):
        self.constrainedRules: frozenset[ConstrainedMarkedRule] = constrainedRules
        self.transitions: dict[Symbol, ParserBuilderNode] = {}

        self.id: int = 0

    def of(
        sourceConstrainedRules: Iterable[ConstrainedMarkedRule],
        firstSets: dict[NonTerminal, set[AbstractTerminal]],
        generators: dict[NonTerminal, list[Rule]],
    ) -> ParserBuilderNode:
        stack: deque[ConstrainedMarkedRule] = deque(sourceConstrainedRules)
        resultRules: set[ConstrainedMarkedRule] = set(stack)

        for rule in stack:
            rule.computeFollowSets(firstSets)

        while stack:
            currentRule = stack.pop()

            for symbol, targetNode in currentRule.markedRule.rule.nodes[
                currentRule.markedRule.mark
            ].transitions.items():
                if not isinstance(symbol, NonTerminal):
                    continue

                for generator in generators[symbol]:
                    newRule = ConstrainedMarkedRule(
                        MarkedRule(generator, 0),
                        frozenset(currentRule.followSets[targetNode.id]),
                    )

                    if newRule not in resultRules:
                        stack.append(newRule)
                        resultRules.add(newRule)
                        newRule.computeFollowSets(firstSets)

        mergedRules: dict[MarkedRule, set[AbstractTerminal]] = {}

        for rule in resultRules:
            if rule.markedRule not in mergedRules:
                mergedRules[rule.markedRule] = set(rule.lookAheads)
            else:
                mergedRules[rule.markedRule].update(rule.lookAheads)

        finalRules: list[ConstrainedMarkedRule] = []

        for rule, lookAheads in mergedRules.items():
            newRule = ConstrainedMarkedRule(rule, frozenset(lookAheads))
            newRule.computeFollowSets(firstSets)
            finalRules.append(newRule)

        return ParserBuilderNode(frozenset(finalRules))

    def __hash__(self) -> int:
        return hash(self.constrainedRules)

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, ParserBuilderNode)
            and self.constrainedRules == value.constrainedRules
        )

    def fullPresentation(self):
        buffer = StringIO()
        buffer.write(
            "\x1b[1;31m===== ParserBuilderNode {} =====\x1b[0m\n".format(self.id)
        )
        for index, rule in enumerate(self.constrainedRules):
            buffer.write("\x1b[1;35m{} : {}\x1b[0m\n".format(index, rule.lookAheads))
            buffer.write(rule.markedRule.graphviz("PBN{}_R{}_".format(self.id, index)))
            if index < len(self.constrainedRules) - 1:
                buffer.write("\n")

        return buffer.getvalue()


class ParserBuilder:

    def __init__(self):
        self.rules: list[Rule] = []
        self.terminals: dict[str, SolidTerminal] = {}
        self.nonTerminals: dict[str, NonTerminal] = {}
        self.conflictSolver: Callable[
            [dict[ParserAction, list[ConstrainedMarkedRule]]], ParserAction
        ] = None

        # Computed
        self.terminalList: list[SolidTerminal] = []
        self.nonTerminalList: list[NonTerminal] = []
        self.generators: dict[NonTerminal, list[Rule]] = {}
        self.firstSets: dict[NonTerminal, set[AbstractTerminal]] = {}

        self.nodes: list[ParserBuilderNode] = []

    def addRule(self, rule: Rule):
        rule.id = len(self.rules)
        self.rules.append(rule)

    def addRegexRule(
        self,
        nonTerminal: str,
        gammaRegex: GammaRegex,
        name: str = None,
        tags: set[str] = None,
    ):
        ruleContent = buildRuleContent(gammaRegex)
        self.addRule(
            Rule(
                self.getNonTerminal(nonTerminal),
                ruleContent,
                reverseRuleContent(ruleContent[0], ruleContent),
                name=name,
                tags=tags,
            )
        )

    def addRawRule(self, nonTerminal: str, gammaRegex: str, name: str = None):
        self.addRegexRule(
            nonTerminal,
            readGammaRegex(
                CharFlow.fromString(gammaRegex),
                self.getTerminal,
                self.getNonTerminal,
            ),
            name,
        )

    def getTerminal(self, name: str):
        if name not in self.terminals:
            self.terminals[name] = SolidTerminal(name)

        return self.terminals[name]

    def getNonTerminal(self, name: str):
        if name not in self.nonTerminals:
            self.nonTerminals[name] = NonTerminal(name)

        return self.nonTerminals[name]

    def build(self, rootNonTerminal: NonTerminal):
        self._prepareSymbols()
        self._prepareGenerators()
        self._computeFirstSets()
        self._computeNodes(rootNonTerminal)
        return self._computeStates(rootNonTerminal)

    def _prepareSymbols(self):
        terminals: set[AbstractTerminal] = set()
        nonTerminals: set[NonTerminal] = set()

        for rule in self.rules:
            nonTerminals.add(rule.nonTerminal)

            for node in rule.nodes:
                for symbol in node.transitions.keys():
                    if isinstance(symbol, SolidTerminal):
                        terminals.add(symbol)
                        continue

                    if isinstance(symbol, NonTerminal):
                        nonTerminals.add(symbol)
                        continue

                    raise Exception("Unknown type {}".format(symbol))

        self.terminalList.append(SpecialTerminal.EOF())

        for terminal in terminals:
            terminal.id = len(self.terminalList)
            self.terminalList.append(terminal)

        for nonTerminal in nonTerminals:
            nonTerminal.id = len(self.nonTerminalList)
            self.nonTerminalList.append(nonTerminal)

    def _prepareGenerators(self):
        for rule in self.rules:
            if rule.nonTerminal not in self.generators:
                self.generators[rule.nonTerminal] = []

            self.generators[rule.nonTerminal].append(rule)

    def _computeFirstSets(self):
        for nonTerminal in self.nonTerminalList:
            self.firstSets[nonTerminal] = set()

        changed = True
        while changed:
            changed = False

            for rule in self.rules:
                targetSet = self.firstSets[rule.nonTerminal]
                previousLength = len(targetSet)

                stack: deque[GammaRegexNode] = deque()
                done: set[GammaRegexNode] = set()
                stack.append(rule.nodes[0])
                done.add(rule.nodes[0])

                while stack:
                    currentNode = stack.pop()

                    if currentNode.isFinal:
                        targetSet.add(SpecialTerminal.EMPTY())

                    for symbol, targetNode in currentNode.transitions.items():
                        if isinstance(symbol, SolidTerminal):
                            targetSet.add(symbol)
                            continue

                        if isinstance(symbol, NonTerminal):
                            targetFirstSet = self.firstSets[symbol]

                            if SpecialTerminal.EMPTY() in targetFirstSet:
                                targetFirstSet = set(targetFirstSet)
                                targetFirstSet.remove(SpecialTerminal.EMPTY())
                                if targetNode not in done:
                                    stack.append(targetNode)

                            targetSet.update(targetFirstSet)
                            continue

                changed |= previousLength != len(targetSet)

    def _computeNodes(self, rootNonTerminal: NonTerminal):
        nodeMap: dict[ParserBuilderNode, ParserBuilderNode] = {}
        stack: deque[ParserBuilderNode] = deque()

        def nodeFactory(constrainedRules: Iterable[ConstrainedMarkedRule]):
            node: ParserBuilderNode = ParserBuilderNode.of(
                constrainedRules, self.firstSets, self.generators
            )

            if node not in nodeMap:
                nodeMap[node] = node
                node.id = len(self.nodes)
                self.nodes.append(node)
                stack.append(node)

            return nodeMap[node]

        rootNode: ParserBuilderNode = nodeFactory(
            (
                ConstrainedMarkedRule(
                    MarkedRule(generator, 0), frozenset([SpecialTerminal.EOF()])
                )
                for generator in self.generators[rootNonTerminal]
            )
        )

        while stack:
            currentNode = stack.pop()

            transitions: dict[Symbol, set[ConstrainedMarkedRule]] = {}

            for rule in currentNode.constrainedRules:
                for symbol, targetRuleNode in rule.markedRule.rule.nodes[
                    rule.markedRule.mark
                ].transitions.items():

                    if symbol not in transitions:
                        transitions[symbol] = set()

                    newRule = ConstrainedMarkedRule(
                        MarkedRule(rule.markedRule.rule, targetRuleNode.id),
                        rule.lookAheads,
                    )
                    newRule.followSets = rule.followSets
                    transitions[symbol].add(newRule)

            for symbol, targetSet in transitions.items():
                targetNode = nodeFactory(targetSet)
                currentNode.transitions[symbol] = targetNode

    def _computeStates(self, rootNonTerminal: NonTerminal):
        states: list[ParserState] = []

        for node in self.nodes:
            actionSources: list[list[tuple[ConstrainedMarkedRule, ParserAction]]] = [
                [] for _ in self.terminalList
            ]
            gotos: list[int] = [None for _ in self.nonTerminalList]
            activeRules: list[bool] = [False for _ in self.rules]

            for nonTerminal in self.nonTerminalList:
                targetNode = node.transitions.get(nonTerminal)

                if targetNode is None:
                    continue

                gotos[nonTerminal.id] = targetNode.id

            for rule in node.constrainedRules:
                activeRules[rule.markedRule.rule.id] = True

                for symbol in rule.markedRule.rule.nodes[
                    rule.markedRule.mark
                ].transitions.keys():
                    if isinstance(symbol, SolidTerminal):
                        actionSources[symbol.id].append(
                            (rule, ParserShiftAction(node.transitions[symbol].id))
                        )

                if (
                    rule.markedRule.rule.nodes[rule.markedRule.mark].isFinal
                    and rule.markedRule.rule.nonTerminal == rootNonTerminal
                ):
                    actionSources[SpecialTerminal.EOF().id].append(
                        (rule, ParserAcceptAction())
                    )
                    continue

                if not rule.markedRule.rule.nodes[rule.markedRule.mark].isFinal:
                    continue

                for lookAhead in rule.lookAheads:
                    actionSources[lookAhead.id].append(
                        (rule, ParserReduceAction(rule.markedRule.rule))
                    )
            resultActions: list[ParserAction] = [None for _ in self.terminalList]
            for index, actions in enumerate(actionSources):
                compiledActions: dict[ParserAction, list[ConstrainedMarkedRule]] = {}
                for rule, action in actions:
                    if action not in compiledActions:
                        compiledActions[action] = []

                    compiledActions[action].append(rule)
                if len(compiledActions) > 1:
                    if self.conflictSolver is None:
                        raise Exception(
                            "Conflict found, but no conflict solver defined"
                        )

                    foundAction = self.conflictSolver(compiledActions)
                    if foundAction is None:
                        raise Exception(
                            "Unsolved conflict on state {} between actions {}".format(
                                node.id, ", ".join(map(str, compiledActions.keys()))
                            )
                        )
                    resultActions[index] = foundAction
                elif len(compiledActions) == 1:
                    resultActions[index] = next(iter(compiledActions.keys()))

            states.append(
                ParserState(
                    len(states),
                    resultActions,
                    gotos,
                    activeRules,
                )
            )

        return Parser(states)
