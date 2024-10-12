from typing import Generic, TypeVar

T = TypeVar("T")


class Token(Generic[T]):

    def __init__(self, key: T, data: str, line: int, column: int):
        self.key: T = key
        self.data: str = data
        self.line: int = line
        self.column: int = column

    def __repr__(self) -> str:
        return "Token(key={}, data={}, line={}, column={})".format(
            repr(self.key), repr(self.data), self.line, self.column
        )
