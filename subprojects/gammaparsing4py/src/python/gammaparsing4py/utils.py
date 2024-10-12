"""Set of utility tools"""

from collections import deque
from io import StringIO
from typing import Iterable, Callable, Generic, Reversible, TypeVar

T = TypeVar("T")


def treeRepr(
    root: T,
    name: Callable[[T], str],
    children: Callable[[T], Reversible[T]],
    rootBodyPrefix: str = "",
    rootHeadPrefix: str = "",
):
    """
    Returns a tree representation of the given object, 
    using the specified functions to retrieve its textual value and children

    Args:
        root (T) : The root element of the resulting tree
    """
    buffer = StringIO()

    stack: deque[tuple[T, str, str]] = deque()
    stack.append((root, rootBodyPrefix, rootHeadPrefix))

    while stack:
        current, bodyPrefix, headPrefix = stack.pop()

        buffer.write(headPrefix)
        buffer.write(name(current))

        first = True
        for item in reversed(children(current)):
            if first:
                stack.append((item, bodyPrefix + "  ", bodyPrefix + "└─"))
                first = False
            else:
                stack.append((item, bodyPrefix + "│ ", bodyPrefix + "├─"))

        if stack:
            buffer.write("\n")

    return buffer.getvalue()


def unfoldPostfix(root: T, children: Callable[[T], Reversible[T]]) -> deque[T]:
    inputStack: deque[T] = deque()
    outputStack: deque[T] = deque()

    inputStack.append(root)

    while inputStack:
        current = inputStack.pop()

        outputStack.append(current)
        inputStack.extend(reversed(children(current)))

    return outputStack


class PushbackIterator(Generic[T]):

    def __init__(self, iterable: Iterable[T]):
        self.iterable: Iterable[T] = iterable
        self.stack: deque[T] = deque()

    def push(self, item: T):
        self.stack.append(item)

    def __iter__(self):
        return self

    def __next__(self):
        if self.stack:
            return self.stack.pop()

        return next(self.iterable)
