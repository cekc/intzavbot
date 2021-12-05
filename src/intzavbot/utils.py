from enum import Enum
from itertools import islice
from typing import Optional


class StrEnum(str, Enum):
    def _generate_next_value_(name: str, start, count, last_values):
        return name.lower()


def normalize_str(string: str, limit: Optional[int] = None) -> str:
    return "".join(islice(filter(str.isalnum, string), 0, limit)).lower().replace("ё", "е")
