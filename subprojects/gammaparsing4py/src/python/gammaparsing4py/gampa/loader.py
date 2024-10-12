from io import StringIO, TextIOBase

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.parser.builder import ParserBuilder
from gammaparsing4py.parser.gammaregex import GammaRegex, readGammaRegex
from gammaparsing4py.parser.parser import Parser
from gammaparsing4py.parser.symbols import (
    AbstractTerminal,
    NonTerminal,
    SpecialTerminal,
)
from gammaparsing4py.tokenizer.tokenizer import Tokenizer, TokenizerBuilder


def loadGAMPAPartially(
    inputStream: TextIOBase,
) -> tuple[NonTerminal, TokenizerBuilder[AbstractTerminal], ParserBuilder]:
    flow = CharFlow(inputStream)

    rootSymbol: NonTerminal = None

    tokenizerBuilder = TokenizerBuilder[AbstractTerminal]()
    parserBuilder = ParserBuilder()

    flow.skipBlanksAndComments()
    while flow.hasMore():
        section = _readIdentifier(flow)

        if section == "patterns":
            _read(flow, "{")
            while flow.peek() != ord("}"):
                _readPattern(flow, parserBuilder, tokenizerBuilder)
            _read(flow, "}")
            continue

        if section == "rootSymbol":
            identifer = _readIdentifier(flow)
            _read(flow, ";")
            rootSymbol = parserBuilder.getNonTerminal(identifer)
            continue

        if section == "rules":
            _read(flow, "{")
            while flow.peek() != ord("}"):
                _readRule(flow, parserBuilder, tokenizerBuilder)
            _read(flow, "}")
            continue

        raise Exception("Unknown section type '{}'".format(section))

    return rootSymbol, tokenizerBuilder, parserBuilder


def loadGAMPA(inputStream: TextIOBase) -> tuple[Tokenizer[AbstractTerminal], Parser]:
    rootSymbol, tokenizerBuilder, parserBuilder = loadGAMPAPartially(inputStream)

    parser = parserBuilder.build(rootSymbol)

    tokenizer = tokenizerBuilder.build(SpecialTerminal.EOF())
    tokenizer.skipper = lambda token: token.key.id is None

    return tokenizer, parser


@CharFlow.skipBlanksAndCommentsDecorator
def _readIdentifier(flow: CharFlow):
    buffer = StringIO()

    while flow.hasMore() and (chr(flow.peek()).isalnum() or flow.peek() == ord("_")):
        buffer.write(chr(flow.next()))

    return buffer.getvalue()


@CharFlow.skipBlanksAndCommentsDecorator
def _readTerminalIdentifier(flow: CharFlow):
    flow.read(ord("'"))

    buffer = StringIO()

    while flow.peek() != ord("'"):
        buffer.write(chr(flow.next()))

    flow.read(ord("'"))

    return buffer.getvalue()


@CharFlow.skipBlanksAndCommentsDecorator
def _read(flow: CharFlow, target: str):
    for c in target:
        flow.read(ord(c))


@CharFlow.skipBlanksAndCommentsDecorator
def _readString(flow: CharFlow):
    flow.read(ord('"'))

    buffer = StringIO()

    while flow.peek() != ord('"'):
        if flow.check(ord("\\")):
            if flow.check(ord('"')):
                buffer.write('"')
                continue
            buffer.write("\\")
        buffer.write(chr(flow.next()))

    flow.read(ord('"'))

    return buffer.getvalue()


@CharFlow.skipBlanksAndCommentsDecorator
def _readPattern(
    flow: CharFlow,
    parserBuilder: ParserBuilder,
    tokenizerBuilder: TokenizerBuilder[AbstractTerminal],
) -> None:

    pattern: str = None
    terminal: AbstractTerminal = None
    reluctant: bool = False
    above: set[AbstractTerminal] = set()

    # Reading terminal
    terminal = parserBuilder.getTerminal(_readTerminalIdentifier(flow))

    _read(flow, "<--")

    # Reading reluctancy
    reluctant = flow.check(ord("r"))

    # Reading pattern
    pattern = _readString(flow)

    # Reading above set
    if flow.peek() == ord(">"):
        _read(flow, ">")

        above.add(parserBuilder.getTerminal(_readTerminalIdentifier(flow)))

        while flow.peek() != ord(";"):
            _read(flow, ",")
            above.add(parserBuilder.getTerminal(_readTerminalIdentifier(flow)))

    _read(flow, ";")

    tokenizerBuilder.addRawPattern(pattern, terminal, reluctant, above)


@CharFlow.skipBlanksAndCommentsDecorator
def _readRule(
    flow: CharFlow,
    parserBuilder: ParserBuilder,
    tokenizerBuilder: TokenizerBuilder[AbstractTerminal],
) -> None:
    name: str = None
    nonTerminal: NonTerminal = None
    gammaRegex: GammaRegex = None

    # Reading name
    if flow.peek() == ord('"'):
        name = _readString(flow)
        _read(flow, ":")

    # Reading non terminal
    nonTerminal = _readIdentifier(flow)

    _read(flow, "=>")

    # Reading gamma regex
    gammaRegex = readGammaRegex(
        flow, parserBuilder.getTerminal, parserBuilder.getNonTerminal
    )

    _read(flow, ";")

    parserBuilder.addRegexRule(nonTerminal, gammaRegex, name)
