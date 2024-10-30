from gammaparsing4py.parser.gammaregex import GammaRegexNode
from gammaparsing4py.parser.symbols import NonTerminal


class Rule:

    def __init__(
        self,
        nonTerminal: NonTerminal,
        nodes: list[GammaRegexNode],
        reversedNodes: list[GammaRegexNode],
        name: str = None,
        tags: set[str] = None,
    ):
        self.id: int = None
        self.nonTerminal: NonTerminal = nonTerminal
        self.nodes: list[GammaRegexNode] = nodes
        self.reversedNodes: list[GammaRegexNode] = reversedNodes
        self.name: str = name
        if tags is None:
            self.tags: set[str] = set()
        else:
            self.tags: set[str] = tags

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, value: object) -> bool:
        return isinstance(value, Rule) and self.id == value.id
