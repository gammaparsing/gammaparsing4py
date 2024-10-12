from unittest import TestCase

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.tokenizer.regex import RegexRange
from gammaparsing4py.tokenizer.tokenizer import (
    AVLTree,
    TokenizerBuilder,
)
from gammaparsing4py.utils import treeRepr


class Test_AVLTree(TestCase):

    def test_tree_basic(self):
        tree = AVLTree[str]()
        tree.insert(RegexRange(5, 8), "A")
        tree.insert(RegexRange(10, 15), "B")
        tree.insert(RegexRange(18, 20), "C")
        tree.insert(RegexRange(25, 32), "D")

        self.assertEqual(tree.find(11), "B")
        self.assertEqual(tree.find(26), "D")


class Test_Tokenizer(TestCase):

    def test_tokenizer_building(self):
        builder = TokenizerBuilder[str]()
        builder.addRawPattern(r"\p{Alpha}\w*", "id")
        builder.addRawPattern(r"or", "or", above={"id"})
        builder.addRawPattern(r"\s+", "blank")
        builder.addRawPattern(r"\+|\*|-|/|>|<|>=|<=|!=|==|^", "operator")
        builder.addRawPattern(r"\(", ("leftpar"))
        builder.addRawPattern(r"\)", "rightpar")
        builder.addRawPattern(r"(//|#)[^\n]*\n", "comment", reluctant=True)
        builder.addRawPattern(r"/\*.**/", "comment-multiline", reluctant=True)

        tokenizer = builder.build("eof")

        skipped: set[str] = {"comment", "comment-multiline", "blank"}

        tokenizer.skipper = lambda token: token.key in skipped

        flow: CharFlow = CharFlow.fromString(
            """
            var1 + var2 * (var3 / var4) or test
            """
        )

        iterator = tokenizer.iterator(flow)
        for token in iterator:
            ...
