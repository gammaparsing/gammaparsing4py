from collections import deque
from typing import Any, Callable, Iterable
from gammaparsing4py.core.token import Token
from gammaparsing4py.parser.struct import Rule
from gammaparsing4py.parser.symbols import AbstractTerminal, Symbol
from gammaparsing4py.utils import PushbackIterator


class ParserState:

    def __init__(
        self,
        id: int,
        actions,
        gotos: list[int],
        activeRules: list[bool],
    ):
        self.id: int = id
        self.actions: list[ParserAction] = actions
        self.gotos: list[int] = gotos
        self.activeRules: list[bool] = activeRules

    def __repr__(self) -> str:
        return "ParserState({})".format(self.id)


class Parser:

    def __init__(self, states: list[ParserState]):
        self.states: list[ParserState] = states

        self.reducer: Callable[[Rule, list[Any]], Any] = lambda rule, data: None

    def parse(self, tokens: Iterable[Token[AbstractTerminal]]):
        stateStack: deque[ParserState] = deque()
        dataStack: deque[Any] = deque()
        symbolStack: deque[Symbol] = deque()

        stateStack.append(self.states[0])

        iterator = PushbackIterator(tokens)

        for token in iterator:
            currentState = stateStack[-1]

            action = currentState.actions[token.key.id]

            if action is None:

                raise Exception("Unexpected token {}".format(token))

            result = action.apply(
                token, self, stateStack, symbolStack, dataStack, iterator
            )
            if result is not None:
                return result


class ParserAction:

    def apply(
        self,
        token: Token[AbstractTerminal],
        parser: Parser,
        stateStack: deque[ParserState],
        symbolStack: deque[Symbol],
        dataStack: deque[Any],
        iterator: PushbackIterator[Token[AbstractTerminal]],
    ) -> Any:
        raise NotImplementedError()


class ParserAcceptAction(ParserAction):

    def apply(
        self,
        token: Token[AbstractTerminal],
        parser: Parser,
        stateStack: deque[ParserState],
        symbolStack: deque[Symbol],
        dataStack: deque[Any],
        iterator: PushbackIterator[Token[AbstractTerminal]],
    ) -> Any:
        return dataStack.pop()

    def __eq__(self, value: object) -> bool:
        return isinstance(value, ParserAcceptAction)

    def __hash__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "ACCEPT()"


class ParserShiftAction(ParserAction):

    def __init__(self, target: int):
        self.target: int = target

    def apply(
        self,
        token: Token[AbstractTerminal],
        parser: Parser,
        stateStack: deque[ParserState],
        symbolStack: deque[Symbol],
        dataStack: deque[Any],
        iterator: PushbackIterator[Token[AbstractTerminal]],
    ) -> Any:
        stateStack.append(parser.states[self.target])
        dataStack.append(token)
        symbolStack.append(token.key)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, ParserShiftAction) and self.target == value.target

    def __hash__(self) -> int:
        return self.target

    def __repr__(self) -> str:
        return "SHIFT({})".format(self.target)


class ParserReduceAction(ParserAction):

    def __init__(self, rule: Rule) -> None:
        self.rule: Rule = rule

    def apply(
        self,
        token: Token[AbstractTerminal],
        parser: Parser,
        stateStack: deque[ParserState],
        symbolStack: deque[Symbol],
        dataStack: deque[Any],
        iterator: PushbackIterator[Token[AbstractTerminal]],
    ) -> Any:
        accumulator: deque[Any] = deque()

        currentNode = self.rule.reversedNodes[0]

        while (
            symbolStack
            and stateStack[-2].activeRules[self.rule.id]
            and symbolStack[-1] in currentNode.transitions
        ):
            currentNode = currentNode.transitions[symbolStack[-1]]
            accumulator.append(dataStack.pop())
            symbolStack.pop()
            stateStack.pop()

        stateStack.append(parser.states[stateStack[-1].gotos[self.rule.nonTerminal.id]])
        dataStack.append(parser.reducer(self.rule, list(reversed(accumulator))))
        symbolStack.append(self.rule.nonTerminal)
        iterator.push(token)

    def __eq__(self, value: object) -> bool:
        return isinstance(value, ParserReduceAction) and self.rule == value.rule

    def __repr__(self) -> str:
        return "REDUCE({})".format(self.rule.id)

    def __hash__(self) -> int:
        return hash(self.rule)


class ParserBranchingAction(ParserAction):

    def __init__(
        self,
        selector: Callable[
            [
                Token[AbstractTerminal],
                Parser,
                deque[ParserState],
                deque[Symbol],
                deque[Any],
                PushbackIterator[Token[AbstractTerminal]],
            ],
            ParserAction,
        ],
        *args,
        **kwargs
    ):
        self.selector: Callable[
            [
                Token[AbstractTerminal],
                Parser,
                deque[ParserState],
                deque[Symbol],
                deque[Any],
                PushbackIterator[Token[AbstractTerminal]],
            ],
            ParserAction,
        ] = selector

        self.args = args
        self.kwargs = kwargs

    def apply(
        self,
        token: Token[AbstractTerminal],
        parser: Parser,
        stateStack: deque[ParserState],
        symbolStack: deque[Symbol],
        dataStack: deque[Any],
        iterator: PushbackIterator[Token[AbstractTerminal]],
    ) -> Any:
        action = self.selector(
            token,
            parser,
            stateStack,
            symbolStack,
            dataStack,
            iterator,
            *self.args,
            **self.kwargs
        )

        if action is None:
            raise Exception("Unable to find an action for token {}".format(token))

        return action.apply(token, parser, stateStack, symbolStack, dataStack, iterator)
