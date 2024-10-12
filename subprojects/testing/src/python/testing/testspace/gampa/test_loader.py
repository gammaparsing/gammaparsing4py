from collections import deque
import os
from unittest import TestCase
from typing import Any

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.core.token import Token
from gammaparsing4py.gampa.loader import loadGAMPA, loadGAMPAPartially
from gammaparsing4py.parser.builder import ConstrainedMarkedRule
from gammaparsing4py.parser.parser import (
    Parser,
    ParserAction,
    ParserBranchingAction,
    ParserShiftAction,
    ParserState,
)
from gammaparsing4py.parser.struct import Rule
from gammaparsing4py.parser.symbols import AbstractTerminal, SpecialTerminal, Symbol
from gammaparsing4py.utils import PushbackIterator
from pengine_utils import PEngineUtils


class Test_Loader(TestCase):

    def test_load_basic(self):
        with open(
            os.path.join(PEngineUtils.subprojectResPath("testing"), "parser1.gampa"),
            "r",
            encoding="utf-8",
        ) as inputStream:
            tokenizer, parser = loadGAMPA(inputStream)

        def reducer(rule: Rule, data: list):
            if rule.name == "paren":
                return data[1]
            if rule.name.startswith("biop"):
                if len(data) == 1:
                    return data[0]
                return ("biop", data[1].data, data[0], data[2])

            if rule.name == "assignment":
                return ("assignment", ("var", data[0].data), data[2])

            if rule.name == "program":
                return data

            if rule.name == "var":
                return ("var", data[0].data)

            if rule.name == "number":
                return ("number", float(data[0].data))

            raise Exception("Unknown rule '{}'".format(rule.name))

        parser.reducer = reducer

        flow = CharFlow.fromString("A = 2 / var2 + var3 - (4 + 7); B = 3;")

        result = parser.parse(tokenizer.iterator(flow))

    def test_load_complex(self):
        with open(
            os.path.join(PEngineUtils.subprojectResPath("testing"), "complex.gampa"),
            "r",
            encoding="utf-8",
        ) as inputStream:
            rootSymbol, tokenizerBuilder, parserBuilder = loadGAMPAPartially(
                inputStream
            )

            tokenizer = tokenizerBuilder.build(SpecialTerminal.EOF())
            tokenizer.skipper = lambda token: token.key.id is None

            RIGHT = 0
            LEFT = 1
            OPERATORS: dict[str, tuple[int, int]] = {
                "+": (1, RIGHT),
                "-": (2, LEFT),
                "/": (3, LEFT),
                "*": (4, LEFT),
                ":": (5, LEFT),
                "^": (6, RIGHT),
            }

            def conflictSolver(
                compiledActions: dict[ParserAction, list[ConstrainedMarkedRule]]
            ) -> ParserAction:

                assert len(compiledActions) == 2
                actions = list(compiledActions.keys())
                shift, reduce = (
                    actions
                    if isinstance(actions[0], ParserShiftAction)
                    else reversed(actions)
                )

                def selector(
                    token: Token[AbstractTerminal],
                    parser: Parser,
                    stateStack: deque[ParserState],
                    symbolStack: deque[Symbol],
                    dataStack: deque[Any],
                    iterator: PushbackIterator[Token[AbstractTerminal]],
                ):
                    nextOpData = OPERATORS[token.data]
                    previousOpData = OPERATORS[dataStack[-2].data]

                    if nextOpData[0] < previousOpData[0] or (
                        nextOpData[0] == previousOpData[0] and previousOpData[1] == LEFT
                    ):
                        return reduce
                    return shift

                return ParserBranchingAction(selector)

            def reducer(rule: Rule, data: list):
                if rule.name == "parenthesis":
                    return data[1]
                if rule.name == "biop":
                    if len(data) == 1:
                        return data[0]
                    return ("biop", data[1].data, data[0], data[2])

                if rule.name == "var":
                    return ("var", data[0].data)

                if rule.name == "number":
                    return ("number", int(data[0].data))

            parserBuilder.conflictSolver = conflictSolver
            parser = parserBuilder.build(rootSymbol)
            parser.reducer = reducer

            data = "A + B * C + D"
            result = parser.parse(tokenizer.iterator(CharFlow.fromString(data)))