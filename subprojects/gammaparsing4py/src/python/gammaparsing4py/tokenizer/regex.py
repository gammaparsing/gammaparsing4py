from collections import deque
from io import StringIO
import itertools
from typing import Callable, Iterable, Reversible, TypeVar
from typing_extensions import Self

from gammaparsing4py.core.charflow import CharFlow

T = TypeVar("T")

## Regex structure


def flatten(
    data: Iterable[T],
    criterion: Callable[[T], bool],
    splitter: Callable[[T], Reversible[T]],
) -> deque[T]:
    stack: deque[T] = deque(data)
    output: deque[T] = deque()

    while stack:
        current = stack.pop()
        if criterion(current):
            stack.extend(reversed(splitter(current)))
        else:
            output.append(current)

    return output


class Regex:

    def getChildren(self) -> list[Self]:
        raise NotImplementedError()

    def getShortName(self) -> str:
        raise NotImplementedError()


def getRegexChildren(target: Regex):
    return target.getChildren()


def getRegexShortName(target: Regex) -> str:
    return target.getShortName()


class RegexChoice(Regex):

    def __init__(self, options: list[Regex]):
        self.options: list[Regex] = options

    def getChildren(self) -> list[Self]:
        return self.options

    def getShortName(self) -> str:
        return "RegexChoice({})".format(len(self.options))

    def isChoice(target: Regex):
        return isinstance(target, RegexChoice)

    def of(options: Iterable[Regex]) -> Regex:
        flat = flatten(options, RegexChoice.isChoice, getRegexChildren)

        if len(flat) == 1:
            return flat[0]

        return RegexChoice(list(flat))


class RegexSequence(Regex):

    def __init__(self, items: list[Regex]):
        self.items: list[Regex] = items

    def getChildren(self) -> list[Self]:
        return self.items

    def getShortName(self) -> str:
        return "RegexSequence({})".format(len(self.items))

    def isSequence(target: Regex):
        return isinstance(target, RegexSequence)

    def of(options: Iterable[Regex]) -> Regex:
        flat = flatten(options, RegexSequence.isSequence, getRegexChildren)

        if len(flat) == 1:
            return flat.pop()

        return RegexSequence(list(flat))


class RegexQuantified(Regex):

    STAR = 0
    PLUS = 1
    INTERROGATION_MARK = 2

    def __init__(self, quantifier: int, target: Regex):
        self.quantifier: int = quantifier
        self.target: Regex = target

    def getChildren(self) -> list[Self]:
        return [self.target]

    def getShortName(self) -> str:
        return "RegexQuantified({})".format(self.quantifier)


class RegexRange:

    def __init__(self, start: int, end: int):
        self.start: int = start
        self.end: int = end

    def getShortRepr(self):
        return "{} -> {}".format(self.start, self.end)

    def copy(self) -> Self:
        return RegexRange(self.start, self.end)

    def __repr__(self) -> str:
        return "RegexRange({})".format(self.getShortRepr())

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, RegexRange)
            and self.start == value.start
            and self.end == value.end
        )

    def intersect(rangeA: Self, rangeB: Self):
        start = max(rangeA.start, rangeB.start)
        end = min(rangeA.end, rangeB.end)

        if start <= end:
            return RegexRange(start, end)
        return None

    def isListDisjointed(target: list[Self]) -> bool:
        for i in range(len(target) - 1):
            if target[i].end >= target[i + 1].start:
                return False
        return True

    def ensureListDisjointure(target: list[Self]) -> bool:
        if not RegexRange.isListDisjointed(target):
            return RegexRange.disjointList(target)
        return target

    def disjointList(target: list[Self]) -> list[Self]:
        if len(target) <= 1:
            return target

        data = sorted(target, key=lambda item: item.start)

        iterator = iter(data)
        result: list[RegexRange] = []
        previous: RegexRange = next(iterator).copy()

        for item in iterator:
            if item.start <= previous.end + 1:
                previous.end = max(previous.end, item.end)
            else:
                result.append(previous)
                previous = item.copy()
        result.append(previous)

        return result

    def intersectLists(
        listA: list[Self], listB: list[Self], skipDisjointureChecking: bool = True
    ) -> list[Self]:
        if not skipDisjointureChecking:
            listA = RegexRange.ensureListDisjointure(listA)
            listB = RegexRange.ensureListDisjointure(listB)

        result: list[RegexRange] = []

        indexA = 0
        indexB = 0

        while indexA < len(listA) and indexB < len(listB):
            candidate = RegexRange.intersect(listA[indexA], listB[indexB])

            if candidate is not None:
                result.append(candidate)

            if listA[indexA].end < listB[indexB].end:
                indexA += 1
            else:
                indexB += 1

        return result

    def unionList(*lists: tuple[list[Self]]) -> list[Self]:
        return RegexRange.disjointList(list(itertools.chain.from_iterable(lists)))

    def invertList(target: list[Self], lowerLimit: int = 0, higherLimit: int = 0xFFFF):
        result = []
        lower = lowerLimit

        for item in target:
            if item.start > lower:
                result.append(RegexRange(lower, item.start - 1))
            lower = item.end + 1

        if lower <= higherLimit:
            result.append(RegexRange(lower, higherLimit))

        return result

    def disjointValuedList(
        data: Iterable[tuple[Self, set[T]]]
    ) -> list[tuple[Self, set[T]]]:

        points: list[tuple[int, bool, set[T]]] = []

        for range, values in data:
            points.append((range.start, True, values))
            points.append((range.end + 1, False, values))

        points.sort(key=lambda point: (point[0], point[1]))

        result: list[tuple[RegexRange, set[T]]] = []

        acc: set[T] = set()
        counts: dict[T, int] = {}
        previousIndex: int = -1
        previousType: bool = False

        for index, pointType, values in points:
            if (previousIndex != index or pointType != previousType) and len(acc) > 0:
                result.append((RegexRange(previousIndex, index - 1), set(acc)))

            if pointType:
                for item in values:
                    acc.add(item)

                    if item not in counts:
                        counts[item] = 1
                    else:
                        counts[item] += 1
            else:
                for item in values:
                    counts[item] -= 1

                    if counts[item] == 0:
                        acc.remove(item)

            previousIndex = index
            previousType = pointType

        return result


