from unittest import TestCase

from gammaparsing4py.core.charflow import CharFlow
from gammaparsing4py.tokenizer.regex import (
    RegexRange,
    getRegexChildren,
    getRegexShortName,
    parseRegex,
)
from gammaparsing4py.utils import treeRepr


class Test_RegexRange(TestCase):

    def test_list_disjointure(self):
        target: list[RegexRange] = [
            RegexRange(5, 8),
            RegexRange(1, 10),
            RegexRange(12, 15),
            RegexRange(20, 25),
            RegexRange(15, 18),
        ]

        self.assertEqual(
            RegexRange.disjointList(target),
            [RegexRange(1, 10), RegexRange(12, 18), RegexRange(20, 25)],
        )

    def test_list_intersect(self):
        listA: list[RegexRange] = [
            RegexRange(1, 10),
            RegexRange(15, 28),
            RegexRange(32, 35),
        ]

        listB: list[RegexRange] = [
            RegexRange(2, 5),
            RegexRange(8, 8),
            RegexRange(10, 12),
            RegexRange(20, 35),
        ]

        self.assertEqual(
            RegexRange.intersectLists(listA, listB),
            [
                RegexRange(2, 5),
                RegexRange(8, 8),
                RegexRange(10, 10),
                RegexRange(20, 28),
                RegexRange(32, 35),
            ],
        )

    def test_list_union(self):
        listA: list[RegexRange] = [
            RegexRange(1, 10),
            RegexRange(15, 28),
            RegexRange(32, 35),
        ]

        listB: list[RegexRange] = [
            RegexRange(2, 5),
            RegexRange(8, 8),
            RegexRange(10, 12),
            RegexRange(20, 35),
        ]

        self.assertEqual(
            RegexRange.unionList(listA, listB), [RegexRange(1, 12), RegexRange(15, 35)]
        )

    def test_list_invert(self):
        target: list[RegexRange] = [
            RegexRange(1, 10),
            RegexRange(15, 28),
            RegexRange(32, 35),
        ]

        self.assertEqual(
            RegexRange.invertList(target),
            [
                RegexRange(0, 0),
                RegexRange(11, 14),
                RegexRange(29, 31),
                RegexRange(36, 0xFFFF),
            ],
        )

    def test_list_disjoint_valued(self):
        target: list[tuple[RegexRange, str]] = [
            (RegexRange(2, 15), {"A", "B", "C"}),
            (RegexRange(6, 18), {"B", "D", "E"}),
            (RegexRange(10, 12), {"F", "G", "A"}),
        ]

        expected: list[tuple[RegexRange, str]] = [
            (RegexRange(2, 5), {"A", "B", "C"}),
            (RegexRange(6, 9), {"A", "B", "C", "D", "E"}),
            (RegexRange(10, 12), {"A", "B", "C", "D", "E", "F", "G"}),
            (RegexRange(13, 15), {"A", "B", "C", "D", "E"}),
            (RegexRange(16, 18), {"B", "D", "E"}),
        ]

        self.assertEqual(RegexRange.disjointValuedList(target), expected)


class Test_RegexParser(TestCase):

    def test_parsing(self):
        regex = parseRegex(CharFlow.fromString(r"\p{Alpha}\w*"))
