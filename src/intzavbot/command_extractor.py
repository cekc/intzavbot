import re
from typing import List, Generic, TypeVar, Union


class _Missing:
    pass


_T = TypeVar("_T")
MISSING = _Missing()


class NoMatch(Exception):
    def __init__(self) -> None:
        super().__init__("default value is missing")


class CommandExtractor(Generic[_T]):
    def __init__(self, regex: re.Pattern, values: List[_T], default_value: Union[_T, _Missing] = MISSING) -> None:
        self.regex = regex
        self.values = values
        self.default_value = default_value


    def extract(self, text: str) -> _T:
        match = self.regex.search(text)

        if match is None:
            if self.default_value is MISSING:
                raise NoMatch

            return self.default_value

        for command_match, value in zip(match.groups(), self.values):
            if command_match is not None:
                return value

        raise ValueError("This statement should be unreachable")


class CommandExtractorBuilder(Generic[_T]):
    def __init__(self) -> None:
        self.patterns: List[str] = []
        self.values: List[_T] = []
        self.default_value: Union[_Missing, _T] = MISSING


    def add(self, value: _T, *commands: str) -> "CommandExtractorBuilder":
        if len(commands) == 0:
            self.default_value = value
        else:
            self.patterns.append(r"(\b" + r"\b|\b".join(commands) + r"\b)")
            self.values.append(value)

        return self


    def build(self) -> CommandExtractor:
        return CommandExtractor(
            regex=re.compile(r"|".join(self.patterns), re.IGNORECASE),
            values=self.values,
            default_value=self.default_value
        )



