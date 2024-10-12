from unittest import TestCase

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.parser.builder import ParserBuilder, Rule
from gammaparsing4py.parser.symbols import AbstractTerminal, SpecialTerminal
from gammaparsing4py.tokenizer.tokenizer import TokenizerBuilder


class Test_Builder(TestCase):

    def test_build_basic(self):
        parserBuilder = ParserBuilder()

        parserBuilder.addRawRule("S", "E")
        parserBuilder.addRawRule("E", "(E '+')? T", "biop-+")
        parserBuilder.addRawRule("T", "(T '*')? F", "biop-*")
        parserBuilder.addRawRule("F", "'id'", "var")
        parserBuilder.addRawRule("F", "'number'", "number")
        parserBuilder.addRawRule("F", "'(' E ')'", "paren")

        

        def reducer(rule: Rule, data: list):
            if rule.name == "paren":
                return data[1]
            if rule.name.startswith("biop"):
                if len(data) == 1:
                    return data[0]
                return ("biop", data[1].data, data[0], data[2])
            return (rule.name, data[0].data)

        

        tokenizerBuilder = TokenizerBuilder[AbstractTerminal]()
        tokenizerBuilder.addRawPattern(r"\+", parserBuilder.getTerminal("+"))
        tokenizerBuilder.addRawPattern(r"\*", parserBuilder.getTerminal("*"))
        tokenizerBuilder.addRawPattern(
            r"[a-zA-Z][0-9a-zA-Z]*", parserBuilder.getTerminal("id")
        )
        tokenizerBuilder.addRawPattern(
            r"[0-9]+\.?[0-9]*", parserBuilder.getTerminal("number")
        )
        tokenizerBuilder.addRawPattern(r"\(", parserBuilder.getTerminal("("))
        tokenizerBuilder.addRawPattern(r"\)", parserBuilder.getTerminal(")"))
        tokenizerBuilder.addRawPattern(r"\s+", parserBuilder.getTerminal("blank"))

        parser = parserBuilder.build(parserBuilder.getNonTerminal("S"))
        parser.reducer = reducer

        tokenizer = tokenizerBuilder.build(SpecialTerminal.EOF())
        tokenizer.skipper = lambda token: token.key.id is None

        data = "A + B + C * D * 2"

        result = parser.parse(tokenizer.iterator(CharFlow.fromString(data)))