class RegexClass(Regex):

    def __init__(self, ranges: list[RegexRange]):
        self.ranges: list[RegexRange] = ranges

    def getChildren(self) -> list[Self]:
        return []

    def getShortName(self) -> str:
        return "RegexClass({})".format(
            ", ".join(map(RegexRange.getShortRepr, self.ranges))
        )


## Regex parsing
"""
Grammar used for regular expressions (Random character is noted 'unit')
E -> T ('|' T)*  
T -> F*  
F -> B ('*'|'+'|'?')*  
B -> Char
B -> '(' E ')'
B -> Class
Class -> '[' '^'? ClassT* ']'
ClassT -> ClassF ('&' ClassF)*
ClassF -> Class
ClassF -> Char ('-' Char)?

Char -> '\\'? 'unit'
Char -> '\\' 'x' 'unit' 'unit'
Char -> '\\' 'u' 'unit' 'unit' 'unit' 'unit'
Char -> '\\' 'x' '{' 'unit'+ '}'
Char -> '\\' 'p' '{' '[a-zA-Z]+' '}'
"""


def parseRegex(flow: CharFlow) -> Regex:
    return _readExpression(flow)


def _readExpression(flow: CharFlow) -> Regex:
    acc: deque[Regex] = deque()

    acc.append(_readTerm(flow))
    while flow.check(ord("|")):
        acc.append(_readTerm(flow))

    return RegexChoice.of(reversed(acc))


def _readTerm(flow: CharFlow) -> Regex:
    acc: deque[Regex] = deque()

    while flow.hasMore() and flow.peek() != ord("|") and flow.peek() != ord(")"):
        acc.append(_readFactor(flow))

    return RegexSequence.of(reversed(acc))


def _readFactor(flow: CharFlow) -> Regex:
    result: Regex = _readBase(flow)

    while flow.hasMore():
        if flow.check(ord("+")):
            result = RegexQuantified(RegexQuantified.PLUS, result)
            continue

        if flow.check(ord("*")):
            result = RegexQuantified(RegexQuantified.STAR, result)
            continue

        if flow.check(ord("?")):
            result = RegexQuantified(RegexQuantified.INTERROGATION_MARK, result)
            continue
        break
    return result


def _readBase(flow: CharFlow) -> Regex:
    if flow.check(ord("(")):
        result = _readExpression(flow)
        flow.read(ord(")"))
        return result

    if flow.peek() == ord("["):
        return RegexClass(_readClass(flow))

    return RegexClass(_readChar(flow))


def _readClass(flow: CharFlow) -> list[RegexRange]:
    flow.read(ord("["))

    inverted = flow.check(ord("^"))

    acc: deque[RegexRange] = deque()
    while not flow.check(ord("]")):
        acc.append(_readClassTerm(flow))

    result = RegexRange.unionList(*acc)
    if inverted:
        result = RegexRange.invertList(result)
    return result


