class Symbol:

    def __init__(self):
        self.id: int = None


class AbstractTerminal(Symbol):

    def __init__(self):
        Symbol.__init__(self)


class SolidTerminal(AbstractTerminal):

    def __init__(self, name: str):
        AbstractTerminal.__init__(self)
        self.name: str = name
        self.tags : set[str] = set()

    def __repr__(self) -> str:
        return "SolidTerminal(name='{}')".format(self.name)


class NonTerminal(Symbol):

    def __init__(self, name: str):
        self.name: str = name

    def __repr__(self) -> str:
        return "NonTerminal(name='{}')".format(self.name)


class SpecialTerminal(AbstractTerminal):

    _EOF_INSTANCE = None
    _EMPTY_INSTANCE = None

    def __init__(self, id: int):
        AbstractTerminal.__init__(self)
        self.id: int = id

    def __hash__(self) -> int:
        return self.id

    def __eq__(self, value: object) -> bool:
        return isinstance(value, SpecialTerminal) and self.id == value.id

    def __repr__(self) -> str:
        return "SpecialTerminal({})".format(
            "EMPTY" if self.id == SpecialTerminal.EMPTY else "EOF"
        )

    def EOF():
        if SpecialTerminal._EOF_INSTANCE is None:
            SpecialTerminal._EOF_INSTANCE = SpecialTerminal(0)

        return SpecialTerminal._EOF_INSTANCE

    def EMPTY():
        if SpecialTerminal._EMPTY_INSTANCE is None:
            SpecialTerminal._EMPTY_INSTANCE = SpecialTerminal(-1)

        return SpecialTerminal._EMPTY_INSTANCE
