from typing import Generic, TypeVar, Union

from ahocorasick import Automaton, EMPTY, TRIE


class _Missing:
    pass


_T = TypeVar("_T")
MISSING = _Missing()


class MultiPatternExtractor(Generic[_T]):
    def __init__(self, default_value: Union[_T, _Missing] = MISSING) -> None:
        self.automaton = Automaton()
        self.default_value = default_value


    def add(self, value: _T, *patterns: str) -> "MultiPatternExtractor":
        if len(patterns) > 0:
            for pattern in patterns:
                self.automaton.add_word(pattern, value)
        else:
            self.default_value = value

        return self


    def finalize(self) -> None:
        if self.automaton.kind == TRIE:
            self.automaton.make_automaton()


    def extract(self, text: str) -> _T:
        self.finalize()

        if self.automaton.kind == EMPTY:
            value = self.default_value
        else:
            _, value = next(self.automaton.iter(text), (None, self.default_value))

        if value is MISSING:
            raise ValueError("MultiPatternExtractor: default value is missing")

        return value
