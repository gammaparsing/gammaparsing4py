from collections import deque
from io import StringIO, TextIOBase


class CharFlow:

    def __init__(self, reader: TextIOBase):
        self.reader: TextIOBase = reader

        self.current: int = None
        self.line: int = 0
        self.column: int = 0

    def peek(self):
        if self.current is None:
            obtained: str = self.reader.read(1)
            if len(obtained) == 1:
                self.current = ord(obtained)
            else:
                self.current = -1

        return self.current

    def read(self, target: int):
        if not self.hasMore():
            raise Exception(
                "At line {}, column {}, expected '{}' ({}) but got end of stream".format(
                    self.line, self.column, chr(target), target
                )
            )

        if self.peek() != target:
            raise Exception(
                "At line {}, column {}, expected '{}' ({}) but got '{}' ({})".format(
                    self.line,
                    self.column,
                    chr(target),
                    target,
                    chr(self.peek()),
                    self.peek(),
                )
            )

        self._step()

    def push(self, target: int):
        """
        This functions assumes that the pushed character is not a newline
        """
        assert target != 10
        self.column -= 1
        self.stack.append(target)

    def check(self, target: int):
        if self.hasMore() and self.peek() == target:
            self._step()
            return True
        return False

    def next(self):
        if not self.hasMore():
            raise Exception(
                "At line {}, column {}, tried to step but got end of stream".format(
                    self.line, self.column
                )
            )
        result = self.peek()
        self._step()
        return result

    def _step(self):
        if self.peek() == 10:
            self.line += 1
            self.column = 0
        else:
            self.column += 1

        self.current = None

    def hasMore(self):
        return self.peek() >= 0

    def skipBlanks(self):
        while self.hasMore() and chr(self.peek()).isspace():
            self.next()

    def skipBlanksAndComments(self):
        while self.hasMore():
            if chr(self.peek()).isspace():
                self.next()
                continue

            if self.peek() == ord("#"):
                self.read(ord("#"))

                while self.hasMore() and not self.check(10):
                    self.next()

                continue

            break

    def skipBlanksDecorator(func):

        def wrapped(flow: CharFlow, *args, **kwargs):
            flow.skipBlanks()
            result = func(flow, *args, **kwargs)
            flow.skipBlanks()
            return result

        return wrapped

    def skipBlanksAndCommentsDecorator(func):

        def wrapped(flow: CharFlow, *args, **kwargs):
            flow.skipBlanksAndComments()
            result = func(flow, *args, **kwargs)
            flow.skipBlanksAndComments()
            return result

        return wrapped

    def fromString(target: str):
        return CharFlow(StringIO(target))
