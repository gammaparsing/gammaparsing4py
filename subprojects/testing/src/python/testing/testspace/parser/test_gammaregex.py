from unittest import TestCase

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.parser.gammaregex import (
    buildRuleContent,
    readGammaRegex,
)


class Test_GammaRegex(TestCase):

    def test_parse_basic(self):
        flow: CharFlow = CharFlow.fromString(
            "'id' 'leftpar' (E ('colon' E)*)? 'rightpar'"
        )

        gammaRegex = readGammaRegex(flow)

        nodes = buildRuleContent(gammaRegex)