def _readClassTerm(flow: CharFlow) -> list[RegexRange]:
    intersection = _readClassFactor(flow)

    while flow.check(ord("&")):
        intersection = RegexRange.intersectLists(intersection, _readClassFactor(flow))

    return intersection


def _readClassFactor(flow: CharFlow) -> list[RegexRange]:
    if flow.peek() == ord("["):
        return _readClass(flow)

    ranges = _readChar(flow)

    if flow.check(ord("-")):
        if len(ranges) != 1 or ranges[0].start != ranges[0].end:
            raise Exception(
                "Cannot define character class whose lower border is not a character"
            )

        start: int = ranges[0].start

        upper = _readChar(flow)
        if len(upper) != 1 or upper[0].start != upper[0].end:
            raise Exception(
                "Cannot define character class whose upper border is not a character"
            )
        end = upper[0].end

        ranges = [RegexRange(min(start, end), max(start, end))]

    return ranges


def getHexValue(target: int):
    if target >= ord("A") and target <= ord("F"):
        return target - ord("A") + 10

    if target >= ord("a") and target <= ord("f"):
        return target - ord("a") + 10

    if target >= ord("0") and target <= ord("9"):
        return target - ord("0")

    return None


def _readChar(flow: CharFlow, protected: bool = False):
    if flow.check(ord(".")):
        return [RegexRange(0, 0xFFFF)]
    if flow.check(ord("\\")) or protected:
        if flow.check(ord("p")):
            posixClass = _readPosixIdentifier(flow)

            if posixClass not in POSIX_CLASSES:
                raise Exception("Unknown posix class '{}'".format(posixClass))

            return POSIX_CLASSES[posixClass]

        if flow.check(ord("s")):
            return POSIX_CLASSES["Space"]

        if flow.check(ord("S")):
            return RegexRange.invertList(POSIX_CLASSES["Space"])

        if flow.check(ord("n")):
            return [RegexRange(0xA, 0xA)]

        if flow.check(ord("t")):
            return [RegexRange(0x9, 0x9)]

        if flow.check(ord("r")):
            return [RegexRange(0xD, 0xD)]

        if flow.check(ord("f")):
            return [RegexRange(0xC, 0xC)]

        if flow.check(ord("a")):
            return [RegexRange(0x7, 0x7)]

        if flow.check(ord("e")):
            return [RegexRange(0x1B, 0x1B)]

        if flow.check(ord("s")):
            return POSIX_CLASSES["Digit"]

        if flow.check(ord("S")):
            return RegexRange.invertList(POSIX_CLASSES["Digit"])

        if flow.check(ord("w")):
            return POSIX_CLASSES["Alnum"] + [RegexRange(ord("_"), ord("_"))]

        if flow.check(ord("W")):
            return RegexRange.invertList(
                POSIX_CLASSES["Alnum"] + [RegexRange(ord("_"), ord("_"))]
            )

        if flow.check(ord("x")):
            code = 0
            if flow.check(ord("{")):
                while not flow.check(ord("}")):
                    code = 16 * code + getHexValue(flow.next())
            else:
                for _ in range(2):
                    code = 16 * code + getHexValue(flow.next())
            return [RegexRange(code, code)]

        if flow.check(ord("u")):
            code = 0
            for _ in range(4):
                code = 16 * code + getHexValue(flow.next())
            return [RegexRange(code, code)]

    code = flow.next()
    return [RegexRange(code, code)]


def _readPosixIdentifier(flow: CharFlow):
    flow.read(ord("{"))

    buffer = StringIO()

    while flow.peek() != ord("}"):
        buffer.write(chr(flow.next()))

    flow.read(ord("}"))

    return buffer.getvalue()


POSIX_CLASSES = {
    "Space": _readClass(CharFlow.fromString("[\x09-\x0D\x20\x85\xA0]")),
    "Lower": _readClass(CharFlow.fromString("[a-z]")),
    "Upper": _readClass(CharFlow.fromString("[A-Z]")),
    "ASCII": _readClass(CharFlow.fromString("[\x00-\x7F]")),
    "Alpha": _readClass(CharFlow.fromString("[a-zA-Z]")),
    "Digit": _readClass(CharFlow.fromString("[0-9]")),
    "Alnum": _readClass(CharFlow.fromString("[0-9a-zA-Z]")),
    "Cntrl": _readClass(CharFlow.fromString("[\x00-\x1F\x7F]")),
    "XDigit": _readClass(CharFlow.fromString("[0-9a-fA-F]")),
}
